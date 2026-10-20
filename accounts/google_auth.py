from django.contrib.auth import get_user_model

from .models import UserProfile

User = get_user_model()


def find_or_create_google_user(
    email, given_name="", family_name="", role=None
):
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
