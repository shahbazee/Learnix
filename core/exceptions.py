"""
Learnix Custom Domain Exception Hierarchy.
Defines domain-specific platform exceptions per system specifications.
"""

class LearnixBaseException(Exception):
    """Base exception for all domain-specific platform errors."""
    def __init__(self, message="An internal business logic error occurred.", code="INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class PaymentVerificationFailedException(LearnixBaseException):
    """Raised when Stripe webhook signature or charge verification fails."""
    def __init__(self, message="The payment verification check failed."):
        super().__init__(message=message, code="PAYMENT_VERIFICATION_FAILED")


class CourseAccessDeniedException(LearnixBaseException):
    """Raised when a student attempts unauthorized lesson access."""
    def __init__(self, message="Enrollment required to access course content."):
        super().__init__(message=message, code="ACCESS_DENIED")


class OTPExpiredException(LearnixBaseException):
    """Raised when an OTP submission exceeds the permitted validity window."""
    def __init__(self, message="This OTP has expired. Please request a new verification code."):
        super().__init__(message=message, code="OTP_EXPIRED")
