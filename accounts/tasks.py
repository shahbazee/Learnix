from celery import Task, shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import EmailLog, FailedTask
from core.emails import (
    send_forgot_password_otp_email,
    send_otp_verification_email,
    send_password_changed_email,
    send_registration_success_email,
)


class EmailTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        FailedTask.objects.create(
            task_name=self.name,
            args=list(args or []),
            kwargs=dict(kwargs or {}),
            exception=f"{type(exc).__name__}: {exc}",
        )


@shared_task(
    bind=True,
    base=EmailTask,
    max_retries=5,
    queue="emails",
    soft_time_limit=240,
    time_limit=300,
)
def send_otp_email(self, user_id, otp_code, expires_minutes=10):
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return
    key = f"otp:{user_id}:{otp_code}"
    log, created = EmailLog.objects.get_or_create(
        idempotency_key=key,
        defaults={"recipient": user.email, "kind": "otp"},
    )
    if not created and log.status == "sent":
        return
    sent = send_otp_verification_email(
        user,
        otp_code,
        expires_minutes=expires_minutes,
    )
    if sent:
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    else:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(countdown=countdown)


@shared_task(
    bind=True,
    base=EmailTask,
    max_retries=5,
    queue="emails",
    soft_time_limit=240,
    time_limit=300,
)
def send_email_change_otp_email(
    self, user_id, otp_code, new_email, expires_minutes=10
):
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return
    key = f"otp-change:{user_id}:{otp_code}"
    log, created = EmailLog.objects.get_or_create(
        idempotency_key=key,
        defaults={"recipient": new_email, "kind": "otp"},
    )
    if not created and log.status == "sent":
        return
    sent = send_otp_verification_email(
        user,
        otp_code,
        expires_minutes=expires_minutes,
        recipient_email=new_email,
    )
    if sent:
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    else:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(countdown=countdown)


@shared_task(
    bind=True,
    base=EmailTask,
    max_retries=5,
    queue="emails",
    soft_time_limit=240,
    time_limit=300,
)
def send_welcome_email(self, user_id):
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return
    key = f"welcome:{user_id}"
    log, created = EmailLog.objects.get_or_create(
        idempotency_key=key,
        defaults={"recipient": user.email, "kind": "welcome"},
    )
    if not created and log.status == "sent":
        return
    sent = send_registration_success_email(user)
    if sent:
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    else:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(countdown=countdown)


@shared_task(
    bind=True,
    base=EmailTask,
    max_retries=5,
    queue="emails",
    soft_time_limit=240,
    time_limit=300,
)
def send_password_reset_email(self, user_id, reset_code, expires_minutes=10):
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return
    key = f"reset:{user_id}:{reset_code}"
    log, created = EmailLog.objects.get_or_create(
        idempotency_key=key,
        defaults={"recipient": user.email, "kind": "password_reset"},
    )
    if not created and log.status == "sent":
        return
    sent = send_forgot_password_otp_email(
        user,
        reset_code,
        expires_minutes=expires_minutes,
    )
    if sent:
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    else:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(countdown=countdown)


@shared_task(
    bind=True,
    base=EmailTask,
    max_retries=5,
    queue="emails",
    soft_time_limit=240,
    time_limit=300,
)
def send_password_changed_email_task(self, user_id):
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return
    key = f"password_changed:{user_id}:{user.password[-8:]}"
    log, created = EmailLog.objects.get_or_create(
        idempotency_key=key,
        defaults={"recipient": user.email, "kind": "password_changed"},
    )
    if not created and log.status == "sent":
        return
    sent = send_password_changed_email(user)
    if sent:
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    else:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(countdown=countdown)
