import secrets
import requests
import logging
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.core import signing
from django.views.generic import FormView, View
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

from django.contrib.auth import update_session_auth_hash
from .otp_utils import verify_otp
from .models import UserProfile, EmailOTP
from .forms import (
    StudentRegistrationForm,
    OTPVerificationForm,
    UserLoginForm,
    ForgotPasswordRequestForm,
    SetNewPasswordForm
)
from core.emails import (
    send_registration_success_email,
    send_otp_verification_email,
    send_forgot_password_otp_email,
    send_password_changed_email,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _generate_otp_token(user_id):
    return signing.dumps(user_id, salt='learnix_otp_verify')


def _decode_otp_token(token):
    return signing.loads(token, salt='learnix_otp_verify', max_age=1800)


class SignUpView(FormView):
    template_name = 'accounts/signup.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('accounts:verify_otp')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        submitted_email = str(request.POST.get('email', '')).strip().lower()
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
        otp_record = EmailOTP.create_for_user(user, purpose='registration')
        token = _generate_otp_token(user.id)

        self.request.session['otp_user_id'] = user.id
        self.request.session['otp_token'] = token
        self.request.session.modified = True

        email_sent = False
        try:
            email_sent = send_otp_verification_email(
                user, otp_record.otp_code, async_send=True
            )
            if email_sent:
                self.request.session['otp_last_sent'] = (
                    timezone.now().timestamp()
                )
        except Exception as e:
            logger.error(
                f"Error invoking send_otp_verification_email for "
                f"{user.email}: {e}"
            )

        if email_sent:
            messages.success(
                self.request,
                f"Your account is pending verification. A fresh verification "
                f"code has been dispatched to {user.email}."
            )
        else:
            messages.warning(
                self.request,
                f"Account pending verification. If you do not receive the "
                f"email at {user.email} shortly, please click "
                f"'Resend Verification Code' below."
            )
        verify_url = f"{reverse('accounts:verify_otp')}?token={token}"
        return redirect(verify_url)

    def form_valid(self, form):
        is_re_registration = bool(form.instance and form.instance.pk)

        with transaction.atomic():
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data['password'])
            user.save()

            role = form.cleaned_data.get('role', 'student')
            if role not in ['student', 'instructor']:
                role = 'student'
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save(update_fields=['role'])

            otp_record = EmailOTP.create_for_user(
                user, purpose='registration'
            )

        token = _generate_otp_token(user.id)
        self.request.session['otp_user_id'] = user.id
        self.request.session['otp_token'] = token
        self.request.session.modified = True

        try:
            send_otp_verification_email(
                user, otp_record.otp_code, async_send=True
            )
            self.request.session['otp_last_sent'] = (
                timezone.now().timestamp()
            )
            if is_re_registration:
                messages.success(
                    self.request,
                    f"Your account is pending verification. A fresh "
                    f"verification code has been dispatched to {user.email}."
                )
            else:
                messages.success(
                    self.request,
                    f"Verification code sent to {user.email}. Enter the "
                    f"6-digit code to activate your account."
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
                f"'Resend Verification Code' below."
            )

        verify_url = f"{reverse('accounts:verify_otp')}?token={token}"
        return redirect(verify_url)


