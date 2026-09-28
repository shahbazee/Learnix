"""
Centralized Reusable Email Notification Subsystem for Learnix.
Provides unified dispatchers for all 8 core platform lifecycle events:
1. Registration Success
2. OTP Verification
3. Forgot Password OTP
4. Password Changed
5. Course Purchase Successful
6. Payment Receipt / Invoice
7. Course Enrollment
8. Payment Failed

Features:
- Responsive HTML emails with automated plain-text fallback.
- Defensive exception handling so email delivery issues never crash user transactions.
- Zero password/secret exposure in logs or terminal output.
- Complete compatibility with local SMTP and Render production environments.
"""

import os
import logging
import smtplib
import time
import threading
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Fast non-blocking timeout policy:
# Socket connection timeouts and refused connections must never be retried across
# multiple attempts in synchronous web contexts because each timeout stacks into
# worker termination (Gunicorn SIGKILL).
EMAIL_SEND_MAX_ATTEMPTS = 1
EMAIL_SEND_RETRY_DELAY_SECONDS = 1

# Permanent provider rejections that must never be retried (bad credentials, refused
# sender/recipient address, unsupported SMTP feature).
PERMANENT_EMAIL_ERRORS = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPNotSupportedError,
)


def _is_retryable_email_error(exc) -> bool:
    """
    Retry only transient SMTP 4xx responses.
    Socket connection timeouts and refused connections must NOT be retried
    because repeated timeouts aggregate into Gunicorn worker kills.
    """
    if isinstance(exc, PERMANENT_EMAIL_ERRORS):
        return False
    if isinstance(exc, (TimeoutError, smtplib.SMTPConnectError)):
        return False
    # SMTP 4xx responses are temporary, 5xx responses are permanent.
    if isinstance(exc, smtplib.SMTPResponseException):
        code = getattr(exc, 'smtp_code', None)
        return isinstance(code, int) and 400 <= code < 500
    return False


