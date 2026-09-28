"""
Centralized email notification and order fulfillment services for Learnix.
All emails are dispatched with sender set to settings.DEFAULT_FROM_EMAIL (shahbazbutt22ee@gmail.com).
"""

import logging
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from xhtml2pdf import pisa
from decimal import Decimal
from django.db import transaction as db_transaction
from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment
from .models import PaymentTransaction, Invoice
from core.emails import (
    send_registration_success_email,
    send_otp_verification_email,
    send_forgot_password_otp_email,
    send_password_changed_email,
    send_course_purchase_success_email,
    send_payment_receipt_invoice_email,
    send_course_enrollment_email,
    send_payment_failed_email,
)

logger = logging.getLogger(__name__)


def send_order_confirmation_email(user, course, transaction, invoice=None):
    """
    Dispatches order receipt and tuition confirmation email to the enrolled student.
    Routes through core.emails._send_platform_email → Brevo HTTP API (primary channel).
    """
    from core.emails import send_course_purchase_success_email
    try:
        result = send_course_purchase_success_email(user, course, transaction, invoice=invoice)
        if result:
            logger.info(f"Order confirmation email dispatched to {user.email} via Brevo for order #{transaction.order_number}")
        else:
            logger.error(f"Order confirmation email failed for {user.email} order #{transaction.order_number}")
        return result
    except Exception as e:
        logger.error(f"Failed to dispatch order confirmation email for order #{transaction.order_number}: {e}")
        return False


def send_registration_welcome_email(user):
    """
    Dispatches welcome email upon successful account verification.
    Routes through core.emails._send_platform_email → Brevo HTTP API.
    """
    from core.emails import send_registration_success_email
    return send_registration_success_email(user)


def send_password_reset_otp_email(user, reset_code):
    """
    Dispatches password recovery OTP to the user.
    Routes through core.emails._send_platform_email → Brevo HTTP API.
    """
    from core.emails import send_forgot_password_otp_email
    return send_forgot_password_otp_email(user, reset_code)



def generate_invoice_pdf(invoice) -> bytes:
    """
    Renders the official tax invoice HTML template and converts it to PDF binary bytes
    using xhtml2pdf. Also caches the generated PDF to invoice.pdf_file if not already saved.
    """
    context = {
        'invoice': invoice,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }
    html_string = render_to_string('payments/invoice_pdf.html', context)
    result_buffer = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode('utf-8')), result_buffer, encoding='utf-8')
    if pdf.err:
        logger.error(f"xhtml2pdf error generating invoice PDF {invoice.invoice_number}: {pdf.err}")
        return None

    pdf_bytes = result_buffer.getvalue()

    # Cache PDF in model FileField if empty and model provides save method
    if getattr(invoice, 'pdf_file', None) is not None and hasattr(invoice.pdf_file, 'save') and not invoice.pdf_file:
        try:
            invoice.pdf_file.save(f"invoice_{invoice.invoice_number}.pdf", ContentFile(pdf_bytes), save=True)
        except Exception as e:
            logger.warning(f"Could not persist PDF file to disk for {invoice.invoice_number}: {e}")

    return pdf_bytes


def generate_receipt_pdf(transaction) -> bytes:
    """
    Renders the payment receipt HTML template and converts it to PDF binary bytes
    using xhtml2pdf.
    """
    context = {
        'transaction': transaction,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }
    html_string = render_to_string('payments/receipt_pdf.html', context)
    result_buffer = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode('utf-8')), result_buffer, encoding='utf-8')
    if pdf.err:
        logger.error(f"xhtml2pdf error generating receipt PDF {transaction.order_number}: {pdf.err}")
        return None

    return result_buffer.getvalue()