class VerifyOTPView(FormView):
    template_name = 'accounts/verify_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('courses:course_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:home')

        user_id = request.session.get('otp_user_id')
        token = request.GET.get('token') or request.POST.get('token')

        if not user_id and token:
            try:
                user_id = _decode_otp_token(token)
                request.session['otp_user_id'] = user_id
                request.session.modified = True
            except (signing.BadSignature, signing.SignatureExpired):
                user_id = None

        if not user_id:
            messages.error(
                request, "Registration session expired. Please sign up again."
            )
            return redirect('accounts:signup')

        user = User.objects.filter(id=user_id).first()
        if not user:
            request.session.pop('otp_user_id', None)
            messages.error(
                request, "Registration session expired. Please sign up again."
            )
            return redirect('accounts:signup')

        if user.is_active:
            request.session.pop('otp_user_id', None)
            request.session.pop('otp_last_sent', None)
            messages.info(
                request,
                "Your account has already been verified. Please sign in."
            )
            return redirect('accounts:login')

        return super().dispatch(request, *args, **kwargs)

    def get_user(self):
        user_id = self.request.session.get('otp_user_id')
        token = (
            self.request.GET.get('token') or
            self.request.POST.get('token')
        )
        if not user_id and token:
            try:
                user_id = _decode_otp_token(token)
                self.request.session['otp_user_id'] = user_id
            except Exception:
                pass
        return get_object_or_404(User, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user()
        context['pending_user'] = user
        context['pending_email'] = user.email if user else ""
        context['token'] = (
            self.request.GET.get('token') or
            self.request.POST.get('token', '')
        )
        return context

    def form_valid(self, form):
        user = self.get_user()
        submitted_code = form.cleaned_data['otp_code']
        
        success, error, _ = verify_otp(user, submitted_code, 'registration')
        if not success:
            form.add_error('otp_code', error)
            return self.form_invalid(form)


        user.is_active = True
        user.save(update_fields=['is_active'])

        login(
            self.request, user,
            backend='django.contrib.auth.backends.ModelBackend'
        )

        self.request.session.pop('otp_user_id', None)
        self.request.session.pop('otp_last_sent', None)

        try:
            send_registration_success_email(user, async_send=True)
        except Exception as e:
            logger.error(
                f"Failed to dispatch registration success email: {e}"
            )

        messages.success(
            self.request,
            f"Account verified! Welcome to {settings.SITE_NAME}, "
            f"{user.first_name or user.username}."
        )
        return redirect(self.get_success_url())


class ResendOTPView(View):
    RATE_LIMIT_SECONDS = 60

    def post(self, request, *args, **kwargs):
        user_id = request.session.get('otp_user_id')
        token = request.POST.get('token') or request.GET.get('token')

        if not user_id and token:
            try:
                user_id = _decode_otp_token(token)
                request.session['otp_user_id'] = user_id
                request.session.modified = True
            except Exception:
                user_id = None

        if not user_id:
            messages.error(
                request, "Session expired. Please register again."
            )
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)
        if user.is_active:
            messages.info(
                request,
                "This account is already verified. Please sign in."
            )
            return redirect('accounts:login')

        token = token or _generate_otp_token(user.id)
        last_sent = request.session.get('otp_last_sent')
        if last_sent:
            elapsed = timezone.now().timestamp() - last_sent
            if elapsed < self.RATE_LIMIT_SECONDS:
                remaining = int(self.RATE_LIMIT_SECONDS - elapsed)
                messages.warning(
                    request,
                    f"Please wait {remaining} seconds before "
                    f"requesting a new code."
                )
                target_url = (
                    f"{reverse('accounts:verify_otp')}?token={token}"
                    if token
                    else reverse('accounts:verify_otp')
                )
                return redirect(target_url)

        otp_record = EmailOTP.create_for_user(user, purpose='registration')

        try:
            send_otp_verification_email(
                user, otp_record.otp_code, async_send=True
            )
            request.session['otp_last_sent'] = timezone.now().timestamp()
            messages.info(
                request,
                f"A fresh verification code has been dispatched "
                f"to {user.email}."
            )
        except Exception as e:
            logger.error(
                f"Failed to resend OTP verification email "
                f"to {user.email}: {e}"
            )
            messages.warning(
                request,
                "Could not send verification email. Please check your "
                "network or try again in a moment."
            )

        target_url = (
            f"{reverse('accounts:verify_otp')}?token={token}"
            if token
            else reverse('accounts:verify_otp')
        )
        return redirect(target_url)


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = (
            self.request.GET.get('next') or
            self.request.POST.get('next')
        )
        if next_url:
            return next_url
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.is_instructor:
            return reverse_lazy('courses:instructor_studio')
        return reverse_lazy('accounts:profile')

    def form_valid(self, form):
        user = form.get_user()
        messages.success(
            self.request,
            f"Welcome back, {user.first_name or user.username}!"
        )
        return super().form_valid(form)


class UserLogoutView(View):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            request.session.flush()
            messages.info(
                request,
                "You have been logged out of your Learnix session."
            )
        return redirect('core:home')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            request.session.flush()
            messages.info(
                request,
                "You have been logged out of your Learnix session."
            )
        return redirect('core:home')


class ForgotPasswordView(FormView):
    template_name = 'accounts/forgot_password.html'
    form_class = ForgotPasswordRequestForm
    success_url = reverse_lazy('accounts:verify_reset_otp')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = User.objects.filter(
            email__iexact=email, is_active=True
        ).first()

        self.request.session['reset_email'] = email

        if user:
            otp_record = EmailOTP.create_for_user(
                user, purpose='password_reset'
            )
            self.request.session['reset_user_id'] = user.id
            self.request.session['reset_otp_last_sent'] = (
                timezone.now().timestamp()
            )

            send_forgot_password_otp_email(
                user, otp_record.otp_code, async_send=True
            )
        else:
            self.request.session.pop('reset_user_id', None)

        messages.info(
            self.request,
            "If an active account is registered with that email, "
            "a 6-digit reset code has been dispatched."
        )
        return super().form_valid(form)