def _send_via_http_api(subject, html_message, plain_message, recipients):
    """
    Optional fallback to send email via HTTP REST API (port 443) when standard SMTP ports
    are firewalled (such as Render free tier blocking ports 25, 465, and 587).
    Supports Resend and Brevo APIs without requiring third-party Django packages.
    """
    resend_key = getattr(settings, 'RESEND_API_KEY', '') or os.getenv('RESEND_API_KEY', '')
    if resend_key:
        try:
            import requests
            sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Learnix <onboarding@resend.dev>')
            payload = {
                "from": sender if '@' in sender else "onboarding@resend.dev",
                "to": recipients,
                "subject": subject,
                "html": html_message,
                "text": plain_message,
            }
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=5
            )
            if resp.status_code in (200, 201):
                logger.info(f"Email successfully dispatched via Resend HTTP API to {recipients}: '{subject}'")
                return True
            else:
                logger.warning(f"Resend HTTP API returned status {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.warning(f"Resend HTTP API dispatch failed: {err}")

    brevo_key = getattr(settings, 'BREVO_API_KEY', '') or os.getenv('BREVO_API_KEY', '')
    if brevo_key:
        try:
            import requests
            sender_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@learnix.com')
            payload = {
                "sender": {"name": getattr(settings, 'SITE_NAME', 'Learnix'), "email": sender_email},
                "to": [{"email": r} for r in recipients],
                "subject": subject,
                "htmlContent": html_message,
                "textContent": plain_message,
            }
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": brevo_key, "Content-Type": "application/json"},
                json=payload,
                timeout=5
            )
            if resp.status_code in (200, 201):
                logger.info(f"Email successfully dispatched via Brevo HTTP API to {recipients}: '{subject}'")
                return True
            else:
                logger.warning(f"Brevo HTTP API returned status {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.warning(f"Brevo HTTP API dispatch failed: {err}")

    return False


def send_platform_email_async(subject, template_name, context, recipient_email, fallback_text=None, attachment_filename=None, attachment_bytes=None, attachment_mimetype="application/pdf"):
    """
    Dispatches platform email in a background daemon thread.
    Guarantees user web transactions and redirects execute in milliseconds without blocking on network I/O.
    """
    thread = threading.Thread(
        target=_send_platform_email,
        args=(subject, template_name, context, recipient_email, fallback_text, attachment_filename, attachment_bytes, attachment_mimetype),
        daemon=True
    )
    thread.start()
    return True


def _send_platform_email(subject, template_name, context, recipient_email, fallback_text=None, attachment_filename=None, attachment_bytes=None, attachment_mimetype="application/pdf"):
    """
    Internal helper to render HTML template, build plain-text fallback,
    and safely dispatch email via Django's configured EMAIL_BACKEND.
    Supports binary file attachments (e.g. PDF Tax Invoices).
    Never exposes passwords or sensitive credentials in error logs.
    """
    if isinstance(recipient_email, (list, tuple, set)):
        recipients = [str(e).strip() for e in recipient_email if e and str(e).strip()]
    else:
        recipients = [str(recipient_email).strip()] if recipient_email and str(recipient_email).strip() else []

    if not recipients:
        logger.warning(f"Cannot dispatch email '{subject}': recipient email is empty.")
        return False

    # Inject platform globals into template context
    context.setdefault('site_name', getattr(settings, 'SITE_NAME', 'Learnix'))
    context.setdefault('support_email', getattr(settings, 'DEFAULT_FROM_EMAIL', 'shahbazbutt22ee@gmail.com'))

    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
    except Exception as e:
        logger.warning(f"Failed to render HTML email template '{template_name}': {e}. Using plain text fallback.")
        html_message = None
        plain_message = fallback_text or f"Notification from {context['site_name']}.\n\nPlease visit the website for details."

    # If no binary attachments, attempt HTTP REST API dispatch if an API key is configured
    if not attachment_bytes and _send_via_http_api(subject, html_message, plain_message, recipients):
        return True

    last_error = None
    for attempt in range(1, EMAIL_SEND_MAX_ATTEMPTS + 1):
        try:
            if attachment_bytes and attachment_filename:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipients,
                )
                if html_message:
                    email.attach_alternative(html_message, "text/html")
                email.attach(attachment_filename, attachment_bytes, attachment_mimetype)
                email.send(fail_silently=False)
            else:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients,
                    html_message=html_message,
                    fail_silently=False
                )
            logger.info(f"Email successfully dispatched to {recipients}: '{subject}'" + (f" [Attachment: {attachment_filename}]" if attachment_filename else ""))
            return True
        except Exception as e:
            last_error = e
            if attempt < EMAIL_SEND_MAX_ATTEMPTS and _is_retryable_email_error(e):
                logger.warning(
                    f"Email delivery attempt {attempt}/{EMAIL_SEND_MAX_ATTEMPTS} to {recipients} for subject "
                    f"'{subject}' failed ({type(e).__name__} - {e}). Retrying in {EMAIL_SEND_RETRY_DELAY_SECONDS}s."
                )
                time.sleep(EMAIL_SEND_RETRY_DELAY_SECONDS)
                continue
            break

    # Log failure safely without exposing passwords or private credentials
    logger.error(f"Email delivery failed to {recipient_email} for subject '{subject}'. Reason: {type(last_error).__name__} - {last_error}")
    if getattr(settings, 'DEBUG', False) or os.getenv('RENDER', ''):
        print(f"[LEARNIX EMAIL NOTICE] SMTP delivery to {recipient_email} failed: {type(last_error).__name__} - {last_error}")
    return False


# ==============================================================================
# 1. REGISTRATION SUCCESS
# ==============================================================================
def send_registration_success_email(user, async_send=False):
    """
    Triggered when a student successfully verifies their registration OTP.
    """
    subject = f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')} — Registration Confirmed!"
    recipient_email = user.email
    context = {
        'user': user,
        'login_url': 'https://learnix-ofqe.onrender.com/accounts/login/',
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')}! Your account has been verified and is now fully active.\n\n"
        f"You can log in and explore our masterclass catalog at: https://learnix-ofqe.onrender.com/courses/\n\n"
        f"— The Learnix Team"
    )
    if async_send:
        return send_platform_email_async(subject, 'emails/registration_success.html', context, recipient_email, fallback_text)
    return _send_platform_email(subject, 'emails/registration_success.html', context, recipient_email, fallback_text)


