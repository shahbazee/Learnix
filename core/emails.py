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

EMAIL_SEND_MAX_ATTEMPTS = 1
EMAIL_SEND_RETRY_DELAY_SECONDS = 1

PERMANENT_EMAIL_ERRORS = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPNotSupportedError,
)


def _is_retryable_email_error(exc) -> bool:
    if isinstance(exc, PERMANENT_EMAIL_ERRORS):
        return False
    if isinstance(exc, (TimeoutError, smtplib.SMTPConnectError)):
        return False
    if isinstance(exc, smtplib.SMTPResponseException):
        code = getattr(exc, 'smtp_code', None)
        return isinstance(code, int) and 400 <= code < 500
    return False


def _send_via_http_api(
    subject, html_message, plain_message, recipients,
    attachment_filename=None, attachment_bytes=None,
    attachment_mimetype="application/pdf"
):
    sender_name = getattr(settings, 'SITE_NAME', 'Learnix')
    sender_email = getattr(
        settings, 'EMAIL_HOST_USER', 'shahbazbutt22ee@gmail.com'
    )
    from_header = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
    if '@' in from_header:
        import email.utils
        parsed_name, parsed_email = email.utils.parseaddr(from_header)
        if parsed_email:
            sender_email = parsed_email
        if parsed_name:
            sender_name = parsed_name

    html_body = (
        html_message
        if html_message and str(html_message).strip()
        else f"<div>{plain_message}</div>"
    )
    text_body = plain_message or strip_tags(html_body)

    brevo_key = (
        getattr(settings, 'BREVO_API_KEY', '') or
        os.getenv('BREVO_API_KEY', '')
    )
    if brevo_key:
        try:
            import requests
            import base64
            payload = {
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": r} for r in recipients],
                "subject": subject,
                "htmlContent": html_body,
                "textContent": text_body,
            }
            if attachment_bytes and attachment_filename:
                payload["attachment"] = [
                    {
                        "name": attachment_filename,
                        "content": base64.b64encode(
                            attachment_bytes
                        ).decode("ascii")
                    }
                ]

            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": brevo_key,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=20
            )
            if resp.status_code in (200, 201):
                att_note = (
                    f" [Attachment: {attachment_filename}]"
                    if (attachment_bytes and attachment_filename)
                    else ""
                )
                logger.info(
                    f"Email successfully dispatched via Brevo HTTP API "
                    f"to {recipients}: '{subject}'{att_note}"
                )
                return True
            else:
                logger.warning(
                    f"Brevo HTTP API returned status "
                    f"{resp.status_code}: {resp.text}"
                )
        except Exception as err:
            logger.warning(f"Brevo HTTP API dispatch failed: {err}")

    resend_key = (
        getattr(settings, 'RESEND_API_KEY', '') or
        os.getenv('RESEND_API_KEY', '')
    )
    if resend_key:
        try:
            import requests
            import base64
            sender_str = (
                f"{sender_name} <{sender_email}>"
                if '@' in sender_email
                else "onboarding@resend.dev"
            )
            payload = {
                "from": sender_str,
                "to": recipients,
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
            if attachment_bytes and attachment_filename:
                payload["attachments"] = [
                    {
                        "filename": attachment_filename,
                        "content": base64.b64encode(
                            attachment_bytes
                        ).decode("ascii")
                    }
                ]

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=20
            )
            if resp.status_code in (200, 201):
                logger.info(
                    f"Email successfully dispatched via Resend HTTP API "
                    f"to {recipients}: '{subject}'"
                )
                return True
            else:
                logger.warning(
                    f"Resend HTTP API returned status "
                    f"{resp.status_code}: {resp.text}"
                )
        except Exception as err:
            logger.warning(f"Resend HTTP API dispatch failed: {err}")

    return False


