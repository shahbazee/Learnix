"""
Centralized email notification and order fulfillment services for Learnix.
All emails are dispatched with sender set to settings.DEFAULT_FROM_EMAIL (shahbazbutt22ee@gmail.com).
SRS Section 14.
"""

import logging
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from xhtml2pdf import pisa
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
    Sent from: shahbazbutt22ee@gmail.com
    """
    subject = f"Order Confirmed: {course.title} — {settings.SITE_NAME}"
    recipient_email = user.email or f"{user.username}@learnix.edu"

    context = {
        'user': user,
        'course': course,
        'transaction': transaction,
        'invoice': invoice,
        'site_name': settings.SITE_NAME,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }

    try:
        html_message = render_to_string('emails/order_confirmation.html', context)
        plain_message = strip_tags(html_message)
    except Exception as e:
        logger.warning(f"Could not render HTML email template, falling back to plain text: {e}")
        plain_message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"Thank you for enrolling in {course.title}!\n\n"
            f"Order Reference: #{transaction.order_number}\n"
            f"Amount Paid: ${transaction.amount} {transaction.currency}\n"
            f"Payment Status: {transaction.status}\n\n"
            f"You can access your interactive curriculum at any time via your student dashboard:\n"
            f"https://learnix.com/dashboard/\n\n"
            f"— The {settings.SITE_NAME} Team\n"
            f"Sent from: {settings.DEFAULT_FROM_EMAIL}"
        )
        html_message = None

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Order confirmation email dispatched to {recipient_email} from {settings.DEFAULT_FROM_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch order confirmation email: {e}")
        return False


def send_registration_welcome_email(user):
    """
    Dispatches welcome email upon successful account verification.
    Sent from: shahbazbutt22ee@gmail.com
    """
    subject = f"Welcome to {settings.SITE_NAME} — Account Verified!"
    recipient_email = user.email

    context = {
        'user': user,
        'site_name': settings.SITE_NAME,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }

    try:
        html_message = render_to_string('emails/registration_welcome.html', context)
        plain_message = strip_tags(html_message)
    except Exception:
        plain_message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"Welcome to {settings.SITE_NAME}! Your account is now fully verified.\n\n"
            f"Explore masterclass curricula, interactive sandboxes, and agentic microservices:\n"
            f"https://learnix.com/courses/\n\n"
            f"— The {settings.SITE_NAME} Team\n"
            f"Sent from: {settings.DEFAULT_FROM_EMAIL}"
        )
        html_message = None

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch welcome email: {e}")
        return False


def send_password_reset_otp_email(user, reset_code):
    """
    Dispatches password recovery OTP to the user.
    Sent from: shahbazbutt22ee@gmail.com
    """
    subject = f"Password Reset Code: {reset_code} — {settings.SITE_NAME}"
    recipient_email = user.email

    plain_message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"You requested a password reset for your {settings.SITE_NAME} account.\n"
        f"Your verification code is: {reset_code}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"If you did not request this reset, your account is secure and you can disregard this email.\n\n"
        f"— The {settings.SITE_NAME} Security Team\n"
        f"Sent from: {settings.DEFAULT_FROM_EMAIL}"
    )

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch password reset email: {e}")
        return False


def generate_invoice_pdf(invoice) -> bytes:
    """
    Renders the official tax invoice HTML template and converts it to PDF binary bytes
    using xhtml2pdf. Also caches the generated PDF to invoice.pdf_file if not already saved.
    SRS Section 13.
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

    # Cache PDF in model FileField if empty
    if not invoice.pdf_file:
        try:
            invoice.pdf_file.save(f"invoice_{invoice.invoice_number}.pdf", ContentFile(pdf_bytes), save=True)
        except Exception as e:
            logger.warning(f"Could not persist PDF file to disk for {invoice.invoice_number}: {e}")

    return pdf_bytes


def generate_receipt_pdf(transaction) -> bytes:
    """
    Renders the payment receipt HTML template and converts it to PDF binary bytes
    using xhtml2pdf.
    SRS Section 13.
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

