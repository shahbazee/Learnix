"""
Asynchronous Stripe Webhook Receiver with HMAC-SHA256 signature verification.
SRS Section 12.2.
"""

import json
import logging
import stripe
from decimal import Decimal
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction

from courses.models import Course, Enrollment
from .models import PaymentTransaction, Invoice
from .services import send_order_confirmation_email
from core.emails import (
    send_course_purchase_success_email,
    send_payment_receipt_invoice_email,
    send_course_enrollment_email,
    send_payment_failed_email,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Production-grade asynchronous webhook listener for Stripe checkout events.
    Verifies cryptographic signature using HMAC-SHA256 with STRIPE_WEBHOOK_SECRET.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    # In local development or test runner without active signature header, allow JSON payload parsing
    is_mock_mode = (
        not sig_header and
        (settings.DEBUG or not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.endswith('_placeholder'))
    )

    if is_mock_mode:
        try:
            event = json.loads(payload.decode('utf-8'))
        except Exception:
            return HttpResponse(status=400)
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.warning(f"Stripe Webhook Signature Verification failed: {e}")
            return HttpResponse(status=400)
        except Exception as e:
            logger.error(f"Unexpected webhook error: {e}")
            return HttpResponse(status=400)

    # Process Completed Checkout
    event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)

    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
        metadata = session.get("metadata", {}) if isinstance(session, dict) else getattr(session, "metadata", {})

        user_id = metadata.get("user_id")
        course_id = metadata.get("course_id")
        order_number = metadata.get("order_number")
        session_id = session.get("id") if isinstance(session, dict) else getattr(session, "id", None)
        payment_intent = session.get("payment_intent") if isinstance(session, dict) else getattr(session, "payment_intent", None)

        if user_id and course_id:
            try:
                user = User.objects.get(id=int(user_id))
                course = Course.objects.get(id=int(course_id))

                with db_transaction.atomic():
                    # 1. Update or create transaction
                    tx = None
                    if order_number:
                        tx = PaymentTransaction.objects.filter(order_number=order_number).first()
                    if not tx and session_id:
                        tx = PaymentTransaction.objects.filter(stripe_checkout_session_id=session_id).first()

                    already_completed = (tx is not None and tx.status == "COMPLETED")

                    if not tx:
                        tx = PaymentTransaction.objects.create(
                            user=user,
                            course=course,
                            order_number=order_number or PaymentTransaction.generate_order_number(),
                            amount=course.price,
                            currency=settings.STRIPE_CURRENCY.upper(),
                            status="COMPLETED",
                            stripe_checkout_session_id=session_id,
                            stripe_payment_intent_id=payment_intent,
                        )
                    else:
                        tx.status = "COMPLETED"
                        tx.stripe_checkout_session_id = session_id or tx.stripe_checkout_session_id
                        tx.stripe_payment_intent_id = payment_intent or tx.stripe_payment_intent_id
                        tx.save()

                    # 2. Grant Active Enrollment (Idempotent get_or_create)
                    enrollment, _ = Enrollment.objects.get_or_create(
                        user=user,
                        course=course,
                        defaults={"is_active": True, "progress_percent": 0.00}
                    )
                    enrollment.is_active = True
                    enrollment.save(update_fields=["is_active"])

                    # 3. Create Formal Tax Invoice (Idempotent get_or_create)
                    invoice, invoice_created = Invoice.objects.get_or_create(
                        transaction=tx,
                        defaults={
                            "invoice_number": Invoice.generate_invoice_number(),
                            "billing_name": user.get_full_name() or user.username,
                            "billing_email": user.email or f"{user.username}@learnix.edu",
                            "subtotal": tx.amount,
                            "tax_amount": Decimal("0.00"),
                            "total_amount": tx.amount,
                        }
                    )

                # 4. Dispatch Email only on first verified fulfillment
                if not already_completed or invoice_created:
                    send_course_purchase_success_email(user, course, tx)
                    send_payment_receipt_invoice_email(user, course, tx, invoice)
                    send_course_enrollment_email(user, course, enrollment)
                    logger.info(f"Successfully fulfilled order #{tx.order_number} and sent confirmation emails to {user.username}")
                else:
                    logger.info(f"Order #{tx.order_number} was already fulfilled; skipping duplicate confirmation email.")

            except Exception as e:
                logger.error(f"Error fulfilling webhook order: {e}")
                return HttpResponse(status=500)
        else:
            logger.info(
                f"Stripe webhook: 'checkout.session.completed' received without user/course metadata "
                f"(e.g. from 'stripe trigger checkout.session.completed'). Event acknowledged."
            )

    # Process Failed or Expired Checkout Sessions
    elif event_type in ["payment_intent.payment_failed", "checkout.session.expired"]:
        session = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
        metadata = session.get("metadata", {}) if isinstance(session, dict) else getattr(session, "metadata", {})
        user_id = metadata.get("user_id")
        course_id = metadata.get("course_id")
        last_error = session.get("last_payment_error", {}) if isinstance(session, dict) else getattr(session, "last_payment_error", {})
        error_msg = (
            last_error.get("message") if isinstance(last_error, dict)
            else getattr(last_error, "message", "The payment was declined by your bank or the session expired.")
        )

        if user_id and course_id:
            try:
                user = User.objects.get(id=int(user_id))
                course = Course.objects.get(id=int(course_id))
                send_payment_failed_email(user, course, error_reason=error_msg)
                logger.info(f"Dispatched payment failed email for user {user.username}, course {course.title}")
            except Exception as e:
                logger.error(f"Error dispatching payment failure email: {e}")

    return HttpResponse(status=200)
