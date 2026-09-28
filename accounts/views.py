"""
Class-Based Views for Learnix Authentication, Profile Management, and OAuth 2.0.
Implements Two-Phase OTP Verification, Password Reset, Google OAuth 2.0,
Session Management, and Real-Time Profile Synchronization.
"""

import secrets
import requests
import logging
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.core import signing
from django.views.generic import FormView, TemplateView, UpdateView, View
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import UserProfile, EmailOTP
from .forms import (
    StudentRegistrationForm,
    OTPVerificationForm,
    UserLoginForm,
    ForgotPasswordRequestForm,
    SetNewPasswordForm
)
from core.exceptions import OTPExpiredException
from core.emails import (
    send_registration_success_email,
    send_otp_verification_email,
    send_forgot_password_otp_email,
    send_password_changed_email,
)
from payments.services import send_registration_welcome_email

User = get_user_model()
logger = logging.getLogger(__name__)


def _generate_otp_token(user_id):
    """Cryptographically signs user ID to guarantee session recovery across redirects and browsers."""
    return signing.dumps(user_id, salt='learnix_otp_verify')


def _decode_otp_token(token):
    """Decodes signed user ID with 30-minute validity window."""
    return signing.loads(token, salt='learnix_otp_verify', max_age=1800)


# ==============================================================================
# 1. USER REGISTRATION (TWO-PHASE EMAIL OTP)
# ==============================================================================

class SignUpView(FormView):
    """
    Phase 1 of Registration: Validates input, creates inactive user (is_active=False),
    issues cryptographic 6-digit OTP, and triggers verification email.
    If an unverified account already exists for the email, resends a fresh OTP and
    redirects to OTP verification instead of showing an 'already exists' error.
    """
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
            active_user = User.objects.filter(email__iexact=submitted_email, is_active=True).first()
            if not active_user:
                unverified_user = User.objects.filter(email__iexact=submitted_email, is_active=False).first()
                if unverified_user:
                    form = self.get_form()
                    if form.is_valid():
                        return self.form_valid(form)
                    else:
                        # Unverified account exists; per requirements, do NOT show
                        # "already exists" error. Resend fresh OTP and take user to verification page.
                        return self._dispatch_unverified_otp_and_redirect(unverified_user)
        return super().post(request, *args, **kwargs)

    def _dispatch_unverified_otp_and_redirect(self, user):
        """
        Safely generates a fresh OTP for an unverified user, dispatches email defensively,
        and redirects to the OTP verification page without leaving account in a broken state.
        """
        otp_record = EmailOTP.create_for_user(user, purpose='registration')
        self.request.session['otp_user_id'] = user.id
        self.request.session.modified = True
        token = _generate_otp_token(user.id)

        email_sent = False
        try:
            email_sent = send_otp_verification_email(user, otp_record.otp_code)
            if email_sent:
                self.request.session['otp_last_sent'] = timezone.now().timestamp()
        except Exception as e:
            logger.error(f"Error invoking send_otp_verification_email for {user.email}: {e}")

        if email_sent:
            messages.success(
                self.request,
                f"Your account is pending verification. A fresh verification code has been dispatched to {user.email}."
            )
        else:
            messages.warning(
                self.request,
                f"Account pending verification. If you do not receive the email at {user.email} shortly, please click 'Resend Verification Code' below."
            )
        return redirect(self.success_url)

    def form_valid(self, form):
        # Determine if this is an unverified re-registration
        is_re_registration = bool(form.instance and form.instance.pk)

        with transaction.atomic():
            # Save user as inactive (pending OTP verification)
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Initialize or retrieve UserProfile with selected role
            role = form.cleaned_data.get('role', 'student')
            if role not in ['student', 'instructor']:
                role = 'student'
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save(update_fields=['role'])

            # Generate cryptographic 6-digit OTP (invalidates any pending registration OTPs)
            otp_record = EmailOTP.create_for_user(user, purpose='registration')

        # Persist session verification state
        token = _generate_otp_token(user.id)
        self.request.session['otp_user_id'] = user.id
        self.request.session['otp_token'] = token
        self.request.session.modified = True

        # Dispatch email notification defensively via centralized email service
        email_sent = False
        try:
            email_sent = send_otp_verification_email(user, otp_record.otp_code)
            if email_sent:
                self.request.session['otp_last_sent'] = timezone.now().timestamp()
        except Exception as e:
            logger.error(f"Error invoking send_otp_verification_email for {user.email}: {e}")

        if email_sent:
            if is_re_registration:
                messages.success(
                    self.request,
                    f"Your account is pending verification. A fresh verification code has been dispatched to {user.email}."
                )
            else:
                messages.success(
                    self.request,
                    f"Verification code sent to {user.email}. Enter the 6-digit code to activate your account."
                )
        else:
            messages.warning(
                self.request,
                f"Account pending verification. If you do not receive the email at {user.email} shortly, please click 'Resend Verification Code' below."
            )
        return redirect(self.success_url)


