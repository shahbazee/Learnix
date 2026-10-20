import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, View

from ..forms import OTPVerificationForm, StudentRegistrationForm, UserLoginForm
from ..models import UserProfile
from ..otp_utils import create_and_send_otp, verify_otp
from ..tasks import send_otp_email, send_welcome_email
from .helpers import (
    _generate_otp_token,
    resend_otp_code,
    resolve_otp_user_id,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class SignUpView(FormView):
    template_name = "accounts/signup.html"
    form_class = StudentRegistrationForm
    success_url = reverse_lazy("accounts:verify_otp")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        submitted_email = str(request.POST.get("email", "")).strip().lower()
        if submitted_email:
            active_user = User.objects.filter(
                email__iexact=submitted_email, is_active=True
            ).first()
            if not active_user:
                unverified_user = User.objects.filter(
                    email__iexact=submitted_email, is_active=False
                ).first()
                if unverified_user:
                    form = self.get_form()
                    if form.is_valid():
                        return self.form_valid(form)
                    else:
                        return self._dispatch_unverified_otp_and_redirect(
                            unverified_user
                        )
        return super().post(request, *args, **kwargs)

    def _dispatch_unverified_otp_and_redirect(self, user):
        create_and_send_otp(user, "registration", send_otp_email)
        token = _generate_otp_token(user.id)

        self.request.session["otp_user_id"] = user.id
        self.request.session["otp_token"] = token
        self.request.session.modified = True

        self.request.session["otp_last_sent"] = timezone.now().timestamp()
        messages.success(
            self.request,
            f"Your account is pending verification. A fresh verification "
            f"code has been dispatched to {user.email}.",
        )
        verify_url = f"{reverse('accounts:verify_otp')}?token={token}"
        return redirect(verify_url)

    def form_valid(self, form):
        is_re_registration = bool(form.instance and form.instance.pk)

        with transaction.atomic():
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data["password"])
            user.save()

            role = form.cleaned_data.get("role", "student")
            if role not in ["student", "instructor"]:
                role = "student"
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save(update_fields=["role"])

            create_and_send_otp(user, "registration", send_otp_email)

        token = _generate_otp_token(user.id)
        self.request.session["otp_user_id"] = user.id
        self.request.session["otp_token"] = token
        self.request.session.modified = True

        try:
            self.request.session["otp_last_sent"] = timezone.now().timestamp()
            if is_re_registration:
                messages.success(
                    self.request,
                    f"Your account is pending verification. A fresh "
                    f"verification code has been dispatched to {user.email}.",
                )
            else:
                messages.success(
                    self.request,
                    f"Verification code sent to {user.email}. Enter the "
                    f"6-digit code to activate your account.",
                )
        except Exception as e:
            logger.error(
                f"Error invoking send_otp_verification_email for "
                f"{user.email}: {e}"
            )
            messages.warning(
                self.request,
                f"Account pending verification. If you do not receive the "
                f"email at {user.email} shortly, please click "
                f"'Resend Verification Code' below.",
            )

        verify_url = f"{reverse('accounts:verify_otp')}?token={token}"
        return redirect(verify_url)


class VerifyOTPView(FormView):
    template_name = "accounts/verify_otp.html"
    form_class = OTPVerificationForm
    success_url = reverse_lazy("courses:course_list")

    def dispatch(self, request, *args, **kwargs):
        user_id = resolve_otp_user_id(request)

        if not user_id:
            messages.error(
                request, "Registration session expired. Please sign up again."
            )
            return redirect("accounts:signup")

        user = User.objects.filter(id=user_id).first()
        if not user:
            request.session.pop("otp_user_id", None)
            messages.error(
                request, "Registration session expired. Please sign up again."
            )
            return redirect("accounts:signup")

        if user.is_active:
            request.session.pop("otp_user_id", None)
            request.session.pop("otp_last_sent", None)
            messages.info(
                request,
                "Your account has already been verified. Please sign in.",
            )
            return redirect("accounts:login")

        return super().dispatch(request, *args, **kwargs)

    def get_user(self):
        return get_object_or_404(User, id=resolve_otp_user_id(self.request))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user()
        context["pending_user"] = user
        context["pending_email"] = user.email if user else ""
        context["token"] = self.request.GET.get(
            "token"
        ) or self.request.POST.get("token", "")
        return context

    def form_valid(self, form):
        user = self.get_user()
        submitted_code = form.cleaned_data["otp_code"]

        success, error, _ = verify_otp(user, submitted_code, "registration")
        if not success:
            form.add_error("otp_code", error)
            return self.form_invalid(form)

        user.is_active = True
        user.save(update_fields=["is_active"])

        login(
            self.request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        self.request.session.pop("otp_user_id", None)
        self.request.session.pop("otp_last_sent", None)

        transaction.on_commit(lambda: send_welcome_email.delay(user.id))

        messages.success(
            self.request,
            f"Account verified! Welcome to {settings.SITE_NAME}, "
            f"{user.first_name or user.username}.",
        )
        return redirect(self.get_success_url())


class ResendOTPView(View):
    def post(self, request, *args, **kwargs):
        user_id = resolve_otp_user_id(request)
        if not user_id:
            messages.error(request, "Session expired. Please register again.")
            return redirect("accounts:signup")

        user = get_object_or_404(User, id=user_id)
        if user.is_active:
            messages.info(
                request, "This account is already verified. Please sign in."
            )
            return redirect("accounts:login")

        token = request.POST.get("token") or _generate_otp_token(user.id)
        target_url = f"{reverse('accounts:verify_otp')}?token={token}"

        result, remaining = resend_otp_code(
            request, user, "registration", "otp_last_sent", send_otp_email
        )
        if result == "cooldown":
            messages.warning(
                request,
                f"Please wait {remaining} seconds before "
                f"requesting a new code.",
            )
        elif result == "capped":
            messages.error(
                request,
                "Too many code requests. Please try again in an hour.",
            )
        elif result == "failed":
            messages.warning(
                request,
                "Could not send verification email. Please check your "
                "network or try again in a moment.",
            )
        else:
            messages.info(
                request,
                f"A fresh verification code has been dispatched "
                f"to {user.email}.",
            )
        return redirect(target_url)


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get("next") or self.request.POST.get(
            "next"
        )
        if next_url:
            return next_url
        user = self.request.user
        if hasattr(user, "profile") and user.profile.is_instructor:
            return reverse_lazy("courses:instructor_studio")
        return reverse_lazy("accounts:profile")

    def form_valid(self, form):
        user = form.get_user()
        messages.success(
            self.request, f"Welcome back, {user.first_name or user.username}!"
        )
        return super().form_valid(form)


class UserLogoutView(View):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            request.session.flush()
            messages.info(
                request, "You have been logged out of your Learnix session."
            )
        return redirect("core:home")
