import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = (
                kwargs.get(User.USERNAME_FIELD) or kwargs.get('email')
            )

        if not username or not password:
            return None

        clean_credential = str(username).strip()

        try:
            candidates = list(User.objects.filter(
                Q(username__iexact=clean_credential) |
                Q(email__iexact=clean_credential)
            ).order_by('-is_active', '-id'))
        except Exception as e:
            logger.error(
                f"[AUTH ERROR] Database query failed for "
                f"'{clean_credential}': {e}"
            )
            return None

        candidate_summary = [
            (u.username, u.email, f'active={u.is_active}')
            for u in candidates
        ]
        logger.info(
            f"[AUTH ATTEMPT] Credential: '{clean_credential}' | "
            f"Found {len(candidates)} candidate(s): {candidate_summary}"
        )

        for candidate in candidates:
            if candidate.check_password(password):
                if not candidate.is_active:
                    from accounts.models import EmailOTP
                    if EmailOTP.objects.filter(
                        user=candidate, is_verified=True
                    ).exists():
                        candidate.is_active = True
                        candidate.save(update_fields=['is_active'])
                        logger.info(
                            f"[AUTH AUTO-ACTIVATE] Activated user "
                            f"{candidate.username} ({candidate.email})"
                        )

                if self.user_can_authenticate(candidate):
                    logger.info(
                        f"[AUTH SUCCESS] User '{candidate.username}' "
                        f"({candidate.email}) authenticated."
                    )
                    return candidate
                else:
                    logger.warning(
                        f"[AUTH INACTIVE] User '{candidate.username}' "
                        f"password matched, but is_active=False."
                    )

        logger.warning(
            f"[AUTH FAILED] Password mismatch for '{clean_credential}' "
            f"across {len(candidates)} candidate(s)."
        )
        return None
