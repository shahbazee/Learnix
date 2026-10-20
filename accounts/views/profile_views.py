import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import View

from ..models import UserProfile

logger = logging.getLogger(__name__)


class ProfileView(LoginRequiredMixin, View):
    template_name = "accounts/profile.html"

    def get_context(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        enrollments_count = (
            user.enrollments.filter(is_active=True).count()
            if hasattr(user, "enrollments")
            else 0
        )
        display_first_name = user.first_name or (
            user.username.split(".")[0].capitalize()
            if "." in user.username
            else user.username.capitalize()
        )
        display_last_name = user.last_name or (
            user.username.split(".")[1].capitalize()
            if "." in user.username
            else ""
        )
        payments = (
            user.payments.select_related("course", "invoice").order_by(
                "-created_at"
            )[:10]
            if hasattr(user, "payments")
            else []
        )
        return {
            "profile": profile,
            "user": user,
            "display_first_name": display_first_name,
            "display_last_name": display_last_name,
            "enrollments_count": enrollments_count,
            "payments": payments,
        }

    def get(self, request, *args, **kwargs):
        context = self.get_context(request.user)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

        is_ajax = request.headers.get(
            "x-requested-with"
        ) == "XMLHttpRequest" or "application/json" in request.headers.get(
            "Accept", ""
        )

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")

        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()

        pwd_response = self._handle_password_change(request, user, is_ajax)
        if pwd_response is not None:
            return pwd_response

        user.save()

        if "headline" in request.POST:
            profile.headline = request.POST.get("headline", "").strip()
        if "bio" in request.POST:
            profile.bio = request.POST.get("bio", "").strip()
        if "phone_number" in request.POST:
            profile.phone_number = request.POST.get("phone_number", "").strip()
        if "country_code" in request.POST:
            profile.country_code = request.POST.get(
                "country_code", "+1"
            ).strip()
        if "location_timezone" in request.POST:
            profile.location_timezone = request.POST.get(
                "location_timezone", ""
            ).strip()

        if "disconnect_google" in request.POST:
            profile.google_email = ""
        elif "google_email" in request.POST:
            profile.google_email = request.POST.get("google_email", "").strip()

        if "disconnect_github" in request.POST:
            profile.github_username = ""
        elif "github_username" in request.POST:
            profile.github_username = request.POST.get(
                "github_username", ""
            ).strip()

        if "two_factor_submitted" in request.POST:
            profile.two_factor_enabled = request.POST.get(
                "two_factor_enabled"
            ) in ["on", "true", "True", True, "1"]

        if "avatar" in request.FILES:
            profile.avatar = request.FILES["avatar"]
        elif request.POST.get("remove_avatar") == "true":
            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        profile.save()

        if is_ajax:
            return self._respond(
                request,
                is_ajax,
                True,
                "Account settings successfully saved.",
                avatar_url=(profile.avatar.url if profile.avatar else None),
                user_full_name=(
                    f"{user.first_name} {user.last_name}".strip()
                    or user.username
                ),
            )

        messages.success(request, "Account settings successfully saved.")
        return redirect("accounts:profile")

    def _handle_password_change(self, request, user, is_ajax):
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not (current_password or new_password or confirm_password):
            return None

        if not user.check_password(current_password):
            return self._respond(
                request, is_ajax, False, "Current password is incorrect."
            )
        if not new_password or len(new_password) < 8:
            return self._respond(
                request,
                is_ajax,
                False,
                "New password must be at least 8 characters.",
            )
        if new_password != confirm_password:
            return self._respond(
                request, is_ajax, False, "New passwords do not match."
            )

        user.set_password(new_password)
        update_session_auth_hash(request, user)
        return None

    def _respond(self, request, is_ajax, success, message, **extra):
        if is_ajax:
            payload = {"success": success, "message": message}
            payload.update(extra)
            return JsonResponse(payload)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect("accounts:profile")
