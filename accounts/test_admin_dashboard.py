from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile

User = get_user_model()

TEST_PWD = "Learnix" + "Test" + "123!"

PATCH_TARGET = "accounts.google_auth.verify_oauth2_token"


def make_user(username, role, **kwargs):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@learnix.edu",
        password=TEST_PWD,
        **kwargs,
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.save(update_fields=["role"])
    return user


class AdminDashboardAccessTests(TestCase):
    def setUp(self):
        self.student = make_user("student_sam", "student")
        self.instructor = make_user("instructor_ivy", "instructor")
        self.admin = make_user("admin_anna", "admin")
        self.dashboard_url = reverse("core:admin_dashboard")

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_student_blocked_from_admin_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(
            response,
            reverse("courses:dashboard"),
            fetch_redirect_response=False,
        )

    def test_instructor_blocked_from_admin_dashboard(self):
        self.client.force_login(self.instructor)
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(
            response,
            reverse("courses:dashboard"),
            fetch_redirect_response=False,
        )

    def test_admin_can_open_all_admin_pages(self):
        self.client.force_login(self.admin)
        page_names = [
            "core:admin_dashboard",
            "core:admin_users",
            "core:admin_courses",
            "core:admin_payments",
        ]
        for name in page_names:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_staff_user_can_open_admin_dashboard(self):
        staff = make_user("staff_sid", "student", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_users_page_role_filter(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("core:admin_users"), {"role": "instructor"}
        )
        self.assertContains(response, "instructor_ivy")
        self.assertNotContains(response, "student_sam")


class AdminLoginRedirectTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_anna", "admin")
        self.student = make_user("student_sam", "student")
        self.login_url = reverse("accounts:login")

    def test_admin_login_redirects_to_admin_dashboard(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "admin_anna",
                "password": TEST_PWD,
                "role": "student",
            },
        )
        self.assertRedirects(
            response,
            reverse("core:admin_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertIn("_auth_user_id", self.client.session)

    def test_student_wrong_role_still_rejected(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "student_sam",
                "password": TEST_PWD,
                "role": "instructor",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class AdminCreationGuardTests(TestCase):
    def test_api_register_rejects_admin_role(self):
        api_client = APIClient()
        response = api_client.post(
            reverse("api-register"),
            {
                "username": "mallory",
                "email": "mallory@learnix.edu",
                "role": "admin",
                "password": TEST_PWD,
                "password2": TEST_PWD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="mallory").exists())

    def test_google_signup_cannot_create_admin(self):
        id_info = {
            "email": "new.user@gmail.com",
            "email_verified": True,
            "given_name": "New",
            "family_name": "User",
            "sub": "google-sub-999",
        }
        with patch(PATCH_TARGET, return_value=id_info):
            self.client.post(
                reverse("accounts:google_complete"),
                {"credential": "test-credential", "role": "admin"},
            )
        user = User.objects.get(email="new.user@gmail.com")
        self.assertEqual(user.profile.role, "student")

    def test_google_login_admin_redirected_to_admin_dashboard(self):
        admin = make_user("admin_boss", "admin")
        admin.email = "boss@gmail.com"
        admin.save(update_fields=["email"])
        id_info = {
            "email": "boss@gmail.com",
            "email_verified": True,
            "given_name": "Boss",
            "family_name": "Admin",
            "sub": "google-sub-111",
        }
        with patch(PATCH_TARGET, return_value=id_info):
            response = self.client.post(
                reverse("accounts:google_complete"),
                {"credential": "test-credential"},
            )
        self.assertRedirects(
            response,
            reverse("core:admin_dashboard"),
            fetch_redirect_response=False,
        )
