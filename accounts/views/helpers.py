from django.core import signing
from django.core.cache import cache

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