class VerifyOTPView(FormView):
    """
    Phase 2 of Registration: Validates the 6-digit cryptographic OTP against
    tamper detection, 10-minute expiry, and brute-force throttling.
    """
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
            messages.error(request, "Registration session expired. Please sign up again.")
            return redirect('accounts:signup')

        user = User.objects.filter(id=user_id).first()
        if not user:
            request.session.pop('otp_user_id', None)
            messages.error(request, "Registration session expired. Please sign up again.")
            return redirect('accounts:signup')

        if user.is_active:
            request.session.pop('otp_user_id', None)
            request.session.pop('otp_last_sent', None)
            messages.info(request, "Your account has already been verified. Please sign in.")
            return redirect('accounts:login')

        return super().dispatch(request, *args, **kwargs)

    def get_user(self):
        user_id = self.request.session.get('otp_user_id')
        token = self.request.GET.get('token') or self.request.POST.get('token')
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
        context['token'] = self.request.GET.get('token') or self.request.POST.get('token', '')
        return context

    def form_valid(self, form):
        user = self.get_user()
        submitted_code = form.cleaned_data['otp_code']

        otp_record = EmailOTP.objects.filter(user=user, purpose='registration', is_verified=False).first()

        # Validation 1: Expiry check (10-minute window)
        if not otp_record or otp_record.is_expired:
            form.add_error('otp_code', "This verification code has expired. Please request a new one.")
            return self.form_invalid(form)

        # Validation 2: Brute-force throttling ceiling (max 5 attempts)
        if otp_record.is_locked:
            form.add_error('otp_code', "Security threshold exceeded (5 failed attempts). Please request a fresh code.")
            return self.form_invalid(form)

        # Validation 3: Code mismatch
        if otp_record.otp_code != submitted_code:
            otp_record.attempts_count += 1
            otp_record.save(update_fields=['attempts_count'])
            remaining = EmailOTP.MAX_ATTEMPTS - otp_record.attempts_count
            form.add_error('otp_code', f"Incorrect verification code. {remaining} attempt(s) remaining.")
            return self.form_invalid(form)

        # Success: Verify OTP & Activate Account
        otp_record.is_verified = True
        otp_record.save(update_fields=['is_verified'])

        user.is_active = True
        user.save(update_fields=['is_active'])

        # Auto-login to active session
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Clean up session verification state
        self.request.session.pop('otp_user_id', None)
        self.request.session.pop('otp_last_sent', None)

        # Dispatch registration success notification defensively via centralized email service
        try:
            send_registration_success_email(user)
        except Exception as e:
            logger.error(f"Failed to dispatch registration success email: {e}")

        messages.success(
            self.request,
            f"Account verified! Welcome to {settings.SITE_NAME}, {user.first_name or user.username}."
        )
        return redirect(self.get_success_url())


class ResendOTPView(View):
    """
    Re-issues a fresh 6-digit cryptographic OTP to the inactive user.
    Enforces a strict 60-second cooldown rate limit.
    """
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
            messages.error(request, "Session expired. Please register again.")
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)
        if user.is_active:
            messages.info(request, "This account is already verified. Please sign in.")
            return redirect('accounts:login')

        token_str = token or _generate_otp_token(user.id)
        # Rate limiting check (60s cooldown)
        last_sent = request.session.get('otp_last_sent')
        if last_sent:
            elapsed = timezone.now().timestamp() - last_sent
            if elapsed < self.RATE_LIMIT_SECONDS:
                remaining = int(self.RATE_LIMIT_SECONDS - elapsed)
                messages.warning(request, f"Please wait {remaining} seconds before requesting a new code.")
                return redirect('accounts:verify_otp')

        # Issue new code
        otp_record = EmailOTP.create_for_user(user, purpose='registration')

        # Send fresh verification email defensively via centralized email service
        try:
            send_otp_verification_email(user, otp_record.otp_code)
            request.session['otp_last_sent'] = timezone.now().timestamp()
            messages.info(request, f"A fresh verification code has been dispatched to {user.email}.")
        except Exception as e:
            logger.error(f"Failed to resend OTP verification email to {user.email}: {e}")
            messages.warning(request, "Could not send verification email. Please check your network or try again in a moment.")

        return redirect('accounts:verify_otp')