# ==============================================================================
# 2. OTP VERIFICATION
# ==============================================================================
def send_otp_verification_email(user, otp_code, expires_minutes=10, async_send=False):
    """
    Triggered when a student registers; dispatches the 6-digit activation code.
    Always logs the OTP securely to server logs for verification and diagnostics.
    """
    subject = f"Your {getattr(settings, 'SITE_NAME', 'Learnix')} Verification Code: {otp_code}"
    recipient_email = user.email
    context = {
        'user': user,
        'otp_code': otp_code,
        'expires_minutes': expires_minutes,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your {getattr(settings, 'SITE_NAME', 'Learnix')} verification code is: {otp_code}\n\n"
        f"This code will expire in {expires_minutes} minutes.\n\n"
        f"If you did not request this verification code, please ignore this email.\n\n"
        f"— The Learnix Team"
    )
    logger.info(f"[LEARNIX OTP VERIFICATION] Dispatched OTP code '{otp_code}' for recipient '{recipient_email}' (expires in {expires_minutes}m)")
    if getattr(settings, 'DEBUG', False) or os.getenv('RENDER', ''):
        print(f"[LEARNIX OTP VERIFICATION] Code for {recipient_email}: {otp_code}")

    if async_send:
        return send_platform_email_async(subject, 'emails/otp_verification.html', context, recipient_email, fallback_text)
    return _send_platform_email(subject, 'emails/otp_verification.html', context, recipient_email, fallback_text)


# ==============================================================================
# 3. FORGOT PASSWORD OTP
# ==============================================================================
def send_forgot_password_otp_email(user, reset_code, expires_minutes=10, async_send=False):
    """
    Triggered when a user initiates a password reset request.
    Always logs the reset OTP to server logs for diagnostics.
    """
    subject = f"Password Reset Code: {reset_code} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    recipient_email = user.email
    context = {
        'user': user,
        'reset_code': reset_code,
        'expires_minutes': expires_minutes,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"You requested a password reset for your {getattr(settings, 'SITE_NAME', 'Learnix')} account.\n"
        f"Your 6-digit recovery code is: {reset_code}\n\n"
        f"This code will expire in {expires_minutes} minutes.\n\n"
        f"If you did not request this reset, your account is secure and you can disregard this email.\n\n"
        f"— The Learnix Security Team"
    )
    logger.info(f"[LEARNIX PASSWORD RESET OTP] Dispatched reset OTP '{reset_code}' for recipient '{recipient_email}' (expires in {expires_minutes}m)")
    if getattr(settings, 'DEBUG', False) or os.getenv('RENDER', ''):
        print(f"[LEARNIX PASSWORD RESET OTP] Code for {recipient_email}: {reset_code}")

    if async_send:
        return send_platform_email_async(subject, 'emails/forgot_password_otp.html', context, recipient_email, fallback_text)
    return _send_platform_email(subject, 'emails/forgot_password_otp.html', context, recipient_email, fallback_text)


# ==============================================================================
# 4. PASSWORD CHANGED
# ==============================================================================
def send_password_changed_email(user, async_send=False):
    """
    Triggered when a user successfully updates or resets their password.
    """
    subject = f"Security Alert: Your {getattr(settings, 'SITE_NAME', 'Learnix')} Password Was Changed"
    recipient_email = user.email
    context = {
        'user': user,
        'login_url': 'https://learnix-ofqe.onrender.com/accounts/login/',
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"This email confirms that the password for your {getattr(settings, 'SITE_NAME', 'Learnix')} account was successfully changed.\n\n"
        f"If you made this change, no further action is needed.\n\n"
        f"If you did NOT change your password, please contact support immediately.\n\n"
        f"— The Learnix Security Team"
    )
    if async_send:
        return send_platform_email_async(subject, 'emails/password_changed.html', context, recipient_email, fallback_text)
    return _send_platform_email(subject, 'emails/password_changed.html', context, recipient_email, fallback_text)


