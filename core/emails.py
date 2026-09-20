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

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _send_platform_email(subject, template_name, context, recipient_email, fallback_text=None):
    """
    Internal helper to render HTML template, build plain-text fallback,
    and safely dispatch email via Django's configured EMAIL_BACKEND.
    Never exposes passwords or sensitive credentials in error logs.
    """
    if not recipient_email:
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

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Email successfully dispatched to {recipient_email}: '{subject}'")
        return True
    except Exception as e:
        # Log failure safely without exposing passwords or private credentials
        logger.error(f"Email delivery failed to {recipient_email} for subject '{subject}'. Reason: {type(e).__name__} - {e}")
        return False


# ==============================================================================
# 1. REGISTRATION SUCCESS
# ==============================================================================
def send_registration_success_email(user):
    """
    Triggered when a student successfully verifies their registration OTP.
    """
    subject = f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')} — Registration Confirmed!"
    recipient_email = user.email
    context = {
        'user': user,
        'login_url': 'https://learnix.com/accounts/login/',
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')}! Your account has been verified and is now fully active.\n\n"
        f"You can log in and explore our masterclass catalog at: https://learnix.com/courses/\n\n"
        f"— The Learnix Team"
    )
    return _send_platform_email(subject, 'emails/registration_success.html', context, recipient_email, fallback_text)


# ==============================================================================
# 2. OTP VERIFICATION
# ==============================================================================
def send_otp_verification_email(user, otp_code, expires_minutes=10):
    """
    Triggered when a student registers; dispatches the 6-digit activation code.
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
    return _send_platform_email(subject, 'emails/otp_verification.html', context, recipient_email, fallback_text)


# ==============================================================================
# 3. FORGOT PASSWORD OTP
# ==============================================================================
def send_forgot_password_otp_email(user, reset_code, expires_minutes=10):
    """
    Triggered when a user initiates a password reset request.
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
    return _send_platform_email(subject, 'emails/forgot_password_otp.html', context, recipient_email, fallback_text)


# ==============================================================================
# 4. PASSWORD CHANGED
# ==============================================================================
def send_password_changed_email(user):
    """
    Triggered when a user successfully updates or resets their password.
    """
    subject = f"Security Alert: Your {getattr(settings, 'SITE_NAME', 'Learnix')} Password Was Changed"
    recipient_email = user.email
    context = {
        'user': user,
        'login_url': 'https://learnix.com/accounts/login/',
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"This email confirms that the password for your {getattr(settings, 'SITE_NAME', 'Learnix')} account was successfully changed.\n\n"
        f"If you made this change, no further action is needed.\n"
        f"If you did NOT change your password, please contact support immediately.\n\n"
        f"— The Learnix Security Team"
    )
    return _send_platform_email(subject, 'emails/password_changed.html', context, recipient_email, fallback_text)


# ==============================================================================
# 5. COURSE PURCHASE SUCCESSFUL
# ==============================================================================
def send_course_purchase_success_email(user, course, transaction):
    """
    Triggered when Stripe webhook confirms a successful payment for a course.
    """
    subject = f"Payment Confirmed: {course.title} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    recipient_email = user.email or f"{user.username}@learnix.edu"
    context = {
        'user': user,
        'course': course,
        'transaction': transaction,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your purchase of '{course.title}' has been successfully processed.\n\n"
        f"Order Number: #{transaction.order_number}\n"
        f"Amount: ${transaction.amount} {transaction.currency}\n"
        f"Status: COMPLETED\n\n"
        f"You can launch your course classroom here:\n"
        f"https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Team"
    )
    return _send_platform_email(subject, 'emails/course_purchase_success.html', context, recipient_email, fallback_text)


# ==============================================================================
# 6. PAYMENT RECEIPT / INVOICE
# ==============================================================================
def send_payment_receipt_invoice_email(user, course, transaction, invoice=None):
    """
    Triggered upon confirmed payment to deliver formal tax receipt and invoice details.
    """
    inv_num = invoice.invoice_number if invoice else transaction.order_number
    subject = f"Official Tax Invoice & Receipt: #{inv_num} — {getattr(settings, 'SITE_NAME', 'Learnix')}"
    recipient_email = user.email or f"{user.username}@learnix.edu"
    context = {
        'user': user,
        'course': course,
        'transaction': transaction,
        'invoice': invoice,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Here is your official tuition receipt and invoice for '{course.title}'.\n\n"
        f"Invoice Number: {inv_num}\n"
        f"Order Reference: #{transaction.order_number}\n"
        f"Amount Paid: ${transaction.amount} {transaction.currency}\n\n"
        f"View all receipts and download PDFs in your Billing Hub:\n"
        f"https://learnix.com/payments/billing/\n\n"
        f"— The Learnix Billing Department"
    )
    return _send_platform_email(subject, 'emails/payment_receipt_invoice.html', context, recipient_email, fallback_text)


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
