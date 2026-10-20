import logging

from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from ..models import EmailOTP

logger = logging.getLogger(__name__)

RESEND_COOLDOWN_SECONDS = 60

OTP_RESEND_LIMIT = 10
OTP_RESEND_WINDOW = 3600


def otp_resend_allowed(user_id, purpose):
    key = f"otp_resend:{purpose}:{user_id}"
    count = cache.get(key, 0)
    if count >= OTP_RESEND_LIMIT:
        return False
    cache.set(key, count + 1, OTP_RESEND_WINDOW)
    return True


def _generate_otp_token(user_id):
    return signing.dumps(user_id, salt="learnix_otp_verify")


def _decode_otp_token(token):
    return signing.loads(token, salt="learnix_otp_verify", max_age=1800)


def resolve_otp_user_id(request):
    user_id = request.session.get("otp_user_id")
    token = request.GET.get("token") or request.POST.get("token")
    if not user_id and token:
        try:
            user_id = _decode_otp_token(token)
            request.session["otp_user_id"] = user_id
            request.session.modified = True
        except (signing.BadSignature, signing.SignatureExpired):
            user_id = None
    return user_id


def resend_otp_code(request, user, purpose, stamp_key, send_task):
    last_sent = request.session.get(stamp_key)
    if last_sent:
        elapsed = timezone.now().timestamp() - last_sent
        if elapsed < RESEND_COOLDOWN_SECONDS:
            return "cooldown", int(RESEND_COOLDOWN_SECONDS - elapsed)
    if not otp_resend_allowed(user.id, purpose):
        return "capped", 0
    otp_record, code = EmailOTP.create_for_user(user, purpose=purpose)
    try:
        transaction.on_commit(lambda: send_task.delay(user.id, code))
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {e}")
        return "failed", 0
    request.session[stamp_key] = timezone.now().timestamp()
    return "sent", 0