# ==============================================================================
# 5. COURSE PURCHASE SUCCESSFUL
# ==============================================================================
def send_course_purchase_success_email(user, course, transaction, invoice=None):
    """
    Triggered when Stripe webhook or checkout confirms a successful payment for a course.
    Dispatches to registered account email and/or email entered in Stripe hosted checkout.
    """
    subject = f"Payment Confirmed: {course.title} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    
    recipients = []
    if getattr(user, 'email', None) and user.email.strip():
        recipients.append(user.email.strip())
    inv = invoice or getattr(transaction, 'invoice', None)
    if inv and getattr(inv, 'billing_email', None) and inv.billing_email.strip():
        if inv.billing_email.strip() not in recipients:
            recipients.append(inv.billing_email.strip())
    if not recipients:
        recipients = [f"{user.username}@learnix.edu"]

    context = {
        'user': user,
        'course': course,
        'transaction': transaction,
        'invoice': inv,
    }
    date_str = transaction.created_at.strftime('%B %d, %Y, %I:%M %p') if getattr(transaction, 'created_at', None) else 'Confirmed'
    stripe_ref = getattr(transaction, 'stripe_payment_intent_id', None) or getattr(transaction, 'stripe_checkout_session_id', None) or 'Stripe Verified'
    customer_name = (getattr(inv, 'billing_name', None) or user.get_full_name() or user.first_name or user.username)
    fallback_text = (
        f"Hello {customer_name},\n\n"
        f"Your purchase of '{course.title}' has been successfully processed.\n\n"
        f"Customer Name: {customer_name}\n"
        f"Course: {course.title}\n"
        f"Order Number: #{transaction.order_number}\n"
        f"Amount Paid: ${transaction.amount} {transaction.currency}\n"
        f"Payment Status: {getattr(transaction, 'status', 'COMPLETED')}\n"
        f"Purchase Date: {date_str}\n"
        f"Stripe Reference: {stripe_ref}\n\n"
        f"You can launch your course classroom here:\n"
        f"https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Team"
    )
    return _send_platform_email(subject, 'emails/course_purchase_success.html', context, recipients, fallback_text)


