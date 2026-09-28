"""
Custom authentication backends for Learnix.
Allows users to log in using either their username OR their email address (case-insensitive).
"""

import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    Allows authentication using either username OR email address (case-insensitive).
    Resilient to duplicate email records by verifying password against all candidates.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD) or kwargs.get('email')

        if not username or not password:
            return None

        clean_credential = str(username).strip()

        # Find all candidates matching either username or email (case-insensitive)
        # Prioritize active accounts first, then most recently created/updated
        try:
            candidates = list(User.objects.filter(
                Q(username__iexact=clean_credential) | Q(email__iexact=clean_credential)
            ).order_by('-is_active', '-id'))
        except Exception as e:
            logger.error(f"[AUTH ERROR] Database query failed for '{clean_credential}': {e}")
            return None

        logger.info(
            f"[AUTH ATTEMPT] Credential: '{clean_credential}' | Found {len(candidates)} candidate(s): "
            f"{[(u.username, u.email, f'active={u.is_active}') for u in candidates]}"
        )

        for candidate in candidates:
            if candidate.check_password(password):
                # If password matches but account is inactive, check if they have a verified OTP
                if not candidate.is_active:
                    from accounts.models import EmailOTP
                    if EmailOTP.objects.filter(user=candidate, is_verified=True).exists():
                        candidate.is_active = True
                        candidate.save(update_fields=['is_active'])
                        logger.info(f"[AUTH AUTO-ACTIVATE] Activated user {candidate.username} ({candidate.email})")

                if self.user_can_authenticate(candidate):
                    logger.info(f"[AUTH SUCCESS] User '{candidate.username}' ({candidate.email}) authenticated.")
                    return candidate
                else:
                    logger.warning(f"[AUTH INACTIVE] User '{candidate.username}' password matched, but is_active=False.")

        logger.warning(f"[AUTH FAILED] Password mismatch for '{clean_credential}' across {len(candidates)} candidate(s).")
        return None
