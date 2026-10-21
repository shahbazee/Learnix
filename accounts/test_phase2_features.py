from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import EmailOTP

User = get_user_model()

TEST_PASSWORD = "Str0ng!Passw0rd"
WRONG_PASSWORD = "Wr0ng!Passw0rd"


def make_user(username, email):
    return User.objects.create_user(
        username=username, email=email, password=TEST_PASSWORD
    )


class TwoFactorLoginTests(TestCase):
    def setUp(self):
        self.user = make_user("tf_student", "tf@example.com")
        profile = self.user.profile
        profile.role = "student"
        profile.two_factor_enabled = True
        profile.save()

    def login_post(self):
        return self.client.post(
            reverse("accounts:login"),
            {
                "username": "tf_student",
                "password": TEST_PASSWORD,
                "role": "student",
            },
        )

    def test_login_redirects_to_otp_challenge(self):
        response = self.login_post()
        self.assertRedirects(
            response,
            reverse("accounts:two_factor_verify"),
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(
            EmailOTP.objects.filter(
                user=self.user, purpose="two_factor"
            ).exists()
        )

    def test_correct_code_completes_login(self):
        self.login_post()
        _, code = EmailOTP.create_for_user(
            self.user, purpose="two_factor"
        )
        response = self.client.post(
            reverse("accounts:two_factor_verify"), {"otp_code": code}
        )
        self.assertRedirects(
            response,
            reverse("accounts:profile"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session.get("_auth_user_id"), str(self.user.pk)
        )

    def test_wrong_code_rejected(self):
        self.login_post()
        EmailOTP.create_for_user(self.user, purpose="two_factor")
        response = self.client.post(
            reverse("accounts:two_factor_verify"),
            {"otp_code": "000000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class LoginLockoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("lock_user", "lock@example.com")

    def test_sixth_attempt_locked_out_even_with_correct_password(self):
        url = reverse("accounts:login")
        for _ in range(5):
            self.client.post(
                url,
                {
                    "username": "lock_user",
                    "password": WRONG_PASSWORD,
                    "role": "student",
                },
            )
        response = self.client.post(
            url,
            {
                "username": "lock_user",
                "password": TEST_PASSWORD,
                "role": "student",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many failed login attempts")
        self.assertNotIn("_auth_user_id", self.client.session)


class EmailChangeTests(TestCase):
    def setUp(self):
        self.user = make_user("changer", "old@example.com")
        self.client.force_login(self.user)

    def test_request_and_verify_updates_email(self):
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "email_change_action": "request",
                "new_email": "new@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            EmailOTP.objects.filter(
                user=self.user, purpose="email_change"
            ).exists()
        )
        _, code = EmailOTP.create_for_user(
            self.user, purpose="email_change"
        )
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "email_change_action": "verify",
                "email_change_code": code,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

    def test_request_rejects_email_of_another_account(self):
        make_user("other_user", "taken@example.com")
        self.client.post(
            reverse("accounts:profile"),
            {
                "email_change_action": "request",
                "new_email": "taken@example.com",
            },
        )
        self.assertFalse(
            EmailOTP.objects.filter(
                user=self.user, purpose="email_change"
            ).exists()
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")


class ZAuthThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def test_auth_endpoints_throttled_after_limit(self):
        url = reverse("api-login")
        statuses = []
        for _ in range(21):
            response = self.api.post(
                url,
                {"username": "nobody", "password": WRONG_PASSWORD},
                format="json",
            )
            statuses.append(response.status_code)
        self.assertNotIn(429, statuses[:20])
        self.assertEqual(statuses[20], 429)
