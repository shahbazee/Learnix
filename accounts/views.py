"""
Class-Based Views for Learnix Authentication, Profile Management, and OAuth 2.0.
Implements Two-Phase OTP Verification, Password Reset, Google OAuth 2.0,
Session Management, and Real-Time Profile Synchronization.
"""

import secrets
import requests
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, UpdateView, View
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse

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


# ==============================================================================
# 1. USER REGISTRATION (TWO-PHASE EMAIL OTP)
# ==============================================================================

class SignUpView(FormView):
    """
    Phase 1 of Registration: Validates input, creates inactive user (is_active=False),
    issues cryptographic 6-digit OTP, and triggers verification email.
    """
    template_name = 'accounts/signup.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('accounts:verify_otp')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Create inactive user
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

        # Generate cryptographic 6-digit OTP
        otp_record = EmailOTP.create_for_user(user, purpose='registration')

        # Persist session verification state
        self.request.session['otp_user_id'] = user.id
        self.request.session['otp_last_sent'] = timezone.now().timestamp()

        # Dispatch email notification via centralized email service
        send_otp_verification_email(user, otp_record.otp_code)

        messages.success(
            self.request,
            f"Verification code sent to {user.email}. Enter the 6-digit code to activate your account."
        )
        return super().form_valid(form)


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
        if not request.session.get('otp_user_id'):
            messages.error(request, "Registration session expired. Please sign up again.")
            return redirect('accounts:signup')
        return super().dispatch(request, *args, **kwargs)

    def get_user(self):
        user_id = self.request.session.get('otp_user_id')
        return get_object_or_404(User, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user()
        context['pending_user'] = user
        context['pending_email'] = user.email if user else ""
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

        # Dispatch registration success notification via centralized email service
        send_registration_success_email(user)

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
        if not user_id:
            messages.error(request, "Session expired. Please register again.")
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)

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
        request.session['otp_last_sent'] = timezone.now().timestamp()

        # Send fresh verification email via centralized email service
        send_otp_verification_email(user, otp_record.otp_code)

        messages.info(request, "A fresh verification code has been dispatched to your email.")
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
            messages.info(request, "You have been logged out of your Learnix session.")
        return redirect('core:home')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
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

class GoogleLoginView(View):
    """
    Initiates Google OAuth 2.0 Authorization Code Flow for both Login and Signup.
    Secured with state token against CSRF attacks.
    """
    def get(self, request, *args, **kwargs):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        if not client_id or client_id.startswith('your_'):
            messages.warning(
                request,
                "Google OAuth 2.0 is not yet configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file."
            )
            return redirect('accounts:login')

        # Generate cryptographic CSRF state token
        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state
        if request.GET.get('next'):
            request.session['google_oauth_next'] = request.GET.get('next')

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
    3. Fetches userinfo profile from Google
    4. Finds or creates corresponding Django User (preventing duplicate accounts)
    5. Logs user in and redirects to appropriate page
    """
    def get(self, request, *args, **kwargs):
        # 1. Error check
        if 'error' in request.GET:
            error = request.GET.get('error')
            messages.info(request, f"Google sign-in was cancelled ({error}).")
            return redirect('accounts:login')

        # 2. State verification (Anti-CSRF)
        state = request.GET.get('state')
        saved_state = request.session.pop('google_oauth_state', None)
        if not state or state != saved_state:
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

            # 5. Fetch user profile from Google userinfo API
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

        given_name = userinfo.get('given_name', '')
        family_name = userinfo.get('family_name', '')

        # 6. Find or create Django User
        user = User.objects.filter(email__iexact=google_email).first()
        is_new_user = False

        if user:
            # Existing user: Activate if not active
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])

            profile, _ = UserProfile.objects.get_or_create(user=user)
            if not profile.google_email:
                profile.google_email = google_email
                profile.save(update_fields=['google_email'])
        else:
            # New user: Create unique username
            is_new_user = True
            base_username = google_email.split('@')[0]
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
                first_name=given_name,
                last_name=family_name,
                is_active=True
            )
            user.set_unusable_password()
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.google_email = google_email
            profile.headline = "Engineering Fellow"
            profile.location_timezone = "San Francisco, CA · Pacific Daylight (UTC-7)"
            profile.save()

        # 7. Authenticate session
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        next_url = request.session.pop('google_oauth_next', None) or reverse_lazy('accounts:profile')

        if is_new_user:
            messages.success(
                request,
                f"Welcome to {settings.SITE_NAME}, {user.first_name or user.username}! Your account has been created via Google."
            )
        else:
            messages.success(
                request,
                f"Welcome back, {user.first_name or user.username}! Signed in via Google."
            )

        return redirect(next_url)