def fulfill_order_and_dispatch_emails(
    user_id=None,
    course_id=None,
    order_number=None,
    session_id=None,
    stripe_payment_intent=None,
    transaction=None,
    billing_name=None,
    billing_email=None,
):
    """
    Unified, idempotent order fulfillment and email delivery function.
    Guarantees:
    - Atomically locates or creates the PaymentTransaction.
    - Sets transaction status = 'COMPLETED'.
    - Updates stripe_checkout_session_id and stripe_payment_intent_id if provided.
    - Idempotently creates or activates the user's Enrollment in the course.
    - Idempotently generates the formal tax Invoice.
    - Checks `confirmation_emails_sent`:
      If False:
        1. send_course_purchase_success_email(user, course, tx)
        2. send_payment_receipt_invoice_email(user, course, tx, invoice)
        3. send_course_enrollment_email(user, course, enrollment)
        4. Only flags tx.confirmation_emails_sent = True when the invoice / receipt email was
           actually accepted by the SMTP server, so a transient delivery failure is retried by
           the next confirmation event instead of silently losing the customer's invoice.
      If True:
        Suppresses duplicate emails, ensuring zero duplicates upon webhook retries
        or repeated success page redirects.
    Sender:
      Always settings.DEFAULT_FROM_EMAIL ('shahbazbutt22ee@gmail.com').
    Returns:
      dict: {'transaction': tx, 'enrollment': enrollment, 'invoice': invoice, 'emails_sent': bool}
    """
    User = get_user_model()

    if billing_name and not isinstance(billing_name, str):
        billing_name = None
    if billing_email and not isinstance(billing_email, str):
        billing_email = None

    with db_transaction.atomic():
        tx = None
        if transaction:
            tx = PaymentTransaction.objects.select_for_update().filter(pk=transaction.pk).first()
        elif order_number:
            tx = PaymentTransaction.objects.select_for_update().filter(order_number=order_number).first()
        elif session_id:
            tx = PaymentTransaction.objects.select_for_update().filter(stripe_checkout_session_id=session_id).first()

        user = None
        course = None
        if tx:
            user = tx.user
            course = tx.course
        else:
            if user_id:
                user = User.objects.filter(pk=int(user_id)).first()
            if course_id:
                course = Course.objects.filter(pk=int(course_id)).first()

            if not user or not course:
                logger.error(f"Cannot fulfill order: missing user ({user_id}) or course ({course_id})")
                return None

            tx = PaymentTransaction.objects.create(
                user=user,
                course=course,
                order_number=order_number or PaymentTransaction.generate_order_number(),
                amount=course.price,
                currency=settings.STRIPE_CURRENCY.upper(),
                status="COMPLETED",
                stripe_checkout_session_id=session_id,
                stripe_payment_intent_id=stripe_payment_intent,
            )

        # Update transaction details
        tx.status = "COMPLETED"
        if session_id and not tx.stripe_checkout_session_id:
            tx.stripe_checkout_session_id = session_id
        if stripe_payment_intent and not tx.stripe_payment_intent_id:
            tx.stripe_payment_intent_id = stripe_payment_intent
        tx.save()

        # Grant Active Enrollment (Idempotent get_or_create)
        enrollment, _ = Enrollment.objects.get_or_create(
            user=user,
            course=course,
            defaults={"is_active": True, "progress_percent": 0.00}
        )
        if not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save(update_fields=["is_active"])

        # Create Formal Tax Invoice (Idempotent get_or_create)
        b_name = billing_name or user.get_full_name() or user.username
        b_email = billing_email or user.email or f"{user.username}@learnix.edu"
        invoice, created = Invoice.objects.get_or_create(
            transaction=tx,
            defaults={
                "invoice_number": Invoice.generate_invoice_number(),
                "billing_name": b_name,
                "billing_email": b_email,
                "subtotal": tx.amount,
                "tax_amount": Decimal("0.00"),
                "total_amount": tx.amount,
            }
        )
        if not created and (billing_name or billing_email):
            updated_fields = []
            if billing_name and invoice.billing_name != billing_name:
                invoice.billing_name = billing_name
                updated_fields.append("billing_name")
            if billing_email and invoice.billing_email != billing_email:
                invoice.billing_email = billing_email
                updated_fields.append("billing_email")
            if updated_fields:
                invoice.save(update_fields=updated_fields)

        # Capture flag BEFORE releasing the lock — read inside atomic, act outside
        already_sent = bool(tx.confirmation_emails_sent)

    # ── DB lock released — now send emails OUTSIDE the atomic block ──────────
    # Sending 3 emails (each 0.5-2s network roundtrip) inside atomic() held a
    # PostgreSQL row lock for several seconds, causing timeouts on Render.
    emails_sent = False
    if not already_sent:
        # Generate official PDF invoice binary bytes (no DB lock needed)
        pdf_bytes = None
        try:
            pdf_bytes = generate_invoice_pdf(invoice)
        except Exception as e:
            logger.warning(f"Could not pre-render invoice PDF for order #{tx.order_number}: {e}")

        # Each notification is isolated — failure in one never blocks the others.
        delivery = {}

        # 1. Purchase Confirmation Email (Brevo HTTP API — instant, no attachment)
        try:
            delivery['purchase_confirmation'] = bool(send_course_purchase_success_email(user, course, tx, invoice=invoice))
        except Exception as e:
            delivery['purchase_confirmation'] = False
            logger.exception(f"Unexpected error dispatching purchase confirmation email for order #{tx.order_number}: {e}")

        # 2. Formal Tax Invoice & Receipt Email with PDF (Brevo SMTP relay — supports attachments)
        try:
            delivery['invoice_receipt'] = bool(send_payment_receipt_invoice_email(user, course, tx, invoice, pdf_bytes=pdf_bytes))
        except Exception as e:
            delivery['invoice_receipt'] = False
            logger.exception(f"Unexpected error dispatching invoice/receipt email for order #{tx.order_number}: {e}")

        # 3. Enrollment Active Email (Brevo HTTP API — instant, no attachment)
        try:
            delivery['enrollment'] = bool(send_course_enrollment_email(user, course, enrollment))
        except Exception as e:
            delivery['enrollment'] = False
            logger.exception(f"Unexpected error dispatching course enrollment email for order #{tx.order_number}: {e}")

        if delivery.get('invoice_receipt'):
            # Mark as sent — short atomic update, not holding lock during network I/O
            PaymentTransaction.objects.filter(pk=tx.pk).update(confirmation_emails_sent=True)
            tx.confirmation_emails_sent = True
            emails_sent = True
            logger.info(
                f"Order #{tx.order_number} fulfilled — all emails dispatched to {user.email} | {delivery}"
            )
            if not all(delivery.values()):
                logger.warning(
                    f"Order #{tx.order_number}: invoice/receipt delivered but some other emails failed: {delivery}"
                )
        else:
            logger.error(
                f"Order #{tx.order_number}: invoice/receipt email FAILED for {user.email}. "
                f"Delivery results: {delivery}. confirmation_emails_sent left False for automatic retry."
            )
    else:
        logger.info(
            f"Order #{tx.order_number} already confirmed — suppressed duplicate emails."
        )

    return {
        'transaction': tx,
        'enrollment': enrollment,
        'invoice': invoice,
        'emails_sent': emails_sent
    }


