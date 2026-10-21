import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from google.auth.transport import requests as google_requests
from google.oauth2.id_token import verify_oauth2_token

from .models import UserProfile

User = get_user_model()

logger = logging.getLogger(__name__)


def verify_google_id_token(credential):
    try:
        return verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception:
        logger.warning("Google token verification failed")
        return None


def verified_google_email(id_info):
    email = (id_info.get("email") or "").strip().lower()
    if not email or id_info.get("email_verified") not in (True, "true"):
        return None
    return email


def find_or_create_google_user(
    email, given_name="", family_name="", role=None
):
    linked_profile = (
        UserProfile.objects.filter(google_email__iexact=email)
        .select_related("user")
        .first()
    )
    user = linked_profile.user if linked_profile else None
    if user is None:
        user = User.objects.filter(email__iexact=email).first()
    if user:
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        profile, _ = UserProfile.objects.get_or_create(user=user)
        is_linked = False
        if not profile.google_email:
            profile.google_email = email
            profile.save(update_fields=["google_email"])
            is_linked = True
        user.profile = profile
        return user, False, is_linked
    base_username = (
        given_name.lower().replace(" ", "")
        if given_name
        else email.split("@")[0]
    )
    clean_username = "".join(
        c for c in base_username if c.isalnum() or c in ["_", "."]
    )
    if not clean_username:
        clean_username = "student"
    username = clean_username
    counter = 1
    while User.objects.filter(username__iexact=username).exists():
        username = f"{clean_username}_{counter}"
        counter += 1
    user = User.objects.create(
        username=username,
        email=email,
        first_name=(given_name or email.split("@")[0].capitalize()),
        last_name=family_name or "Learner",
        is_active=True,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.google_email = email
    if role is not None:
        profile.role = (
            role if role in ["student", "instructor"] else "student"
        )
    profile.save()
    user.profile = profile
    return user, True, False