# ==============================================================================
# 2. LOGIN & LOGOUT
# ==============================================================================

class UserLoginView(LoginView):
    """
    Standard credentials login view utilizing Django cryptographically signed session cookies.
    """
    template_name = 'accounts/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.is_instructor:
            return reverse_lazy('courses:instructor_studio')
        return reverse_lazy('accounts:profile')

    def form_valid(self, form):
        user = form.get_user()
        messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
        return super().form_valid(form)


class UserLogoutView(View):
    """
    Standard Django session logout handler.
    Invalidates user session, flushes auth cookies, displays feedback message,
    and safely redirects to the public home page.
    Supports both POST (recommended) and GET requests.
    """
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            request.session.flush()
            messages.info(request, "You have been logged out of your Learnix session.")
        return redirect('core:home')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            request.session.flush()
            messages.info(request, "You have been logged out of your Learnix session.")
        return redirect('core:home')


# ==============================================================================
# 3. FORGOT PASSWORD & PASSWORD RESET FLOW
# ==============================================================================

class ForgotPasswordView(FormView):
    """
    Step 1 of Password Reset:
    Accepts user's registered email, generates a 6-digit cryptographic OTP,
    and sends it via configured email backend.
    """
    template_name = 'accounts/forgot_password.html'
    form_class = ForgotPasswordRequestForm
    success_url = reverse_lazy('accounts:verify_reset_otp')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        # Store email in session for the verification step
        self.request.session['reset_email'] = email

        if user:
            otp_record = EmailOTP.create_for_user(user, purpose='password_reset')
            self.request.session['reset_user_id'] = user.id
            self.request.session['reset_otp_last_sent'] = timezone.now().timestamp()

            # Dispatch password reset OTP email via centralized email service
            send_forgot_password_otp_email(user, otp_record.otp_code)
        else:
            # Privacy preservation: do not disclose that account does not exist
            self.request.session.pop('reset_user_id', None)

        messages.info(
            self.request,
            "If an active account is registered with that email, a 6-digit reset code has been dispatched."
        )
        return super().form_valid(form)


class VerifyResetOTPView(FormView):
    """
    Step 2 of Password Reset:
    Validates the 6-digit OTP code against brute-force limit and 10-minute expiry.
    """
    template_name = 'accounts/verify_reset_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('accounts:reset_password')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        if not request.session.get('reset_email'):
            messages.error(request, "Password reset session expired. Please enter your email.")
            return redirect('accounts:forgot_password')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reset_email'] = self.request.session.get('reset_email', '')
        return context

    def form_valid(self, form):
        user_id = self.request.session.get('reset_user_id')
        if not user_id:
            form.add_error('otp_code', "Invalid verification session. Please request a new code.")
            return self.form_invalid(form)

        user = get_object_or_404(User, id=user_id)
        submitted_code = form.cleaned_data['otp_code']
        otp_record = EmailOTP.objects.filter(user=user, purpose='password_reset', is_verified=False).first()

        # Validation 1: Expiry
        if not otp_record or otp_record.is_expired:
            form.add_error('otp_code', "This reset code has expired. Please request a new one.")
            return self.form_invalid(form)

        # Validation 2: Throttling ceiling
        if otp_record.is_locked:
            form.add_error('otp_code', "Security threshold exceeded (5 failed attempts). Please request a fresh code.")
            return self.form_invalid(form)

        # Validation 3: Mismatch
        if otp_record.otp_code != submitted_code:
            otp_record.attempts_count += 1
            otp_record.save(update_fields=['attempts_count'])
            remaining = EmailOTP.MAX_ATTEMPTS - otp_record.attempts_count
            form.add_error('otp_code', f"Incorrect verification code. {remaining} attempt(s) remaining.")
            return self.form_invalid(form)

        # Success: Authorize password update
        otp_record.is_verified = True
        otp_record.save(update_fields=['is_verified'])
        self.request.session['reset_otp_verified'] = True

        messages.success(self.request, "Code verified! Please create your new secure password.")
        return super().form_valid(form)


