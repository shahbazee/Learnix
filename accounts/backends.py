"""
Custom authentication backends for Learnix.
Allows users to log in using either their username OR their email address (case-insensitive).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    Allows authentication using either username OR email address (case-insensitive).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD) or kwargs.get('email')

        if not username or not password:
            return None

        clean_credential = str(username).strip()

        # Find user matching either username or email (case-insensitive)
        user = User.objects.filter(
            Q(username__iexact=clean_credential) | Q(email__iexact=clean_credential)
        ).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
