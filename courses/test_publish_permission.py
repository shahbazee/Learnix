from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Course, CourseCategory

User = get_user_model()

TEST_PASSWORD = "PublishPass!234"


def make_user(username, email, role):
    user = User.objects.create_user(
        username=username, email=email, password=TEST_PASSWORD
    )
    profile = user.profile
    profile.role = role
    profile.save()
    return user


class PublishPermissionSetupTests(TestCase):
    def test_publish_course_permission_is_registered(self):
        permission = Permission.objects.filter(
            content_type__app_label="courses",
            content_type__model="course",
            codename="publish_course",
        )
        self.assertTrue(permission.exists())

    def test_authorized_instructors_group_has_permission(self):
        group = Group.objects.get(name="Authorized Instructors")
        codenames = set(
            group.permissions.values_list("codename", flat=True)
        )
        self.assertIn("publish_course", codenames)


class PublishGateBase(TestCase):
    def setUp(self):
        self.category = CourseCategory.objects.create(
            name="Development", slug="development"
        )
        self.instructor = make_user(
            "plain_inst", "plain@example.com", "instructor"
        )
        self.authorized = make_user(
            "auth_inst", "auth@example.com", "instructor"
        )
        group = Group.objects.get(name="Authorized Instructors")
        self.authorized.groups.add(group)
        self.form_data = {
            "title": "Gated Course",
            "category": self.category.id,
            "level": "ADVANCED",
            "price": "49.00",
            "short_description": "Short summary.",
            "full_description": "Full syllabus.",
            "is_published": True,
        }


class WebsitePublishGateTests(PublishGateBase):
    def test_create_without_permission_stays_draft(self):
        self.client.force_login(self.instructor)
        response = self.client.post(
            reverse("courses:instructor_course_create"),
            self.form_data,
        )
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(title="Gated Course")
        self.assertFalse(course.is_published)

    def test_create_with_permission_publishes(self):
        self.client.force_login(self.authorized)
        response = self.client.post(
            reverse("courses:instructor_course_create"),
            self.form_data,
        )
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(title="Gated Course")
        self.assertTrue(course.is_published)

    def test_update_without_permission_forces_draft(self):
        course = Course.objects.create(
            title="Already Live",
            slug="already-live",
            instructor=self.instructor,
            category=self.category,
            short_description="Short summary.",
            price=Decimal("10.00"),
            is_published=True,
        )
        self.client.force_login(self.instructor)
        data = dict(self.form_data)
        data["title"] = "Already Live"
        response = self.client.post(
            reverse(
                "courses:instructor_course_edit",
                kwargs={"slug": course.slug},
            ),
            data,
        )
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertFalse(course.is_published)

    def test_superuser_instructor_can_publish(self):
        admin = User.objects.create_superuser(
            username="boss",
            email="boss@example.com",
            password=TEST_PASSWORD,
        )
        profile = admin.profile
        profile.role = "instructor"
        profile.save()
        self.client.force_login(admin)
        response = self.client.post(
            reverse("courses:instructor_course_create"),
            self.form_data,
        )
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(title="Gated Course")
        self.assertTrue(course.is_published)


class ApiPublishGateTests(PublishGateBase):
    def api_payload(self):
        return {
            "title": "API Gated Course",
            "category": self.category.id,
            "short_description": "Short summary.",
            "full_description": "Full syllabus.",
            "price": "49.00",
            "level": "ADVANCED",
            "is_published": True,
        }

    def test_api_create_without_permission_stays_draft(self):
        api = APIClient()
        api.force_authenticate(self.instructor)
        response = api.post(
            reverse("course-list"),
            self.api_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        course = Course.objects.get(title="API Gated Course")
        self.assertFalse(course.is_published)

    def test_api_create_with_permission_publishes(self):
        api = APIClient()
        api.force_authenticate(self.authorized)
        response = api.post(
            reverse("course-list"),
            self.api_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        course = Course.objects.get(title="API Gated Course")
        self.assertTrue(course.is_published)