class ResendResetOTPView(View):
    """
    Re-issues a 6-digit password reset OTP with a 60-second cooldown rate limit.
    """
    RATE_LIMIT_SECONDS = 60

    def post(self, request, *args, **kwargs):
        user_id = request.session.get('reset_user_id')
        if not user_id:
            messages.error(request, "Password reset session expired. Please start over.")
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)

        last_sent = request.session.get('reset_otp_last_sent')
        if last_sent:
            elapsed = timezone.now().timestamp() - last_sent
            if elapsed < self.RATE_LIMIT_SECONDS:
                remaining = int(self.RATE_LIMIT_SECONDS - elapsed)
                messages.warning(request, f"Please wait {remaining} seconds before requesting a new code.")
                return redirect('accounts:verify_reset_otp')

        otp_record = EmailOTP.create_for_user(user, purpose='password_reset')
        request.session['reset_otp_last_sent'] = timezone.now().timestamp()

        # Dispatch fresh reset OTP via centralized email service
        send_forgot_password_otp_email(user, otp_record.otp_code)

        messages.info(request, "A fresh password reset code has been sent to your email.")
        return redirect('accounts:verify_reset_otp')


class ResetPasswordView(FormView):
    """
    Step 3 of Password Reset:
    Validates new password against project rules, hashes via PBKDF2, and clears reset session.
    """
    template_name = 'accounts/reset_password.html'
    form_class = SetNewPasswordForm
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        if not request.session.get('reset_otp_verified') or not request.session.get('reset_user_id'):
            messages.error(request, "Unauthorized password reset attempt. Please verify your email first.")
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

        # Securely hash and update password using PBKDF2
        user.set_password(new_password)
        user.save()

        # Invalidate all password reset OTPs for this user
        EmailOTP.objects.filter(user=user, purpose='password_reset').delete()

        # Dispatch password changed security alert email via centralized email service
        send_password_changed_email(user)

        # Clear session
        self.request.session.pop('reset_user_id', None)
        self.request.session.pop('reset_email', None)
        self.request.session.pop('reset_otp_verified', None)
        self.request.session.pop('reset_otp_last_sent', None)

        messages.success(
            self.request,
            "Your password has been successfully updated! You can now log in with your new credentials."
        )
        return super().form_valid(form)


# ==============================================================================
# 4. EDIT PROFILE (ACCOUNT SETTINGS HUB)
# ==============================================================================