def reconcile_pending_purchase_emails(user=None, limit=25):
    """
    Self-healing safety net for customer invoice / receipt delivery.

    A purchase is only confirmed either by the Stripe webhook or when the customer's browser
    lands back on /payments/success/ after checkout. If neither happens (tab closed, webhook
    unreachable, transient Stripe API error) the transaction stays PENDING and the customer
    never receives the "Official Tax Invoice & Receipt" email with the attached PDF even
    though the card was charged.

    This helper selects transactions that never received their confirmation emails, verifies
    the payment status directly with Stripe and - only for genuinely paid sessions - re-runs
    fulfill_order_and_dispatch_emails(), which dispatches the purchase confirmation email,
    the invoice / receipt email (with the attached PDF) and the enrollment email.

    The operation is idempotent through PaymentTransaction.confirmation_emails_sent, so it is
    safe to run repeatedly.

    Usage:
        python manage.py shell -c "from payments.services import reconcile_pending_purchase_emails as r; print(r())"

    Returns:
        dict: {'checked': int, 'redeemed': [order numbers], 'skipped': [order numbers]}
    """
    import stripe

    queryset = (
        PaymentTransaction.objects
        .filter(confirmation_emails_sent=False)
        .select_related('user', 'course')
        .order_by('created_at')
    )
    if user is not None:
        queryset = queryset.filter(user=user)
    if limit:
        queryset = queryset[:limit]

    summary = {'checked': 0, 'redeemed': [], 'skipped': []}
    stripe_ready = bool(settings.STRIPE_SECRET_KEY) and not str(settings.STRIPE_SECRET_KEY).endswith('_placeholder')
    if stripe_ready:
        stripe.api_key = settings.STRIPE_SECRET_KEY

    for tx in queryset:
        summary['checked'] += 1
        billing_name = None
        billing_email = None
        payment_intent = None
        is_paid = False

        if tx.stripe_checkout_session_id and stripe_ready:
            try:
                session = stripe.checkout.Session.retrieve(tx.stripe_checkout_session_id)
                is_paid = getattr(session, 'payment_status', None) == 'paid'
                payment_intent = getattr(session, 'payment_intent', None)
                details = getattr(session, 'customer_details', None)
                if details is not None and hasattr(details, 'to_dict'):
                    details = details.to_dict()
                if isinstance(details, dict):
                    name = details.get('name')
                    email = details.get('email')
                    billing_name = name.strip() if isinstance(name, str) and name.strip() else None
                    billing_email = email.strip() if isinstance(email, str) and email.strip() else None
            except Exception as e:
                logger.warning(
                    f"Reconciliation: could not verify Stripe session {tx.stripe_checkout_session_id} "
                    f"for order #{tx.order_number}: {type(e).__name__} - {e}"
                )
                summary['skipped'].append(tx.order_number)
                continue
        elif tx.status == 'COMPLETED' and not tx.stripe_checkout_session_id:
            # Legacy or simulated completed order without a Stripe session reference.
            is_paid = True

        if not is_paid:
            summary['skipped'].append(tx.order_number)
            continue

        result = fulfill_order_and_dispatch_emails(
            transaction=tx,
            session_id=tx.stripe_checkout_session_id,
            stripe_payment_intent=payment_intent,
            order_number=tx.order_number,
            billing_name=billing_name,
            billing_email=billing_email,
        )
        if result and result.get('emails_sent'):
            summary['redeemed'].append(tx.order_number)
        else:
            summary['skipped'].append(tx.order_number)

    if summary['redeemed']:
        logger.info(f"Reconciliation dispatched previously missing confirmation/invoice emails for: {summary['redeemed']}")
    return summary