def _send_via_brevo_smtp(
    subject, html_message, plain_message, recipients,
    attachment_filename=None, attachment_bytes=None,
    attachment_mimetype="application/pdf"
):
    brevo_key = (
        getattr(settings, 'BREVO_API_KEY', '') or
        os.getenv('BREVO_API_KEY', '')
    )
    if not brevo_key:
        return False

    sender_email = (
        getattr(settings, 'EMAIL_HOST_USER', '') or
        os.getenv('EMAIL_HOST_USER', '')
    )
    if not sender_email:
        return False

    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = getattr(
            settings, 'DEFAULT_FROM_EMAIL', sender_email
        )
        msg['To'] = ', '.join(recipients)

        body_part = MIMEMultipart('alternative')
        body_part.attach(MIMEText(plain_message or '', 'plain', 'utf-8'))
        if html_message:
            body_part.attach(MIMEText(html_message, 'html', 'utf-8'))
        msg.attach(body_part)

        if attachment_bytes and attachment_filename:
            attachment_part = MIMEBase('application', 'pdf')
            attachment_part.set_payload(attachment_bytes)
            encoders.encode_base64(attachment_part)
            attachment_part.add_header(
                'Content-Disposition', 'attachment',
                filename=attachment_filename
            )
            msg.attach(attachment_part)

        with smtplib.SMTP(
            'smtp-relay.brevo.com', 587, timeout=15
        ) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, brevo_key)
            server.sendmail(sender_email, recipients, msg.as_string())

        logger.info(
            f"Email with attachment dispatched via Brevo SMTP relay "
            f"to {recipients}: '{subject}' [{attachment_filename}]"
        )
        return True

    except Exception as e:
        logger.warning(
            f"Brevo SMTP relay failed for '{subject}' to {recipients}: "
            f"{type(e).__name__} - {e}"
        )
        return False


def send_platform_email_async(
    subject, template_name, context, recipient_email,
    fallback_text=None, attachment_filename=None,
    attachment_bytes=None, attachment_mimetype="application/pdf"
):
    thread = threading.Thread(
        target=_send_platform_email,
        args=(
            subject, template_name, context, recipient_email,
            fallback_text, attachment_filename, attachment_bytes,
            attachment_mimetype
        ),
        daemon=True
    )
    thread.start()
    return True


def _send_platform_email(
    subject, template_name, context, recipient_email,
    fallback_text=None, attachment_filename=None,
    attachment_bytes=None, attachment_mimetype="application/pdf"
):
    if isinstance(recipient_email, (list, tuple, set)):
        recipients = [
            str(e).strip()
            for e in recipient_email
            if e and str(e).strip()
        ]
    else:
        recipients = (
            [str(recipient_email).strip()]
            if recipient_email and str(recipient_email).strip()
            else []
        )

    if not recipients:
        logger.warning(
            f"Cannot dispatch email '{subject}': "
            f"recipient email is empty."
        )
        return False

    context.setdefault(
        'site_name', getattr(settings, 'SITE_NAME', 'Learnix')
    )
    context.setdefault(
        'support_email',
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'shahbazbutt22ee@gmail.com')
    )

    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
    except Exception as e:
        logger.warning(
            f"Failed to render HTML email template "
            f"'{template_name}': {e}. Using plain text fallback."
        )
        html_message = None
        plain_message = (
            fallback_text or
            f"Notification from {context['site_name']}.\n\n"
            f"Please visit the website for details."
        )

    if _send_via_http_api(
        subject, html_message, plain_message, recipients,
        attachment_filename, attachment_bytes, attachment_mimetype
    ):
        return True

    if attachment_bytes and _send_via_brevo_smtp(
        subject, html_message, plain_message, recipients,
        attachment_filename, attachment_bytes, attachment_mimetype
    ):
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
                email.attach(
                    attachment_filename, attachment_bytes,
                    attachment_mimetype
                )
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
            logger.info(
                f"Email successfully dispatched to {recipients}: "
                f"'{subject}'"
                + (
                    f" [Attachment: {attachment_filename}]"
                    if attachment_filename else ""
                )
            )
            return True
        except Exception as e:
            last_error = e
            if (
                attempt < EMAIL_SEND_MAX_ATTEMPTS and
                _is_retryable_email_error(e)
            ):
                logger.warning(
                    f"Email delivery attempt "
                    f"{attempt}/{EMAIL_SEND_MAX_ATTEMPTS} "
                    f"to {recipients} for subject '{subject}' failed "
                    f"({type(e).__name__} - {e}). Retrying in "
                    f"{EMAIL_SEND_RETRY_DELAY_SECONDS}s."
                )
                time.sleep(EMAIL_SEND_RETRY_DELAY_SECONDS)
                continue
            break

    logger.error(
        f"Email delivery failed to {recipient_email} for subject "
        f"'{subject}'. Reason: {type(last_error).__name__} - {last_error}"
    )
    if getattr(settings, 'DEBUG', False) or os.getenv('RENDER', ''):
        print(
            f"[LEARNIX EMAIL NOTICE] SMTP delivery to "
            f"{recipient_email} failed: "
            f"{type(last_error).__name__} - {last_error}"
        )
    return False


def send_registration_success_email(user, async_send=False):
    subject = (
        f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')} "
        f"— Registration Confirmed!"
    )
    recipient_email = user.email
    context = {
        'user': user,
        'login_url': 'https://learnix-ofqe.onrender.com/accounts/login/',
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')}! "
        f"Your account has been verified and is now fully active.\n\n"
        f"You can log in and explore our masterclass catalog at: "
        f"https://learnix-ofqe.onrender.com/courses/\n\n"
        f"— The Learnix Team"
    )
    if async_send:
        return send_platform_email_async(
            subject, 'emails/registration_success.html',
            context, recipient_email, fallback_text
        )
    return _send_platform_email(
        subject, 'emails/registration_success.html',
        context, recipient_email, fallback_text
    )