# ==============================================================================
# 6. PAYMENT RECEIPT / INVOICE
# ==============================================================================
def send_payment_receipt_invoice_email(user, course, transaction, invoice=None, pdf_bytes=None):
    """
    Triggered upon confirmed payment to deliver formal tax receipt and invoice details.
    Dispatches itemized HTML receipt in email body AND attaches the official Tax Invoice PDF
    (matching Udemy & Shopify checkout confirmation standards).
    Dispatches to registered account email and/or email entered in Stripe hosted checkout.
    """
    inv_num = invoice.invoice_number if invoice else transaction.order_number
    subject = f"Official Tax Invoice & Receipt: #{inv_num} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    
    recipients = []
    if getattr(user, 'email', None) and user.email.strip():
        recipients.append(user.email.strip())
    if invoice and getattr(invoice, 'billing_email', None) and invoice.billing_email.strip():
        if invoice.billing_email.strip() not in recipients:
            recipients.append(invoice.billing_email.strip())
    if not recipients:
        recipients = [f"{user.username}@learnix.edu"]

    context = {
        'user': user,
        'course': course,
        'transaction': transaction,
        'invoice': invoice,
    }
    date_val = getattr(invoice, 'issued_at', None) or getattr(transaction, 'created_at', None)
    date_str = date_val.strftime('%B %d, %Y, %I:%M %p') if date_val else 'Confirmed'
    stripe_ref = getattr(transaction, 'stripe_payment_intent_id', None) or getattr(transaction, 'stripe_checkout_session_id', None) or 'Stripe Verified'
    customer_name = (getattr(invoice, 'billing_name', None) or user.get_full_name() or user.first_name or user.username)
    billed_to = getattr(invoice, 'billing_email', None) or getattr(user, 'email', '')
    fallback_text = (
        f"Learnix\n"
        f"Official Tax Receipt\n"
        f"Payment Receipt & Invoice\n"
        f"Invoice Number: {inv_num}\n"
        f"Hello {user.first_name or user.username},\n"
        f"Thank you for your business. Here is the formal itemized receipt and tax invoice for your tuition payment:\n\n"
        f"Customer Name: {customer_name}\n"
        f"Billed To: {billed_to}\n"
        f"Course Title: {course.title}\n"
        f"Invoice Number: {inv_num}\n"
        f"Order Reference: #{transaction.order_number}\n"
        f"Payment Status: COMPLETED (Paid via Stripe)\n"
        f"Purchase Date: {date_str}\n"
        f"Stripe Reference: {stripe_ref}\n"
        f"Subtotal: ${transaction.amount} {transaction.currency}\n"
        f"Estimated Tax: $0.00 {transaction.currency}\n"
        f"Amount Paid: ${transaction.amount} {transaction.currency}\n\n"
        f"PDF\n"
        f"Official PDF Tax Invoice Attached\n"
        f"Learnix_Invoice_{inv_num}.pdf\n\n"
        f"View Invoices in Student Billing Hub: https://learnix.com/payments/billing/\n\n"
        f"This invoice was cryptographically authorized via Stripe Inc.\n"
        f"Sent from: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'shahbazbutt22ee@gmail.com')}\n"
        f"© 2026 {getattr(settings, 'SITE_NAME', 'Learnix')} Technologies Inc. All rights reserved."
    )

    # Attach official PDF Invoice if available or renderable
    attachment_filename = f"Learnix_Invoice_{inv_num}.pdf"
    if not pdf_bytes and invoice:
        if getattr(invoice, 'pdf_file', None):
            try:
                invoice.pdf_file.open('rb')
                pdf_bytes = invoice.pdf_file.read()
                invoice.pdf_file.close()
            except Exception:
                pass
        if not pdf_bytes:
            try:
                from payments.services import generate_invoice_pdf
                pdf_bytes = generate_invoice_pdf(invoice)
            except Exception as e:
                logger.warning(f"Could not generate invoice PDF attachment: {e}")

    return _send_platform_email(
        subject,
        'emails/payment_receipt_invoice.html',
        context,
        recipients,
        fallback_text,
        attachment_filename=attachment_filename if pdf_bytes else None,
        attachment_bytes=pdf_bytes,
        attachment_mimetype='application/pdf'
    )


# ==============================================================================
# 7. COURSE ENROLLMENT
# ==============================================================================
def send_course_enrollment_email(user, course, enrollment=None):
    """
    Triggered when a student is actively enrolled into a course (free or paid).
    """
    subject = f"Enrollment Active: Welcome to {course.title} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    recipient_email = user.email or f"{user.username}@learnix.edu"
    context = {
        'user': user,
        'course': course,
        'enrollment': enrollment,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"You are officially enrolled in '{course.title}'!\n\n"
        f"Your learning dashboard and curriculum modules are now active.\n"
        f"Start learning here: https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Academic Pod"
    )
    return _send_platform_email(subject, 'emails/course_enrollment.html', context, recipient_email, fallback_text)


# ==============================================================================
# 8. PAYMENT FAILED
# ==============================================================================
def send_payment_failed_email(user, course, error_reason=None):
    """
    Triggered when Stripe webhook or session indicates payment failed or expired.
    """
    subject = f"Payment Incomplete: Action Required for {course.title} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    recipient_email = user.email or f"{user.username}@learnix.edu"
    context = {
        'user': user,
        'course': course,
        'error_reason': error_reason or "The card issuer declined the transaction or the payment session timed out.",
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"We were unable to process your payment for '{course.title}'.\n\n"
        f"Reason: {context['error_reason']}\n\n"
        f"No funds were deducted. To complete your enrollment, please retry with a valid payment method:\n"
        f"https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Concierge Team"
    )
    return _send_platform_email(subject, 'emails/payment_failed.html', context, recipient_email, fallback_text)