class VerifyResetOTPView(FormView):
    template_name = 'accounts/verify_reset_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('accounts:reset_password')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        if not request.session.get('reset_email'):
            messages.error(
                request,
                "Password reset session expired. Please enter your email."
            )
            return redirect('accounts:forgot_password')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reset_email'] = self.request.session.get('reset_email', '')
        return context

    def form_valid(self, form):
        user_id = self.request.session.get('reset_user_id')
        if not user_id:
            form.add_error(
                'otp_code',
                "Invalid verification session. "
                "Please request a new code."
            )
            return self.form_invalid(form)

        user = get_object_or_404(User, id=user_id)
        submitted_code = form.cleaned_data['otp_code']
        
        success, error, _ = verify_otp(user, submitted_code, 'password_reset')
        if not success:
            form.add_error('otp_code', error)
            return self.form_invalid(form)

        self.request.session['reset_otp_verified'] = True

        messages.success(
            self.request,
            "Code verified! Please create your new secure password."
        )
        return super().form_valid(form)


class ResendResetOTPView(View):
    RATE_LIMIT_SECONDS = 60

    def post(self, request, *args, **kwargs):
        user_id = request.session.get('reset_user_id')
        if not user_id:
            messages.error(
                request,
                "Password reset session expired. Please start over."
            )
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)

        last_sent = request.session.get('reset_otp_last_sent')
        if last_sent:
            elapsed = timezone.now().timestamp() - last_sent
            if elapsed < self.RATE_LIMIT_SECONDS:
                remaining = int(self.RATE_LIMIT_SECONDS - elapsed)
                messages.warning(
                    request,
                    f"Please wait {remaining} seconds before "
                    f"requesting a new code."
                )
                return redirect('accounts:verify_reset_otp')

        otp_record = EmailOTP.create_for_user(
            user, purpose='password_reset'
        )
        request.session['reset_otp_last_sent'] = timezone.now().timestamp()

        send_forgot_password_otp_email(
            user, otp_record.otp_code, async_send=True
        )

        messages.info(
            request,
            "A fresh password reset code has been sent to your email."
        )
        return redirect('accounts:verify_reset_otp')


class ResetPasswordView(FormView):
    template_name = 'accounts/reset_password.html'
    form_class = SetNewPasswordForm
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        if (
            not request.session.get('reset_otp_verified') or
            not request.session.get('reset_user_id')
        ):
            messages.error(
                request,
                "Unauthorized password reset attempt. "
                "Please verify your email first."
            )
            return redirect('accounts:forgot_password')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user_id = self.request.session.get('reset_user_id')
        if user_id:
            kwargs['user'] = User.objects.filter(id=user_id).first()
        return kwargs

    def form_valid(self, form):
        user_id = self.request.session.get('reset_user_id')
        user = get_object_or_404(User, id=user_id)
        new_password = form.cleaned_data['password']

        user.set_password(new_password)
        user.is_active = True
        user.save()

        EmailOTP.objects.filter(
            user=user, purpose='password_reset'
        ).delete()

        send_password_changed_email(user, async_send=True)

        self.request.session.pop('reset_user_id', None)
        self.request.session.pop('reset_email', None)
        self.request.session.pop('reset_otp_verified', None)
        self.request.session.pop('reset_otp_last_sent', None)

        login(
            self.request, user,
            backend='accounts.backends.EmailOrUsernameModelBackend'
        )

        messages.success(
            self.request,
            f"Your password has been successfully updated! "
            f"Welcome back, {user.first_name or user.username}."
        )
        return redirect('accounts:profile')

