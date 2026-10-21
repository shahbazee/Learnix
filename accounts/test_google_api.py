from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

ID_INFO = {
    "email": "ali.raza@gmail.com",
    "email_verified": True,
    "given_name": "Ali",
    "family_name": "Raza",
    "sub": "google-sub-123",
}


class GoogleLoginApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("api-google-login")

    def _post(self, id_info=None, side_effect=None):
        with patch(
            "accounts.google_auth.verify_oauth2_token",
            side_effect=side_effect,
            return_value=id_info,
        ):
            return self.client.post(
                self.url, {"id_token": "test-token"}, format="json"
            )

    def test_new_user_created_and_tokens_returned(self):
        response = self._post(id_info=ID_INFO)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(
            User.objects.filter(email="ali.raza@gmail.com").count(), 1
        )
        user = User.objects.get(email="ali.raza@gmail.com")
        self.assertEqual(user.username, "ali")
        self.assertEqual(user.email, "ali.raza@gmail.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.google_email, "ali.raza@gmail.com")

    def test_existing_user_is_reused(self):
        existing = User.objects.create_user(
            username="someone",
            email="ali.raza@gmail.com",
            password="strong-pass-123",
        )
        total_before = User.objects.count()
        response = self._post(id_info=ID_INFO)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), total_before)
        self.assertEqual(response.data["id"], existing.id)
        existing.profile.refresh_from_db()
        self.assertEqual(existing.profile.google_email, "ali.raza@gmail.com")

    def test_taken_username_gets_suffix(self):
        User.objects.create_user(
            username="ali",
            email="other@example.com",
            password="strong-pass-123",
        )
        response = self._post(id_info=ID_INFO)
        self.assertEqual(response.status_code, 200)
        new_user = User.objects.get(email="ali.raza@gmail.com")
        self.assertEqual(new_user.username, "ali_1")

    def test_invalid_token_returns_400(self):
        response = self._post(side_effect=ValueError("bad token"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            User.objects.filter(email="ali.raza@gmail.com").exists()
        )

    def test_unverified_email_returns_400(self):
        info = dict(ID_INFO, email_verified=False)
        response = self._post(id_info=info)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            User.objects.filter(email="ali.raza@gmail.com").exists()
        )
