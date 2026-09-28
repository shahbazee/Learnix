"""
Automated unit and integration test suite for Learnix Authentication Subsystem.
Validates Two-Phase OTP Verification, Rate Limiting, Brute-Force ceilings, and Session Auth.
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile, EmailOTP
from accounts.forms import StudentRegistrationForm

User = get_user_model()


class AccountsAuthenticationTestCase(TestCase):
    """
    Test suite for two-phase registration, email OTP validation, and session login.
    """

    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('accounts:signup')
        self.verify_otp_url = reverse('accounts:verify_otp')
        self.resend_otp_url = reverse('accounts:resend_otp')
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.profile_url = reverse('accounts:profile')

    def test_student_registration_form_validation(self):
        """Validates email uniqueness and password rules."""
        # Weak password (< 8 chars)
        form = StudentRegistrationForm(data={
            'first_name': 'Marcus',
            'last_name': 'Vance',
            'username': 'marcus',
            'email': 'marcus@learnix.com',
            'password': 'short',
            'confirm_password': 'short',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

        # Mismatched passwords
        form = StudentRegistrationForm(data={
            'first_name': 'Marcus',
            'last_name': 'Vance',
            'username': 'marcus',
            'email': 'marcus@learnix.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'DifferentPassword123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)

    def test_two_phase_otp_registration_lifecycle(self):
        """Full registration lifecycle: signup -> OTP email -> verify -> active login."""
        # 1. Submit signup
        payload = {
            'first_name': 'Elena',
            'last_name': 'Rostova',
            'username': 'elena_ai',
            'email': 'elena@learnix.com',
            'password': 'SuperSecurePassword2026!',
            'confirm_password': 'SuperSecurePassword2026!',
        }
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.verify_otp_url)

        # User is inactive
        user = User.objects.get(username='elena_ai')
        self.assertFalse(user.is_active)

        # Profile was auto-created via post_save signal
        self.assertTrue(hasattr(user, 'profile'))

        # OTP was generated
        otp_record = EmailOTP.objects.get(user=user, is_verified=False)
        self.assertEqual(len(otp_record.otp_code), 6)
        self.assertFalse(otp_record.is_expired)

        # 2. Verify with incorrect code
        bad_response = self.client.post(self.verify_otp_url, data={'otp_code': '000000'})
        self.assertEqual(bad_response.status_code, 200)
        otp_record.refresh_from_db()
        self.assertEqual(otp_record.attempts_count, 1)

        # 3. Verify with correct code
        good_response = self.client.post(self.verify_otp_url, data={'otp_code': otp_record.otp_code})
        self.assertEqual(good_response.status_code, 302)

        # User is now active and logged in
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        otp_record.refresh_from_db()
        self.assertTrue(otp_record.is_verified)

        # Verify access to profile
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, 'elena_ai')

    def test_otp_expiry_enforcement(self):
        """OTPs older than 10 minutes must be rejected."""
        user = User.objects.create_user(
            username='expiring_user',
            email='expiring@learnix.com',
            password='Password123!',
            is_active=False
        )
        otp_record = EmailOTP.create_for_user(user)
        # Artificially age the OTP beyond 10 minutes
        otp_record.expires_at = timezone.now() - timedelta(minutes=1)
        otp_record.save()

        # Set session
        session = self.client.session
        session['otp_user_id'] = user.id
        session.save()

        response = self.client.post(self.verify_otp_url, data={'otp_code': otp_record.otp_code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expired')
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_brute_force_otp_attempt_ceiling(self):
        """Enforces a maximum of 5 failed attempts before locking the code."""
        user = User.objects.create_user(
            username='brute_tester',
            email='brute@learnix.com',
            password='Password123!',
            is_active=False
        )
        otp_record = EmailOTP.create_for_user(user)

        session = self.client.session
        session['otp_user_id'] = user.id
        session.save()

        # Submit 5 incorrect codes
        for i in range(5):
            self.client.post(self.verify_otp_url, data={'otp_code': '999999'})

        otp_record.refresh_from_db()
        self.assertEqual(otp_record.attempts_count, 5)
        self.assertTrue(otp_record.is_locked)

        # Even with correct code, locked OTP is rejected
        locked_response = self.client.post(self.verify_otp_url, data={'otp_code': otp_record.otp_code})
        self.assertEqual(locked_response.status_code, 200)
        self.assertContains(locked_response, 'Security threshold exceeded')

    def test_credentials_login_and_logout(self):
        """Active user can log in; inactive user cannot log in before OTP verification."""
        # Inactive user attempt
        inactive_user = User.objects.create_user(
            username='inactive_student',
            email='inactive@learnix.com',
            password='ValidPassword123!',
            is_active=False
        )
        login_attempt = self.client.post(self.login_url, data={
            'username': 'inactive_student',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(login_attempt.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

        # Activate user and test login
        inactive_user.is_active = True
        inactive_user.save()

        successful_login = self.client.post(self.login_url, data={
            'username': 'inactive_student',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(successful_login.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), inactive_user.id)

        # Test logout
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)


from unittest.mock import patch, MagicMock

@override_settings(GOOGLE_CLIENT_ID='test_client_id_123.apps.googleusercontent.com', GOOGLE_CLIENT_SECRET='test_client_secret_xyz')
class NewAuthenticationFeaturesTestCase(TestCase):
    """
    Comprehensive test suite covering:
    1. Edit Profile (Standard & AJAX, email uniqueness, unauthorized access)
    2. Forgot Password (OTP request, verification, password reset, unauthorized bypass prevention)
    3. Logout (GET & POST handling, session invalidation, navbar state)
    4. Continue with Google (OAuth flow initiation, CSRF state verification, new user, existing user)
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='auth_student',
            email='student@learnix.edu',
            password='OldSecurePassword123!',
            first_name='OriginalFirst',
            last_name='OriginalLast',
            is_active=True
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.forgot_pw_url = reverse('accounts:forgot_password')
        self.verify_reset_otp_url = reverse('accounts:verify_reset_otp')
        self.reset_pw_url = reverse('accounts:reset_password')
        self.profile_url = reverse('accounts:profile')
        self.logout_url = reverse('accounts:logout')
        self.google_login_url = reverse('accounts:google_login')
        self.google_callback_url = reverse('accounts:google_callback')

    # --------------------------------------------------------------------------
    # 1. EDIT PROFILE TESTS
    # --------------------------------------------------------------------------
    def test_unauthorized_profile_access_redirects(self):
        """Unauthenticated requests to profile must redirect to login."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_update_standard_form(self):
        """Authenticated user can update profile details."""
        self.client.login(username='auth_student', password='OldSecurePassword123!')
        response = self.client.post(self.profile_url, data={
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'student_new@learnix.edu',
            'headline': 'AI Researcher & Data Engineer',
            'bio': 'Passionate about deep learning architectures.',
            'phone_number': '+1 555-0199',
            'location_timezone': 'New York, NY · UTC-5',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.last_name, 'UpdatedLast')
        self.assertEqual(self.user.email, 'student_new@learnix.edu')
        self.assertEqual(self.profile.headline, 'AI Researcher & Data Engineer')
        self.assertEqual(self.profile.bio, 'Passionate about deep learning architectures.')

    def test_profile_update_ajax(self):
        """AJAX profile submission returns JSON success response."""
        self.client.login(username='auth_student', password='OldSecurePassword123!')
        response = self.client.post(
            self.profile_url,
            data={
                'first_name': 'AjaxFirst',
                'last_name': 'AjaxLast',
                'headline': 'Full Stack Developer',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'AjaxFirst')

    def test_profile_email_duplicate_rejected(self):
        """Cannot change email to one already registered by another user."""
        User.objects.create_user(
            username='other_student',
            email='existing@learnix.edu',
            password='Password123!'
        )
        self.client.login(username='auth_student', password='OldSecurePassword123!')
        response = self.client.post(self.profile_url, data={
            'first_name': 'Auth',
            'last_name': 'Student',
            'email': 'existing@learnix.edu',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'student@learnix.edu')  # Email remained unchanged

    # --------------------------------------------------------------------------
    # 2. FORGOT PASSWORD & OTP LIFECYCLE TESTS
    # --------------------------------------------------------------------------
    def test_forgot_password_lifecycle(self):
        """Full flow: request reset -> OTP sent -> verify OTP -> update password -> login."""
        # 1. Request OTP for existing email
        req_res = self.client.post(self.forgot_pw_url, data={'email': 'student@learnix.edu'})
        self.assertEqual(req_res.status_code, 302)
        self.assertRedirects(req_res, self.verify_reset_otp_url)

        # Verify OTP record in database with purpose='password_reset'
        otp = EmailOTP.objects.filter(user=self.user, purpose='password_reset', is_verified=False).first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)

        # 2. Bad OTP code submission
        bad_verify = self.client.post(self.verify_reset_otp_url, data={'otp_code': '000000'})
        self.assertEqual(bad_verify.status_code, 200)
        self.assertContains(bad_verify, 'Incorrect verification code')

        # 3. Correct OTP code submission
        good_verify = self.client.post(self.verify_reset_otp_url, data={'otp_code': otp.otp_code})
        self.assertEqual(good_verify.status_code, 302)
        self.assertRedirects(good_verify, self.reset_pw_url)
        self.assertTrue(self.client.session.get('reset_otp_verified'))

        # 4. Set new password
        reset_res = self.client.post(self.reset_pw_url, data={
            'password': 'BrandNewPassword2026!',
            'confirm_password': 'BrandNewPassword2026!',
        })
        self.assertEqual(reset_res.status_code, 302)
        self.assertRedirects(reset_res, reverse('accounts:login'))

        # 5. Authenticate with new password
        login_res = self.client.post(reverse('accounts:login'), data={
            'username': 'auth_student',
            'password': 'BrandNewPassword2026!'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_reset_password_page_guarded_against_direct_access(self):
        """Direct access to /forgot-password/reset/ without verified OTP is blocked."""
        response = self.client.get(self.reset_pw_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.forgot_pw_url)

    # --------------------------------------------------------------------------
    # 3. LOGOUT TESTS
    # --------------------------------------------------------------------------
    def test_logout_clears_session_post_and_get(self):
        """Logout via both POST and GET ends session and redirects to home."""
        # Test POST
        self.client.login(username='auth_student', password='OldSecurePassword123!')
        self.assertIn('_auth_user_id', self.client.session)
        post_logout = self.client.post(self.logout_url)
        self.assertEqual(post_logout.status_code, 302)
        self.assertRedirects(post_logout, reverse('core:home'))
        self.assertNotIn('_auth_user_id', self.client.session)

        # Test GET
        self.client.login(username='auth_student', password='OldSecurePassword123!')
        self.assertIn('_auth_user_id', self.client.session)
        get_logout = self.client.get(self.logout_url)
        self.assertEqual(get_logout.status_code, 302)
        self.assertRedirects(get_logout, reverse('core:home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    # --------------------------------------------------------------------------
    # 4. CONTINUE WITH GOOGLE OAUTH TESTS
    # --------------------------------------------------------------------------
    def test_google_login_initiates_oauth_redirect(self):
        """Google login view generates anti-CSRF state and redirects to Google."""
        response = self.client.get(self.google_login_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('https://accounts.google.com/o/oauth2/v2/auth'))
        self.assertIn('response_type=code', response.url)
        self.assertIn('scope=openid+email+profile', response.url)
        self.assertIn('state=', response.url)
        self.assertTrue('google_oauth_state' in self.client.session)

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_google_callback_creates_and_authenticates_new_user(self, mock_post, mock_get):
        """Google OAuth callback registers a new user if one doesn't exist."""
        # Configure mocks
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'access_token': 'fake_google_access_token'}
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'id': 'google_sub_998877',
                'email': 'newgoogleuser@gmail.com',
                'given_name': 'Google',
                'family_name': 'Student',
                'picture': 'https://example.com/avatar.jpg'
            }
        )

        # Set session state
        session = self.client.session
        session['google_oauth_state'] = 'valid_secret_state'
        session.save()

        callback_url = f"{self.google_callback_url}?code=google_auth_code&state=valid_secret_state"
        response = self.client.get(callback_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

        # User was created and is authenticated
        new_user = User.objects.get(email='newgoogleuser@gmail.com')
        self.assertTrue(new_user.is_active)
        self.assertEqual(new_user.first_name, 'Google')
        self.assertEqual(new_user.last_name, 'Student')
        self.assertFalse(bool(new_user.profile.avatar))  # Profile picture remains empty/default per specs
        self.assertEqual(int(self.client.session['_auth_user_id']), new_user.id)

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_google_callback_links_and_logs_in_existing_user(self, mock_post, mock_get):
        """Google OAuth callback matches existing user by email and logs them in."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'access_token': 'fake_google_access_token'}
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'id': 'google_sub_112233',
                'email': 'student@learnix.edu',
                'given_name': 'OriginalFirst',
                'family_name': 'OriginalLast',
            }
        )

        session = self.client.session
        session['google_oauth_state'] = 'valid_state_for_existing'
        session.save()

        callback_url = f"{self.google_callback_url}?code=google_auth_code&state=valid_state_for_existing"
        response = self.client.get(callback_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.profile_url)

        # Logged in as existing user
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_google_callback_state_mismatch_prevents_csrf(self):
        """Callback with mismatched state token is rejected."""
        session = self.client.session
        session['google_oauth_state'] = 'legitimate_state'
        session.save()

        callback_url = f"{self.google_callback_url}?code=google_auth_code&state=attacker_state"
        response = self.client.get(callback_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_google_login_includes_prompt_select_account(self):
        """Google login URL contains prompt=select_account to support multi-account selection."""
        response = self.client.get(self.google_login_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('prompt=select_account', response.url)

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_google_callback_with_existing_password_user_preserves_password(self, mock_post, mock_get):
        """When an existing normal email/password user authenticates via Google, password is not overwritten."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'access_token': 'fake_google_access_token'}
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'id': 'google_sub_password_preserve',
                'email': 'student@learnix.edu',
                'given_name': 'OriginalFirst',
                'family_name': 'OriginalLast',
            }
        )

        # Set session state
        session = self.client.session
        session['google_oauth_state'] = 'valid_state_for_linking'
        session.save()

        callback_url = f"{self.google_callback_url}?code=google_auth_code&state=valid_state_for_linking"
        response = self.client.get(callback_url)
        self.assertEqual(response.status_code, 302)

        # Refresh user from DB and verify password is still valid!
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldSecurePassword123!'))
        self.assertEqual(self.user.profile.google_email, 'student@learnix.edu')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_google_callback_cancelled_redirects_and_creates_no_user(self):
        """When Google authentication is cancelled (access_denied), no account is created."""
        before_count = User.objects.count()
        session = self.client.session
        session['google_oauth_state'] = 'pending_state'
        session.save()

        callback_url = f"{self.google_callback_url}?error=access_denied&state=pending_state"
        response = self.client.get(callback_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertEqual(User.objects.count(), before_count)
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('accounts.views.requests.post')
    def test_google_callback_token_failure_redirects_and_creates_no_user(self, mock_post):
        """When token exchange with Google fails, no account is created and error is handled."""
        mock_post.return_value = MagicMock(status_code=400, json=lambda: {'error': 'invalid_grant'})
        before_count = User.objects.count()

        session = self.client.session
        session['google_oauth_state'] = 'valid_state_fail'
        session.save()

        callback_url = f"{self.google_callback_url}?code=bad_code&state=valid_state_fail"
        response = self.client.get(callback_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertEqual(User.objects.count(), before_count)
        self.assertNotIn('_auth_user_id', self.client.session)


class UnverifiedUserOTPSignupFlowTestCase(TestCase):
    """
    Test suite specifically validating unverified vs verified user signup behavior:
    1. Unverified user submitting same email resends fresh OTP and redirects to verify_otp.
    2. No 'An account with this email address already exists' error is shown for unverified emails.
    3. Verified user submitting same email shows 'An account with this email address already exists. Please sign in.'.
    4. OTP email sending failure does not leave account or session in a broken state.
    5. Inactive user login returns helpful unverified notice.
    """

    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('accounts:signup')
        self.verify_otp_url = reverse('accounts:verify_otp')
        self.login_url = reverse('accounts:login')

    def test_signup_with_unverified_existing_email_resends_otp_and_redirects(self):
        """If email belongs to an unverified user, resend OTP and redirect to verify_otp without error."""
        unverified_user = User.objects.create_user(
            username='pending_alex',
            email='alex.pending@learnix.edu',
            password='InitialPassword123!',
            is_active=False
        )
        old_otp = EmailOTP.create_for_user(unverified_user, purpose='registration')

        # Re-submit signup with same email
        payload = {
            'first_name': 'Alex',
            'last_name': 'Pending',
            'username': 'pending_alex',
            'email': 'alex.pending@learnix.edu',
            'password': 'UpdatedPassword123!',
            'confirm_password': 'UpdatedPassword123!',
        }
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.verify_otp_url)

        # Check session is set to unverified user
        self.assertEqual(self.client.session.get('otp_user_id'), unverified_user.id)

        # Verify a new OTP was issued
        new_otp = EmailOTP.objects.filter(user=unverified_user, purpose='registration', is_verified=False).first()
        self.assertIsNotNone(new_otp)
        self.assertNotEqual(old_otp.otp_code, new_otp.otp_code)

        # Verify user can complete registration with new OTP
        verify_resp = self.client.post(self.verify_otp_url, data={'otp_code': new_otp.otp_code})
        self.assertEqual(verify_resp.status_code, 302)
        unverified_user.refresh_from_db()
        self.assertTrue(unverified_user.is_active)

    def test_signup_with_unverified_existing_email_and_invalid_form_resends_otp(self):
        """Even if form fields have errors, an unverified email resends OTP and redirects to verify_otp."""
        unverified_user = User.objects.create_user(
            username='pending_jamie',
            email='jamie.pending@learnix.edu',
            password='InitialPassword123!',
            is_active=False
        )

        # Submit signup with same email but mismatched passwords
        payload = {
            'first_name': 'Jamie',
            'last_name': 'Pending',
            'username': 'pending_jamie',
            'email': 'jamie.pending@learnix.edu',
            'password': 'PasswordOne123!',
            'confirm_password': 'PasswordTwoMismatched!',
        }
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.verify_otp_url)

        # Session should be set to unverified user
        self.assertEqual(self.client.session.get('otp_user_id'), unverified_user.id)

    def test_signup_with_verified_existing_email_shows_please_sign_in_error(self):
        """If email belongs to an already active/verified user, reject with sign in notice."""
        User.objects.create_user(
            username='active_samantha',
            email='samantha.active@learnix.edu',
            password='VerifiedPassword123!',
            is_active=True
        )

        payload = {
            'first_name': 'Samantha',
            'last_name': 'Active',
            'username': 'samantha_new',
            'email': 'samantha.active@learnix.edu',
            'password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!',
        }
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email address already exists. Please sign in.")

    @patch('accounts.views.send_otp_verification_email')
    def test_signup_otp_email_failure_does_not_break_account(self, mock_send_email):
        """If SMTP delivery fails during signup, account and session are preserved so user can verify."""
        mock_send_email.return_value = False  # Simulate SMTP failure

        payload = {
            'first_name': 'SMTP',
            'last_name': 'Tester',
            'username': 'smtp_tester',
            'email': 'smtp.fail@learnix.edu',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
        }
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.verify_otp_url)

        user = User.objects.get(username='smtp_tester')
        self.assertFalse(user.is_active)
        self.assertEqual(self.client.session.get('otp_user_id'), user.id)

        # OTP was created
        otp_record = EmailOTP.objects.filter(user=user, is_verified=False).first()
        self.assertIsNotNone(otp_record)

        # User enters OTP on verify page -> successfully activates!
        verify_resp = self.client.post(self.verify_otp_url, data={'otp_code': otp_record.otp_code})
        self.assertEqual(verify_resp.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_unverified_user_login_shows_helpful_notice(self):
        """Unverified user attempting credentials login receives clear instructions to verify OTP."""
        User.objects.create_user(
            username='unverified_login_user',
            email='unverified.login@learnix.edu',
            password='ValidPassword123!',
            is_active=False
        )
        response = self.client.post(self.login_url, data={
            'username': 'unverified_login_user',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your account email has not been verified yet")



