import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View
from google.auth.transport import requests as google_requests
from google.oauth2.id_token import verify_oauth2_token

from ..google_auth import find_or_create_google_user
from ..models import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


def complete_google_auth_login(
    request,
    google_email,
    given_name="",
    family_name="",
    next_url=None,
    role="student",
):
    google_email = google_email.strip().lower()
    user, is_new_user, is_linked_user = find_or_create_google_user(
        google_email, given_name, family_name, role=role
    )

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    if is_new_user:
        target_redirect = reverse_lazy("core:home")
    elif next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        target_redirect = next_url
    elif hasattr(user, "profile") and user.profile.is_instructor:
        target_redirect = reverse_lazy("courses:instructor_studio")
    else:
        target_redirect = reverse_lazy("accounts:profile")

    if is_new_user:
        messages.success(
            request,
            f"Welcome to "
            f"{getattr(settings, 'SITE_NAME', 'Learnix')}, "
            f"{user.first_name or user.username}! Your account has been "
            f"verified and created via Google.",
        )
    elif is_linked_user:
        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}! "
            f"Your Google account has been linked to your existing "
            f"Learnix account.",
        )
    else:
        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}! "
            f"Signed in via Google.",
        )

    return redirect(target_redirect)


class GoogleCompleteView(View):
    def post(self, request, *args, **kwargs):
        credential = request.POST.get("credential", "")
        try:
            id_info = verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception:
            logger.warning("Google GIS token verification failed")
            return self._error(
                request, "Invalid Google token. Please try again."
            )

        email = (id_info.get("email") or "").strip().lower()
        if not email or id_info.get("email_verified") not in (True, "true"):
            return self._error(
                request,
                "Your Google email address is not verified by Google.",
            )

        if request.user.is_authenticated:
            return self._link_google_account(request, email)

        return complete_google_auth_login(
            request,
            email,
            id_info.get("given_name") or "",
            id_info.get("family_name") or "",
            request.POST.get("next") or None,
            role=request.POST.get("role") or "student",
        )

    def _error(self, request, message):
        messages.error(request, message)
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return redirect("accounts:login")

    def _link_google_account(self, request, email):
        other_user = (
            User.objects.filter(email__iexact=email)
            .exclude(pk=request.user.pk)
            .exists()
        )
        linked_elsewhere = (
            UserProfile.objects.filter(google_email__iexact=email)
            .exclude(user=request.user)
            .exists()
        )
        if other_user or linked_elsewhere:
            return self._error(
                request,
                "This Google account is already linked to another "
                "Learnix account.",
            )
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.google_email = email
        profile.save(update_fields=["google_email"])
        messages.success(
            request, "Your Google account has been connected."
        )
        return redirect("accounts:profile")