def send_otp_verification_email(
    user, otp_code, expires_minutes=10, async_send=False
):
    subject = (
        f"Your {getattr(settings, 'SITE_NAME', 'Learnix')} "
        f"Verification Code: {otp_code}"
    )
    recipient_email = user.email
    context = {
        'user': user,
        'otp_code': otp_code,
        'expires_minutes': expires_minutes,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your {getattr(settings, 'SITE_NAME', 'Learnix')} "
        f"verification code is: {otp_code}\n\n"
        f"This code will expire in {expires_minutes} minutes.\n\n"
        f"If you did not request this verification code, "
        f"please ignore this email.\n\n"
        f"— The Learnix Team"
    )

    logger.info(
        f"[OTP DISPATCH] user='{recipient_email}' "
        f"code='{otp_code}' expires_in={expires_minutes}m"
    )

    is_render = bool(os.getenv('RENDER', ''))
    is_debug = getattr(settings, 'DEBUG', False)
    if is_render or is_debug:
        separator = "=" * 60
        print(f"\n{separator}")
        print(f"[LEARNIX OTP CODE] user={recipient_email}")
        print(
            f"[LEARNIX OTP CODE] code={otp_code}  "
            f"(expires in {expires_minutes} min)"
        )
        print(
            "[LEARNIX OTP CODE] Check Render Logs "
            "if email doesn't arrive"
        )
        print(f"{separator}\n", flush=True)

    if async_send:
        return send_platform_email_async(
            subject, 'emails/otp_verification.html',
            context, recipient_email, fallback_text
        )
    return _send_platform_email(
        subject, 'emails/otp_verification.html',
        context, recipient_email, fallback_text
    )


def send_forgot_password_otp_email(
    user, reset_code, expires_minutes=10, async_send=False
):
    subject = (
        f"Password Reset Code: {reset_code} — "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')}"
    )
    recipient_email = user.email
    context = {
        'user': user,
        'reset_code': reset_code,
        'expires_minutes': expires_minutes,
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"You requested a password reset for your "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')} account.\n"
        f"Your 6-digit recovery code is: {reset_code}\n\n"
        f"This code will expire in {expires_minutes} minutes.\n\n"
        f"If you did not request this reset, your account is secure "
        f"and you can disregard this email.\n\n"
        f"— The Learnix Security Team"
    )
    logger.info(
        f"[LEARNIX PASSWORD RESET OTP] Dispatched reset OTP "
        f"'{reset_code}' for recipient '{recipient_email}' "
        f"(expires in {expires_minutes}m)"
    )
    if getattr(settings, 'DEBUG', False) or os.getenv('RENDER', ''):
        print(
            f"[LEARNIX PASSWORD RESET OTP] Code for "
            f"{recipient_email}: {reset_code}"
        )

    if async_send:
        return send_platform_email_async(
            subject, 'emails/forgot_password_otp.html',
            context, recipient_email, fallback_text
        )
    return _send_platform_email(
        subject, 'emails/forgot_password_otp.html',
        context, recipient_email, fallback_text
    )


def send_password_changed_email(user, async_send=False):
    subject = (
        f"Security Alert: Your "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')} "
        f"Password Was Changed"
    )
    recipient_email = user.email
    context = {
        'user': user,
        'login_url': 'https://learnix-ofqe.onrender.com/accounts/login/',
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"This email confirms that the password for your "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')} account "
        f"was successfully changed.\n\n"
        f"If you made this change, no further action is needed.\n\n"
        f"If you did NOT change your password, please contact "
        f"support immediately.\n\n"
        f"— The Learnix Security Team"
    )
    if async_send:
        return send_platform_email_async(
            subject, 'emails/password_changed.html',
            context, recipient_email, fallback_text
        )
    return _send_platform_email(
        subject, 'emails/password_changed.html',
        context, recipient_email, fallback_text
    )