class ProfileView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get_context(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        enrollments_count = (
            user.enrollments.filter(is_active=True).count()
            if hasattr(user, 'enrollments') else 0
        )
        display_first_name = user.first_name or (
            user.username.split('.')[0].capitalize()
            if '.' in user.username
            else user.username.capitalize()
        )
        display_last_name = user.last_name or (
            user.username.split('.')[1].capitalize()
            if '.' in user.username
            else ""
        )
        payments = (
            user.payments.select_related('course', 'invoice')
            .order_by('-created_at')[:10]
            if hasattr(user, 'payments') else []
        )
        return {
            'profile': profile,
            'user': user,
            'display_first_name': display_first_name,
            'display_last_name': display_last_name,
            'enrollments_count': enrollments_count,
            'payments': payments,
        }

    def get(self, request, *args, **kwargs):
        context = self.get_context(request.user)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('Accept', '')
        )

        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()

        pwd_response = self._handle_password_change(request, user, is_ajax)
        if pwd_response is not None:
            return pwd_response

        user.save()

        if 'headline' in request.POST:
            profile.headline = request.POST.get('headline', '').strip()
        if 'bio' in request.POST:
            profile.bio = request.POST.get('bio', '').strip()
        if 'phone_number' in request.POST:
            profile.phone_number = request.POST.get(
                'phone_number', ''
            ).strip()
        if 'country_code' in request.POST:
            profile.country_code = request.POST.get(
                'country_code', '+1'
            ).strip()
        if 'location_timezone' in request.POST:
            profile.location_timezone = request.POST.get(
                'location_timezone', ''
            ).strip()

        if 'disconnect_google' in request.POST:
            profile.google_email = ''
        elif 'google_email' in request.POST:
            profile.google_email = request.POST.get(
                'google_email', ''
            ).strip()

        if 'disconnect_github' in request.POST:
            profile.github_username = ''
        elif 'github_username' in request.POST:
            profile.github_username = request.POST.get(
                'github_username', ''
            ).strip()

        if 'two_factor_submitted' in request.POST:
            profile.two_factor_enabled = (
                request.POST.get('two_factor_enabled') in [
                    'on', 'true', 'True', True, '1'
                ]
            )

        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        elif request.POST.get('remove_avatar') == 'true':
            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        profile.save()

        if is_ajax:
            return self._respond(
                request, is_ajax, True, 'Account settings successfully saved.',
                avatar_url=(profile.avatar.url if profile.avatar else None),
                user_full_name=(
                    f"{user.first_name} {user.last_name}".strip()
                    or user.username
                ),
            )

        messages.success(request, 'Account settings successfully saved.')
        return redirect('accounts:profile')

    def _handle_password_change(self, request, user, is_ajax):
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not (current_password or new_password or confirm_password):
            return None

        if not user.check_password(current_password):
            return self._respond(request, is_ajax, False,
                                 'Current password is incorrect.')
        if not new_password or len(new_password) < 8:
            return self._respond(request, is_ajax, False,
                                 'New password must be at least 8 characters.')
        if new_password != confirm_password:
            return self._respond(request, is_ajax, False,
                                 'New passwords do not match.')

        user.set_password(new_password)
        update_session_auth_hash(request, user)
        return None

    def _respond(self, request, is_ajax, success, message, **extra):
        if is_ajax:
            payload = {'success': success, 'message': message}
            payload.update(extra)
            return JsonResponse(payload)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('accounts:profile')


def complete_google_auth_login(
    request, google_email, given_name='', family_name='',
    next_url=None, role='student', avatar_url=''
):
    google_email = google_email.strip().lower()
    user = User.objects.filter(email__iexact=google_email).first()
    is_new_user = False
    is_linked_user = False

    if user:
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.google_email:
            profile.google_email = google_email
            is_linked_user = True
        profile.save()
        user.profile = profile
    else:
        is_new_user = True
        base_username = (
            given_name.lower().replace(' ', '')
            if given_name
            else google_email.split('@')[0]
        )
        clean_username = ''.join(
            c for c in base_username if c.isalnum() or c in ['_', '.']
        )
        if not clean_username:
            clean_username = 'student'

        username = clean_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{clean_username}_{counter}"
            counter += 1

        user = User.objects.create(
            username=username,
            email=google_email,
            first_name=(
                given_name or google_email.split('@')[0].capitalize()
            ),
            last_name=family_name or 'Learner',
            is_active=True
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])

        assigned_role = (
            role if role in ['student', 'instructor'] else 'student'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.google_email = google_email
        profile.role = assigned_role
        profile.headline = (
            "Masterclass Instructor"
            if assigned_role == 'instructor'
            else "Engineering Fellow"
        )
        profile.location_timezone = (
            "San Francisco, CA · Pacific Daylight (UTC-7)"
        )
        profile.save()
        user.profile = profile

    login(
        request, user,
        backend='django.contrib.auth.backends.ModelBackend'
    )

    if is_new_user:
        target_redirect = reverse_lazy('core:home')
    elif next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        target_redirect = next_url
    elif hasattr(user, 'profile') and user.profile.is_instructor:
        target_redirect = reverse_lazy('courses:instructor_studio')
    else:
        target_redirect = reverse_lazy('accounts:profile')

    if is_new_user:
        messages.success(
            request,
            f"Welcome to "
            f"{getattr(settings, 'SITE_NAME', 'Learnix')}, "
            f"{user.first_name or user.username}! Your account has been "
            f"verified and created via Google."
        )
    elif is_linked_user:
        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}! "
            f"Your Google account has been linked to your existing "
            f"Learnix account."
        )
    else:
        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}! "
            f"Signed in via Google."
        )

    return redirect(target_redirect)


