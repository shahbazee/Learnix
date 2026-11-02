from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views.generic import View

from ..models import UserProfile


class GoogleStartView(View):
    def get(self, request):
        role = request.GET.get("role", "")
        if role in ["student", "instructor"]:
            request.session["signup_role"] = role
        return redirect("google_login")


class RoleSelectView(LoginRequiredMixin, View):
    template_name = "accounts/role_select.html"

    def get(self, request):
        profile = getattr(request.user, "profile", None)
        if profile is not None and profile.role_selected:
            if profile.is_admin:
                return redirect("core:admin_dashboard")
            if profile.is_instructor:
                return redirect("courses:instructor_studio")
            return redirect("core:home")
        return render(request, self.template_name)

    def post(self, request):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return redirect("core:home")
        role = request.POST.get("role", "")
        if role not in ["student", "instructor"]:
            return redirect("accounts:role_select")
        if role == "student":
            profile.role = UserProfile.ROLE_STUDENT
            profile.role_selected = True
            profile.save()
            return redirect("core:home")
        return redirect("accounts:instructor_application")