def send_course_purchase_success_email(
    user, course, transaction, invoice=None
):
    subject = (
        f"Payment Confirmed: {course.title} — "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')}"
    )

    recipients = []
    if getattr(user, 'email', None) and user.email.strip():
        recipients.append(user.email.strip())
    inv = invoice or getattr(transaction, 'invoice', None)
    if (
        inv and getattr(inv, 'billing_email', None) and
        inv.billing_email.strip()
    ):
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
    date_str = (
        transaction.created_at.strftime('%B %d, %Y, %I:%M %p')
        if getattr(transaction, 'created_at', None)
        else 'Confirmed'
    )
    stripe_ref = (
        getattr(transaction, 'stripe_payment_intent_id', None) or
        getattr(transaction, 'stripe_checkout_session_id', None) or
        'Stripe Verified'
    )
    customer_name = (
        getattr(inv, 'billing_name', None) or
        user.get_full_name() or user.first_name or user.username
    )
    fallback_text = (
        f"Hello {customer_name},\n\n"
        f"Your purchase of '{course.title}' has been "
        f"successfully processed.\n\n"
        f"Customer Name: {customer_name}\n"
        f"Course: {course.title}\n"
        f"Order Number: #{transaction.order_number}\n"
        f"Amount Paid: ${transaction.amount} {transaction.currency}\n"
        f"Payment Status: "
        f"{getattr(transaction, 'status', 'COMPLETED')}\n"
        f"Purchase Date: {date_str}\n"
        f"Stripe Reference: {stripe_ref}\n\n"
        f"You can launch your course classroom here:\n"
        f"https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Team"
    )
    return _send_platform_email(
        subject, 'emails/course_purchase_success.html',
        context, recipients, fallback_text
    )


def send_payment_receipt_invoice_email(
    user, course, transaction, invoice=None, pdf_bytes=None
):
    inv_num = (
        invoice.invoice_number if invoice else transaction.order_number
    )
    subject = (
        f"Official Tax Invoice & Receipt: #{inv_num} — "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')}"
    )

    recipients = []
    if getattr(user, 'email', None) and user.email.strip():
        recipients.append(user.email.strip())
    if (
        invoice and getattr(invoice, 'billing_email', None) and
        invoice.billing_email.strip()
    ):
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
    date_val = (
        getattr(invoice, 'issued_at', None) or
        getattr(transaction, 'created_at', None)
    )
    date_str = (
        date_val.strftime('%B %d, %Y, %I:%M %p')
        if date_val else 'Confirmed'
    )
    stripe_ref = (
        getattr(transaction, 'stripe_payment_intent_id', None) or
        getattr(transaction, 'stripe_checkout_session_id', None) or
        'Stripe Verified'
    )
    customer_name = (
        getattr(invoice, 'billing_name', None) or
        user.get_full_name() or user.first_name or user.username
    )
    billed_to = (
        getattr(invoice, 'billing_email', None) or
        getattr(user, 'email', '')
    )
    fallback_text = (
        f"Learnix\n"
        f"Official Tax Receipt\n"
        f"Payment Receipt & Invoice\n"
        f"Invoice Number: {inv_num}\n"
        f"Hello {user.first_name or user.username},\n"
        f"Thank you for your business. Here is the formal itemized "
        f"receipt and tax invoice for your tuition payment:\n\n"
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
        f"View Invoices in Student Billing Hub: "
        f"https://learnix.com/payments/billing/\n\n"
        f"This invoice was cryptographically authorized via Stripe Inc.\n"
        f"Sent from: "
        f"{getattr(settings, 'DEFAULT_FROM_EMAIL', '')}\n"
        f"© 2026 {getattr(settings, 'SITE_NAME', 'Learnix')} "
        f"Technologies Inc. All rights reserved."
    )

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
                logger.warning(
                    f"Could not generate invoice PDF attachment: {e}"
                )

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


def send_course_enrollment_email(user, course, enrollment=None):
    subject = (
        f"Enrollment Active: Welcome to {course.title} — "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')}"
    )
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
        f"Start learning here: "
        f"https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Academic Pod"
    )
    return _send_platform_email(
        subject, 'emails/course_enrollment.html',
        context, recipient_email, fallback_text
    )


def send_payment_failed_email(user, course, error_reason=None):
    subject = (
        f"Payment Incomplete: Action Required for {course.title} — "
        f"{getattr(settings, 'SITE_NAME', 'Learnix')}"
    )
    recipient_email = user.email or f"{user.username}@learnix.edu"
    context = {
        'user': user,
        'course': course,
        'error_reason': (
            error_reason or
            "The card issuer declined the transaction or "
            "the payment session timed out."
        ),
    }
    fallback_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"We were unable to process your payment for "
        f"'{course.title}'.\n\n"
        f"Reason: {context['error_reason']}\n\n"
        f"No funds were deducted. To complete your enrollment, "
        f"please retry with a valid payment method:\n"
        f"https://learnix.com/courses/{course.slug}/\n\n"
        f"— The Learnix Concierge Team"
    )
    return _send_platform_email(
        subject, 'emails/payment_failed.html',
        context, recipient_email, fallback_text
    )
