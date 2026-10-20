import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, View

from ..forms import (
    ForgotPasswordRequestForm,
    OTPVerificationForm,
    SetNewPasswordForm,
)
from ..models import EmailOTP
from ..otp_utils import verify_otp
from ..tasks import send_password_changed_email_task, send_password_reset_email
from .helpers import otp_resend_allowed

User = get_user_model()
logger = logging.getLogger(__name__)


class ForgotPasswordView(FormView):
    template_name = "accounts/forgot_password.html"
    form_class = ForgotPasswordRequestForm
    success_url = reverse_lazy("accounts:verify_reset_otp")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        self.request.session["reset_email"] = email

        if user:
            otp_record, code = EmailOTP.create_for_user(
                user, purpose="password_reset"
            )
            self.request.session["reset_user_id"] = user.id
            self.request.session["reset_otp_last_sent"] = (
                timezone.now().timestamp()
            )

            transaction.on_commit(
                lambda: send_password_reset_email.delay(user.id, code)
            )
        else:
            self.request.session.pop("reset_user_id", None)

        messages.info(
            self.request,
            "If an active account is registered with that email, "
            "a 6-digit reset code has been dispatched.",
        )
        return super().form_valid(form)


class VerifyResetOTPView(FormView):
    template_name = "accounts/verify_reset_otp.html"
    form_class = OTPVerificationForm
    success_url = reverse_lazy("accounts:reset_password")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        if not request.session.get("reset_email"):
            messages.error(
                request,
                "Password reset session expired. Please enter your email.",
            )
            return redirect("accounts:forgot_password")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reset_email"] = self.request.session.get("reset_email", "")
        return context

    def form_valid(self, form):
        user_id = self.request.session.get("reset_user_id")
        if not user_id:
            form.add_error(
                "otp_code",
                "Invalid verification session. " "Please request a new code.",
            )
            return self.form_invalid(form)

        user = get_object_or_404(User, id=user_id)
        submitted_code = form.cleaned_data["otp_code"]

        success, error, _ = verify_otp(user, submitted_code, "password_reset")
        if not success:
            form.add_error("otp_code", error)
            return self.form_invalid(form)

        self.request.session["reset_otp_verified"] = True

        messages.success(
            self.request,
            "Code verified! Please create your new secure password.",
        )
        return super().form_valid(form)


class ResendResetOTPView(View):
    RATE_LIMIT_SECONDS = 60

    def post(self, request, *args, **kwargs):
        user_id = request.session.get("reset_user_id")
        if not user_id:
            messages.error(
                request, "Password reset session expired. Please start over."
            )
            return redirect("accounts:forgot_password")

        user = get_object_or_404(User, id=user_id)

        last_sent = request.session.get("reset_otp_last_sent")
        if last_sent:
            elapsed = timezone.now().timestamp() - last_sent
            if elapsed < self.RATE_LIMIT_SECONDS:
                remaining = int(self.RATE_LIMIT_SECONDS - elapsed)
                messages.warning(
                    request,
                    f"Please wait {remaining} seconds before "
                    f"requesting a new code.",
                )
                return redirect("accounts:verify_reset_otp")

        if not otp_resend_allowed(user.id, "password_reset"):
            messages.error(
                request,
                "Too many code requests. Please try again in an hour.",
            )
            return redirect("accounts:verify_reset_otp")

        otp_record, code = EmailOTP.create_for_user(
            user, purpose="password_reset"
        )
        request.session["reset_otp_last_sent"] = timezone.now().timestamp()

        transaction.on_commit(
            lambda: send_password_reset_email.delay(user.id, code)
        )

        messages.info(
            request, "A fresh password reset code has been sent to your email."
        )
        return redirect("accounts:verify_reset_otp")


class ResetPasswordView(FormView):
    template_name = "accounts/reset_password.html"
    form_class = SetNewPasswordForm
    success_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        if not request.session.get(
            "reset_otp_verified"
        ) or not request.session.get("reset_user_id"):
            messages.error(
                request,
                "Unauthorized password reset attempt. "
                "Please verify your email first.",
            )
            return redirect("accounts:forgot_password")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user_id = self.request.session.get("reset_user_id")
        if user_id:
            kwargs["user"] = User.objects.filter(id=user_id).first()
        return kwargs

    def form_valid(self, form):
        user_id = self.request.session.get("reset_user_id")
        user = get_object_or_404(User, id=user_id)
        new_password = form.cleaned_data["password"]

        user.set_password(new_password)
        user.is_active = True
        user.save()

        EmailOTP.objects.filter(user=user, purpose="password_reset").delete()

        transaction.on_commit(
            lambda: send_password_changed_email_task.delay(user.id)
        )

        self.request.session.pop("reset_user_id", None)
        self.request.session.pop("reset_email", None)
        self.request.session.pop("reset_otp_verified", None)
        self.request.session.pop("reset_otp_last_sent", None)

        login(
            self.request,
            user,
            backend="accounts.backends.EmailOrUsernameModelBackend",
        )

        messages.success(
            self.request,
            f"Your password has been successfully updated! "
            f"Welcome back, {user.first_name or user.username}.",
        )
        return redirect("accounts:profile")
