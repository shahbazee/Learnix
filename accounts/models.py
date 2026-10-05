import secrets

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class UserProfile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_INSTRUCTOR = 'instructor'
    ROLE_CHOICES = (
        (ROLE_STUDENT, 'Student'),
        (ROLE_INSTRUCTOR, 'Instructor'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        db_index=True,
        help_text="Role distinguishing students from course instructors"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True
    )
    bio = models.TextField(blank=True, default='')
    headline = models.CharField(max_length=255, blank=True, default='')
    phone_number = models.CharField(max_length=30, blank=True, default='')
    country_code = models.CharField(max_length=10, blank=True, default='+1')
    location_timezone = models.CharField(
        max_length=150,
        blank=True,
        default='San Francisco, CA · Pacific Daylight (UTC-7)'
    )
    academic_suffix = models.CharField(max_length=50, blank=True, default='')
    public_directory = models.BooleanField(default=True)
    google_email = models.CharField(max_length=255, blank=True, default='')
    github_username = models.CharField(max_length=100, blank=True, default='')
    storage_used_gb = models.FloatField(default=12.4)
    storage_total_gb = models.FloatField(default=50.0)
    two_factor_enabled = models.BooleanField(default=True)
    preferred_currency = models.CharField(max_length=10, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.role})"

    @property
    def is_instructor(self) -> bool:
        return self.role == self.ROLE_INSTRUCTOR

    @property
    def is_student(self) -> bool:
        return self.role == self.ROLE_STUDENT


class EmailOTP(models.Model):
    MAX_ATTEMPTS = 5
    EXPIRY_MINUTES = 10

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_otps'
    )
    otp_code = models.CharField(max_length=6, db_index=True)
    purpose = models.CharField(
        max_length=30,
        default='registration',
        choices=[
            ('registration', 'Registration Verification'),
            ('password_reset', 'Password Reset Verification'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    attempts_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'otp_code']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['user', 'purpose', 'is_verified']),
        ]

    def __str__(self):
        return (
            f"OTP ({self.purpose}) for {self.user.username} "
            f"({'Verified' if self.is_verified else 'Pending'})"
        )

    @classmethod
    def create_for_user(cls, user, purpose='registration'):
        cls.objects.filter(
            user=user, purpose=purpose, is_verified=False
        ).delete()

        digits = "0123456789"
        code = "".join(secrets.choice(digits) for _ in range(6))
        expires_at = timezone.now() + timedelta(minutes=cls.EXPIRY_MINUTES)

        return cls.objects.create(
            user=user,
            otp_code=code,
            purpose=purpose,
            expires_at=expires_at,
            is_verified=False,
            attempts_count=0
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_locked(self) -> bool:
        return self.attempts_count >= self.MAX_ATTEMPTS
