from .models import EmailOTP 

def verify_otp(user, code, purpose):
    """Returns (success: bool, error_message: str | None, otp_record)"""
    otp_record = EmailOTP.objects.filter(
        user=user, purpose=purpose, is_verified=False
    ).first()

    if not otp_record or otp_record.is_expired:
        return False, "This code has expired. Please request a new one.", otp_record
    if otp_record.is_locked:
        return False, "Security threshold exceeded (5 failed attempts).", otp_record
    if otp_record.otp_code != code:
        otp_record.attempts_count += 1
        otp_record.save(update_fields=['attempts_count'])
        remaining = EmailOTP.MAX_ATTEMPTS - otp_record.attempts_count
        return False, f"Incorrect code. {remaining} attempt(s) remaining.", otp_record

    otp_record.is_verified = True
    otp_record.save(update_fields=['is_verified'])
    return True, None, otp_record