class ProfileView(LoginRequiredMixin, View):
    """
    Student profile and comprehensive Account Settings hub (Learnix Spatial Design).
    Handles public avatar uploads, personal information updates, OAuth/class
    integrations, and preference synchronization via AJAX and standard POST.
    Guarantees unauthorized users cannot modify another user's profile.
    """
    template_name = 'accounts/profile.html'

    def get_context(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        enrollments_count = (
            user.enrollments.filter(is_active=True).count()
            if hasattr(user, 'enrollments') else 0
        )
        storage_total = profile.storage_total_gb or 50.0
        storage_used = profile.storage_used_gb or 12.4
        storage_percent = min(100, int((storage_used / storage_total) * 100))

        display_first_name = user.first_name or (user.username.split('.')[0].capitalize() if '.' in user.username else user.username.capitalize())
        display_last_name = user.last_name or (user.username.split('.')[1].capitalize() if '.' in user.username else "")

        return {
            'profile': profile,
            'user': user,
            'display_first_name': display_first_name,
            'display_last_name': display_last_name,
            'enrollments_count': enrollments_count,
            'storage_percent': storage_percent,
            'storage_used': storage_used,
            'storage_total': storage_total,
            'user_id_badge': f"LRN-{user.id:04d}-PX",
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

        # 1. Update User basic model fields
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        new_email = request.POST.get('email')

        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()

        # Safe Email update validation (if submitted)
        if new_email:
            new_email = new_email.strip().lower()
            if new_email != user.email:
                if User.objects.exclude(pk=user.pk).filter(email__iexact=new_email).exists():
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': "This email address is already in use by another account."
                        })
                    messages.error(request, "This email address is already in use by another account.")
                    return redirect('accounts:profile')
                user.email = new_email

        user.save()

        # 2. Update Profile fields
        if 'headline' in request.POST:
            profile.headline = request.POST.get('headline', '').strip()
        if 'bio' in request.POST:
            profile.bio = request.POST.get('bio', '').strip()
        if 'phone_number' in request.POST:
            profile.phone_number = request.POST.get('phone_number', '').strip()
        if 'country_code' in request.POST:
            profile.country_code = request.POST.get('country_code', '+1').strip()
        if 'location_timezone' in request.POST:
            profile.location_timezone = request.POST.get('location_timezone', '').strip()
        if 'academic_suffix' in request.POST:
            profile.academic_suffix = request.POST.get('academic_suffix', '').strip()
        if 'google_email' in request.POST:
            profile.google_email = request.POST.get('google_email', '').strip()
        if 'github_username' in request.POST:
            profile.github_username = request.POST.get('github_username', '').strip()

        # Boolean directory flag
        if 'public_directory' in request.POST:
            profile.public_directory = (request.POST.get('public_directory') in ['on', 'true', 'True', True, '1'])

        # Avatar handling
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        elif request.POST.get('remove_avatar') == 'true':
            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        profile.save()

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': 'Account settings successfully synchronized.',
                'avatar_url': profile.avatar.url if profile.avatar else None,
                'user_full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            })

        messages.success(request, "Account settings successfully saved.")
        return redirect('accounts:profile')


# ==============================================================================
# 5. CONTINUE WITH GOOGLE (OAUTH 2.0 INTEGRATION)
# ==============================================================================

def complete_google_auth_login(request, google_email, given_name='', family_name='', next_url=None, role='student', avatar_url=''):
    """
    Unified Google OAuth authentication and session establishment.
    Handles:
    1. New User: creates Learnix account, marks is_active=True (email verified by Google),
       sets unusable password, configures profile with role and google_email.
    2. Existing User (Google): logs user in, ensures active.
    3. Existing User (Normal email/password): safely links Google email without overwriting
       password or creating duplicate account, marks active if previously unverified.
    """
    google_email = google_email.strip().lower()
    user = User.objects.filter(email__iexact=google_email).first()
    is_new_user = False
    is_linked_user = False

    if user:
        # Activate account if it was pending verification (Google verified identity!)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.google_email:
            profile.google_email = google_email
            is_linked_user = True
        profile.save()
        user.profile = profile
        # NOTE: We preserve user.password intact so existing email/password login continues to work!
    else:
        is_new_user = True
        base_username = (given_name.lower().replace(' ', '') if given_name else google_email.split('@')[0])
        clean_username = ''.join(c for c in base_username if c.isalnum() or c in ['_', '.'])
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
            first_name=given_name or google_email.split('@')[0].capitalize(),
            last_name=family_name or 'Learner',
            is_active=True
        )
        # Set unusable password so account uses Google OAuth (or explicit password reset)
        user.set_unusable_password()
        user.save(update_fields=['password'])

        assigned_role = role if role in ['student', 'instructor'] else 'student'
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.google_email = google_email
        profile.role = assigned_role
        profile.headline = "Masterclass Instructor" if assigned_role == 'instructor' else "Engineering Fellow"
        profile.location_timezone = "San Francisco, CA · Pacific Daylight (UTC-7)"
        profile.save()
        user.profile = profile

    # Authenticate session
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # Determine safe destination redirect URL
    if is_new_user:
        target_redirect = reverse_lazy('core:home')
    elif next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        target_redirect = next_url
    elif hasattr(user, 'profile') and user.profile.is_instructor:
        target_redirect = reverse_lazy('courses:instructor_studio')
    else:
        target_redirect = reverse_lazy('accounts:profile')

    if is_new_user:
        messages.success(
            request,
            f"Welcome to {getattr(settings, 'SITE_NAME', 'Learnix')}, {user.first_name or user.username}! Your account has been verified and created via Google."
        )
    elif is_linked_user:
        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}! Your Google account has been linked to your existing Learnix account."
        )
    else:
        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}! Signed in via Google."
        )

    return redirect(target_redirect)


