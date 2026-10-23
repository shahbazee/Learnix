from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        profile = getattr(request.user, "profile", None)
        if profile is not None and profile.is_admin:
            return reverse("core:admin_dashboard")
        if profile is not None and profile.is_instructor:
            return reverse("courses:instructor_studio")
        return reverse("accounts:profile")
