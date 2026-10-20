from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

ID_INFO = {
    "email": "ali.raza@gmail.com",
    "email_verified": True,
    "given_name": "Ali",
    "family_name": "Raza",
    "sub": "google-sub-123",
}

PATCH_TARGET = "accounts.views.google_views.verify_oauth2_token"


class GoogleGisViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:google_complete")

    def _post(self, data=None, id_info=None, side_effect=None):
        payload = {"credential": "test-credential"}
        if data:
            payload.update(data)
        with patch(
            PATCH_TARGET, side_effect=side_effect, return_value=id_info
        ):
            return self.client.post(self.url, payload)

    def test_new_user_created_logged_in_redirected_home(self):
        response = self._post(id_info=ID_INFO)
        self.assertRedirects(
            response, reverse("core:home"), fetch_redirect_response=False
        )
        user = User.objects.get(email="ali.raza@gmail.com")
        self.assertEqual(user.username, "ali")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.google_email, "ali.raza@gmail.com")
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), user.pk
        )

    def test_existing_user_redirected_to_profile(self):
        User.objects.create_user(
            username="someone",
            email="ali.raza@gmail.com",
            password="strong-pass-123",
        )
        total_before = User.objects.count()
        response = self._post(id_info=ID_INFO)
        self.assertRedirects(
            response,
            reverse("accounts:profile"),
            fetch_redirect_response=False,
        )
        self.assertEqual(User.objects.count(), total_before)

    def test_signup_role_instructor_is_applied(self):
        response = self._post(data={"role": "instructor"}, id_info=ID_INFO)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="ali.raza@gmail.com")
        self.assertEqual(user.profile.role, "instructor")

    def test_invalid_token_redirects_to_login_without_user(self):
        response = self._post(side_effect=ValueError("bad token"))
        self.assertRedirects(
            response,
            reverse("accounts:login"),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            User.objects.filter(email="ali.raza@gmail.com").exists()
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unverified_email_redirects_to_login_without_user(self):
        info = dict(ID_INFO, email_verified=False)
        response = self._post(id_info=info)
        self.assertRedirects(
            response,
            reverse("accounts:login"),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            User.objects.filter(email="ali.raza@gmail.com").exists()
        )

    def test_logged_in_user_links_google_account(self):
        user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="strong-pass-123",
        )
        self.client.force_login(user)
        response = self._post(id_info=ID_INFO)
        self.assertRedirects(
            response,
            reverse("accounts:profile"),
            fetch_redirect_response=False,
        )
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.google_email, "ali.raza@gmail.com")
        self.assertFalse(
            User.objects.filter(email="ali.raza@gmail.com").exists()
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_logged_in_link_conflict_with_other_account(self):
        User.objects.create_user(
            username="someone",
            email="ali.raza@gmail.com",
            password="strong-pass-123",
        )
        user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="strong-pass-123",
        )
        self.client.force_login(user)
        response = self._post(id_info=ID_INFO)
        self.assertRedirects(
            response,
            reverse("accounts:profile"),
            fetch_redirect_response=False,
        )
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.google_email, "")