class GoogleLoginView(View):
    """
    Initiates Google OAuth 2.0 Authorization Code Flow for both Login and Signup.
    Directs user straight to Google's official authorization screen with prompt=select_account
    so users can always choose their intended Google account.
    """
    def get(self, request, *args, **kwargs):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '').strip()

        # If Google OAuth credentials are not yet configured in .env
        if not client_id or not client_secret or client_id.startswith('your_'):
            messages.warning(
                request,
                "Google OAuth 2.0 is not yet configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file."
            )
            referer = request.META.get('HTTP_REFERER')
            if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
                return redirect(referer)
            return redirect('accounts:login')

        # Generate cryptographic CSRF state token
        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state

        if request.GET.get('next'):
            request.session['google_oauth_next'] = request.GET.get('next')
        if request.GET.get('role'):
            request.session['google_oauth_role'] = request.GET.get('role')

        redirect_uri = request.build_absolute_uri(reverse_lazy('accounts:google_callback'))
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'prompt': 'select_account',
            'access_type': 'online',
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return redirect(auth_url)


class GoogleCallbackView(View):
    """
    Handles Google OAuth 2.0 server callback:
    1. Validates CSRF state token
    2. Exchanges authorization code for access token via HTTPS POST
    3. Fetches verified userinfo profile from Google
    4. Finds or creates corresponding Django User (preventing duplicate accounts)
    5. Logs user in and redirects to appropriate page
    """
    def get(self, request, *args, **kwargs):
        # 1. Error check (e.g. user cancelled or denied access)
        if 'error' in request.GET:
            error = request.GET.get('error')
            request.session.pop('google_oauth_state', None)
            request.session.pop('google_oauth_next', None)
            request.session.pop('google_oauth_role', None)
            if error in ['access_denied', 'user_cancelled', 'immediate_failed']:
                messages.info(request, "Google sign-in was cancelled.")
            else:
                messages.error(request, f"Google authentication failed ({error}).")
            return redirect('accounts:login')

        # 2. State verification (Anti-CSRF)
        state = request.GET.get('state')
        saved_state = request.session.pop('google_oauth_state', None)
        if not state or not saved_state or state != saved_state:
            messages.error(request, "OAuth security verification failed (state mismatch). Please try again.")
            return redirect('accounts:login')

        # 3. Code validation
        code = request.GET.get('code')
        if not code:
            messages.error(request, "Authorization code missing from Google callback.")
            return redirect('accounts:login')

        # 4. Exchange code for access token
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '').strip()
        redirect_uri = request.build_absolute_uri(reverse_lazy('accounts:google_callback'))

        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }

        try:
            token_resp = requests.post('https://oauth2.googleapis.com/token', data=token_data, timeout=10)
            if token_resp.status_code != 200:
                messages.error(request, "Failed to exchange authorization token with Google servers. Please verify Google credentials.")
                return redirect('accounts:login')

            tokens = token_resp.json()
            access_token = tokens.get('access_token')
            if not access_token:
                messages.error(request, "Failed to retrieve access token from Google.")
                return redirect('accounts:login')

            # 5. Fetch verified user profile from Google userinfo API
            userinfo_resp = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if userinfo_resp.status_code != 200:
                messages.error(request, "Failed to fetch user profile from Google account.")
                return redirect('accounts:login')

            userinfo = userinfo_resp.json()
        except requests.RequestException:
            messages.error(request, "Network error communicating with Google authentication servers.")
            return redirect('accounts:login')

        google_email = userinfo.get('email', '').strip().lower()
        if not google_email:
            messages.error(request, "Google account did not return a valid email address.")
            return redirect('accounts:login')

        if userinfo.get('email_verified') is False:
            messages.error(request, "Your Google email address is not verified by Google.")
            return redirect('accounts:login')

        given_name = userinfo.get('given_name', '')
        family_name = userinfo.get('family_name', '')
        picture = userinfo.get('picture', '')
        next_url = request.session.pop('google_oauth_next', None)
        role = request.session.pop('google_oauth_role', 'student')

        return complete_google_auth_login(request, google_email, given_name, family_name, next_url, role=role, avatar_url=picture)

