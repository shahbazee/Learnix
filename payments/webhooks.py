import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe

from core.emails import send_payment_failed_email
from courses.models import Course
from .services import fulfill_order_and_dispatch_emails

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    is_mock_mode = (
        not sig_header and
        (
            settings.DEBUG or
            not settings.STRIPE_WEBHOOK_SECRET or
            settings.STRIPE_WEBHOOK_SECRET.endswith('_placeholder')
        )
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
            logger.warning(
                f"Stripe Webhook Signature Verification failed: {e}"
            )
            return HttpResponse(status=400)
        except Exception as e:
            logger.error(f"Unexpected webhook error: {e}")
            return HttpResponse(status=400)

    event_type = (
        event.get("type")
        if isinstance(event, dict)
        else getattr(event, "type", None)
    )

    if event_type == "checkout.session.completed":
        session = (
            event.get("data", {}).get("object", {})
            if isinstance(event, dict)
            else event.data.object
        )
        metadata = (
            session.get("metadata", {})
            if isinstance(session, dict)
            else getattr(session, "metadata", {})
        )

        user_id = metadata.get("user_id")
        course_id = metadata.get("course_id")
        order_number = metadata.get("order_number")
        session_id = (
            session.get("id")
            if isinstance(session, dict)
            else getattr(session, "id", None)
        )
        payment_intent = (
            session.get("payment_intent")
            if isinstance(session, dict)
            else getattr(session, "payment_intent", None)
        )

        if user_id and course_id:
            try:
                customer_details = (
                    session.get("customer_details", {})
                    if isinstance(session, dict)
                    else getattr(session, "customer_details", {})
                )
                billing_name = (
                    customer_details.get("name")
                    if isinstance(customer_details, dict)
                    else getattr(customer_details, "name", None)
                )
                billing_email = (
                    customer_details.get("email")
                    if isinstance(customer_details, dict)
                    else getattr(customer_details, "email", None)
                )

                fulfillment_result = fulfill_order_and_dispatch_emails(
                    user_id=int(user_id),
                    course_id=int(course_id),
                    order_number=order_number,
                    session_id=session_id,
                    stripe_payment_intent=payment_intent,
                    billing_name=billing_name,
                    billing_email=billing_email,
                )
                if not fulfillment_result:
                    logger.error(
                        f"Fulfillment returned None for order #{order_number}"
                    )
                    return HttpResponse(status=500)
            except Exception as e:
                logger.error(f"Error fulfilling webhook order: {e}")
                return HttpResponse(status=500)
        else:
            logger.info(
                "Stripe webhook: 'checkout.session.completed' received "
                "without user/course metadata (e.g. from 'stripe trigger "
                "checkout.session.completed'). Event acknowledged."
            )

    elif event_type in [
        "payment_intent.payment_failed",
        "checkout.session.expired"
    ]:
        session = (
            event.get("data", {}).get("object", {})
            if isinstance(event, dict)
            else event.data.object
        )
        metadata = (
            session.get("metadata", {})
            if isinstance(session, dict)
            else getattr(session, "metadata", {})
        )
        user_id = metadata.get("user_id")
        course_id = metadata.get("course_id")
        last_error = (
            session.get("last_payment_error", {})
            if isinstance(session, dict)
            else getattr(session, "last_payment_error", {})
        )
        default_err = (
            "The payment was declined by your bank or the session expired."
        )
        error_msg = (
            last_error.get("message")
            if isinstance(last_error, dict)
            else getattr(last_error, "message", default_err)
        )

        if user_id and course_id:
            try:
                user = User.objects.get(id=int(user_id))
                course = Course.objects.get(id=int(course_id))
                send_payment_failed_email(
                    user, course, error_reason=error_msg
                )
                logger.info(
                    f"Dispatched payment failed email for user "
                    f"{user.username}, course {course.title}"
                )
            except Exception as e:
                logger.error(f"Error dispatching payment failure email: {e}")

    return HttpResponse(status=200)
