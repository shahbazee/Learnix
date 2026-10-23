from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from accounts.adapters import AccountAdapter
from accounts.models import UserProfile

User = get_user_model()

GOOGLE_SETTINGS = {
    "google": {
        "APP": {
            "client_id": "test-client-id",
            "secret": "test-secret",
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "EMAIL_AUTHENTICATION": True,
    }
}


@override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE_SETTINGS)
class GoogleAllauthTests(TestCase):
    def test_login_page_links_to_allauth_google(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "/auth/google/login/")

    def test_signup_page_links_to_allauth_google(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertContains(response, "/auth/google/login/")

    def test_google_login_redirects_to_google(self):
        response = self.client.get(reverse("google_login"))
        self.assertEqual(response.status_code, 302)
        location = unquote(response["Location"])
        self.assertIn("accounts.google.com", location)
        self.assertIn("client_id=test-client-id", location)
        self.assertIn("/auth/google/login/callback/", location)

    def test_old_gis_callback_route_is_gone(self):
        with self.assertRaises(NoReverseMatch):
            reverse("accounts:google_complete")


class AccountAdapterRedirectTests(TestCase):
    def _redirect_for(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return AccountAdapter().get_login_redirect_url(request)

    def _make_user(self, username, role=None):
        user = User.objects.create_user(
            username=username, password="pass12345"
        )
        if role is not None:
            profile = user.profile
            profile.role = role
            profile.save(update_fields=["role"])
        return user

    def test_student_goes_to_profile(self):
        user = self._make_user("student1")
        self.assertEqual(
            self._redirect_for(user), reverse("accounts:profile")
        )

    def test_instructor_goes_to_studio(self):
        user = self._make_user("inst1", UserProfile.ROLE_INSTRUCTOR)
        self.assertEqual(
            self._redirect_for(user),
            reverse("courses:instructor_studio"),
        )

    def test_admin_goes_to_admin_dashboard(self):
        user = self._make_user("admin1", UserProfile.ROLE_ADMIN)
        self.assertEqual(
            self._redirect_for(user), reverse("core:admin_dashboard")
        )
