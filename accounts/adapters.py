from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

from .models import InstructorRegistrationRequest, UserProfile


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return reverse("accounts:profile")
        signup_role = request.session.pop("signup_role", None)
        if signup_role == "student" and not profile.role_selected:
            profile.role = UserProfile.ROLE_STUDENT
            profile.role_selected = True
            profile.save()
            return reverse("core:home")
        if signup_role == "instructor" and not profile.role_selected:
            return reverse("accounts:instructor_application")
        if not profile.role_selected:
            return reverse("accounts:role_select")
        pending = InstructorRegistrationRequest.objects.filter(
            user=request.user,
            status=InstructorRegistrationRequest.Status.PENDING,
        ).exists()
        if pending:
            return reverse("accounts:application_status")
        if profile.is_admin:
            return reverse("core:admin_dashboard")
        if profile.is_instructor:
            return reverse("courses:instructor_studio")
        return reverse("core:home")
