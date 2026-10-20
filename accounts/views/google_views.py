import logging
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View

from ..google_auth import find_or_create_google_user

logger = logging.getLogger(__name__)


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


class GoogleLoginView(View):
    def get(self, request, *args, **kwargs):
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "").strip()
        client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret or client_id.startswith("your_"):
            messages.warning(
                request,
                "Google OAuth 2.0 is not yet configured. Please set "
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your "
                ".env file.",
            )
            referer = request.META.get("HTTP_REFERER")
            if referer and url_has_allowed_host_and_scheme(
                referer, allowed_hosts={request.get_host()}
            ):
                return redirect(referer)
            return redirect("accounts:login")

        state = secrets.token_urlsafe(32)
        request.session["google_oauth_state"] = state

        if request.GET.get("next"):
            request.session["google_oauth_next"] = request.GET.get("next")
        if request.GET.get("role"):
            request.session["google_oauth_role"] = request.GET.get("role")

        redirect_uri = request.build_absolute_uri(
            reverse_lazy("accounts:google_callback")
        )
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
            "access_type": "online",
        }
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"{urlencode(params)}"
        )
        return redirect(auth_url)


class GoogleCallbackView(View):
    def get(self, request, *args, **kwargs):
        if "error" in request.GET:
            error = request.GET.get("error")
            request.session.pop("google_oauth_state", None)
            request.session.pop("google_oauth_next", None)
            request.session.pop("google_oauth_role", None)
            if error in [
                "access_denied",
                "user_cancelled",
                "immediate_failed",
            ]:
                messages.info(request, "Google sign-in was cancelled.")
            else:
                messages.error(
                    request, f"Google authentication failed ({error})."
                )
            return redirect("accounts:login")

        state = request.GET.get("state")
        saved_state = request.session.pop("google_oauth_state", None)
        if not state or not saved_state or state != saved_state:
            messages.error(
                request,
                "OAuth security verification failed (state mismatch). "
                "Please try again.",
            )
            return redirect("accounts:login")

        code = request.GET.get("code")
        if not code:
            messages.error(
                request, "Authorization code missing from Google callback."
            )
            return redirect("accounts:login")

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "").strip()
        client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "").strip()
        redirect_uri = request.build_absolute_uri(
            reverse_lazy("accounts:google_callback")
        )

        token_data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            token_resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                timeout=10,
            )
            if token_resp.status_code != 200:
                messages.error(
                    request,
                    "Failed to exchange authorization token with "
                    "Google servers. Please verify Google credentials.",
                )
                return redirect("accounts:login")

            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                messages.error(
                    request, "Failed to retrieve access token from Google."
                )
                return redirect("accounts:login")

            userinfo_resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if userinfo_resp.status_code != 200:
                messages.error(
                    request,
                    "Failed to fetch user profile from Google account.",
                )
                return redirect("accounts:login")

            userinfo = userinfo_resp.json()
        except requests.RequestException:
            messages.error(
                request,
                "Network error communicating with Google "
                "authentication servers.",
            )
            return redirect("accounts:login")

        google_email = userinfo.get("email", "").strip().lower()
        if not google_email:
            messages.error(
                request, "Google account did not return a valid email address."
            )
            return redirect("accounts:login")

        if userinfo.get("email_verified") is False:
            messages.error(
                request, "Your Google email address is not verified by Google."
            )
            return redirect("accounts:login")

        given_name = userinfo.get("given_name", "")
        family_name = userinfo.get("family_name", "")
        next_url = request.session.pop("google_oauth_next", None)
        role = request.session.pop("google_oauth_role", "student")

        return complete_google_auth_login(
            request,
            google_email,
            given_name,
            family_name,
            next_url,
            role=role,
        )