class GoogleLoginView(View):
    def get(self, request, *args, **kwargs):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        client_secret = getattr(
            settings, 'GOOGLE_CLIENT_SECRET', ''
        ).strip()

        if (
            not client_id or not client_secret or
            client_id.startswith('your_')
        ):
            messages.warning(
                request,
                "Google OAuth 2.0 is not yet configured. Please set "
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your "
                ".env file."
            )
            referer = request.META.get('HTTP_REFERER')
            if referer and url_has_allowed_host_and_scheme(
                referer, allowed_hosts={request.get_host()}
            ):
                return redirect(referer)
            return redirect('accounts:login')

        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state

        if request.GET.get('next'):
            request.session['google_oauth_next'] = request.GET.get('next')
        if request.GET.get('role'):
            request.session['google_oauth_role'] = request.GET.get('role')

        redirect_uri = request.build_absolute_uri(
            reverse_lazy('accounts:google_callback')
        )
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'prompt': 'select_account',
            'access_type': 'online',
        }
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"{urlencode(params)}"
        )
        return redirect(auth_url)


class GoogleCallbackView(View):
    def get(self, request, *args, **kwargs):
        if 'error' in request.GET:
            error = request.GET.get('error')
            request.session.pop('google_oauth_state', None)
            request.session.pop('google_oauth_next', None)
            request.session.pop('google_oauth_role', None)
            if error in [
                'access_denied', 'user_cancelled', 'immediate_failed'
            ]:
                messages.info(
                    request, "Google sign-in was cancelled."
                )
            else:
                messages.error(
                    request,
                    f"Google authentication failed ({error})."
                )
            return redirect('accounts:login')

        state = request.GET.get('state')
        saved_state = request.session.pop('google_oauth_state', None)
        if not state or not saved_state or state != saved_state:
            messages.error(
                request,
                "OAuth security verification failed (state mismatch). "
                "Please try again."
            )
            return redirect('accounts:login')

        code = request.GET.get('code')
        if not code:
            messages.error(
                request,
                "Authorization code missing from Google callback."
            )
            return redirect('accounts:login')

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        client_secret = getattr(
            settings, 'GOOGLE_CLIENT_SECRET', ''
        ).strip()
        redirect_uri = request.build_absolute_uri(
            reverse_lazy('accounts:google_callback')
        )

        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }

        try:
            token_resp = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                timeout=10
            )
            if token_resp.status_code != 200:
                messages.error(
                    request,
                    "Failed to exchange authorization token with "
                    "Google servers. Please verify Google credentials."
                )
                return redirect('accounts:login')

            tokens = token_resp.json()
            access_token = tokens.get('access_token')
            if not access_token:
                messages.error(
                    request,
                    "Failed to retrieve access token from Google."
                )
                return redirect('accounts:login')

            userinfo_resp = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if userinfo_resp.status_code != 200:
                messages.error(
                    request,
                    "Failed to fetch user profile from Google account."
                )
                return redirect('accounts:login')

            userinfo = userinfo_resp.json()
        except requests.RequestException:
            messages.error(
                request,
                "Network error communicating with Google "
                "authentication servers."
            )
            return redirect('accounts:login')

        google_email = userinfo.get('email', '').strip().lower()
        if not google_email:
            messages.error(
                request,
                "Google account did not return a valid email address."
            )
            return redirect('accounts:login')

        if userinfo.get('email_verified') is False:
            messages.error(
                request,
                "Your Google email address is not verified by Google."
            )
            return redirect('accounts:login')

        given_name = userinfo.get('given_name', '')
        family_name = userinfo.get('family_name', '')
        picture = userinfo.get('picture', '')
        next_url = request.session.pop('google_oauth_next', None)
        role = request.session.pop('google_oauth_role', 'student')

        return complete_google_auth_login(
            request, google_email, given_name, family_name,
            next_url, role=role, avatar_url=picture
        )
