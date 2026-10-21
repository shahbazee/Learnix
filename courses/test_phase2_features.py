from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import (
    Course,
    CourseModule,
    Enrollment,
    Lesson,
    LessonProgress,
    Review,
)

User = get_user_model()

TEST_PASSWORD = "Str0ng!Passw0rd"


def make_user(username, email, role):
    user = User.objects.create_user(
        username=username, email=email, password=TEST_PASSWORD
    )
    profile = user.profile
    profile.role = role
    profile.save()
    return user


def make_course(instructor, title="Python Basics", slug="python-basics"):
    return Course.objects.create(
        title=title,
        slug=slug,
        instructor=instructor,
        short_description="Learn Python.",
        price=Decimal("0.00"),
        is_published=True,
    )


class CourseArchiveTests(TestCase):
    def setUp(self):
        self.instructor = make_user(
            "inst_one", "inst1@example.com", "instructor"
        )
        self.student = make_user(
            "stud_one", "stud1@example.com", "student"
        )
        self.course = make_course(self.instructor)
        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, is_active=True
        )

    def test_website_delete_archives_and_keeps_enrollment(self):
        self.client.force_login(self.instructor)
        response = self.client.post(
            reverse(
                "courses:instructor_course_delete",
                kwargs={"slug": self.course.slug},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_archived)
        self.assertFalse(self.course.is_published)
        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.is_active)
        detail = self.client.get(
            reverse(
                "courses:course_detail",
                kwargs={"slug": self.course.slug},
            )
        )
        self.assertEqual(detail.status_code, 404)

    def test_api_destroy_archives_instead_of_deleting(self):
        api = APIClient()
        api.force_authenticate(self.instructor)
        response = api.delete(
            reverse(
                "course-detail", kwargs={"slug": self.course.slug}
            )
        )
        self.assertEqual(response.status_code, 204)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_archived)


class ProgressRecalculationTests(TestCase):
    def setUp(self):
        self.instructor = make_user(
            "inst_two", "inst2@example.com", "instructor"
        )
        self.student = make_user(
            "stud_two", "stud2@example.com", "student"
        )
        self.course = make_course(
            self.instructor, "Django Course", "django-course"
        )
        self.module = CourseModule.objects.create(
            course=self.course, title="Start", order_number=1
        )
        self.lesson_one = Lesson.objects.create(
            module=self.module, title="Lesson 1", order_number=1
        )
        self.lesson_two = Lesson.objects.create(
            module=self.module, title="Lesson 2", order_number=2
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, is_active=True
        )
        LessonProgress.objects.create(
            user=self.student,
            lesson=self.lesson_one,
            is_completed=True,
        )
        self.enrollment.calculate_progress()

    def test_progress_recalculated_when_lesson_added_and_removed(self):
        self.enrollment.refresh_from_db()
        self.assertEqual(float(self.enrollment.progress_percent), 50.0)
        lesson_three = Lesson.objects.create(
            module=self.module, title="Lesson 3", order_number=3
        )
        self.enrollment.refresh_from_db()
        self.assertEqual(
            float(self.enrollment.progress_percent), 33.33
        )
        lesson_three.delete()
        self.enrollment.refresh_from_db()
        self.assertEqual(float(self.enrollment.progress_percent), 50.0)


class ReviewTests(TestCase):
    def setUp(self):
        self.instructor = make_user(
            "inst_three", "inst3@example.com", "instructor"
        )
        self.student = make_user(
            "stud_three", "stud3@example.com", "student"
        )
        self.other_student = make_user(
            "stud_four", "stud4@example.com", "student"
        )
        self.course = make_course(
            self.instructor, "Flask Course", "flask-course"
        )
        Enrollment.objects.create(
            user=self.student, course=self.course, is_active=True
        )
        Enrollment.objects.create(
            user=self.other_student, course=self.course, is_active=True
        )
        self.url = reverse(
            "courses:course_review", kwargs={"slug": self.course.slug}
        )

    def test_enrolled_student_review_updates_course_rating(self):
        self.client.force_login(self.student)
        response = self.client.post(
            self.url, {"rating": "5", "comment": "Great course!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        self.course.refresh_from_db()
        self.assertEqual(float(self.course.rating), 5.0)
        self.assertEqual(self.course.reviews_count, 1)

    def test_average_and_update_of_existing_review(self):
        self.client.force_login(self.student)
        self.client.post(self.url, {"rating": "5", "comment": ""})
        self.client.force_login(self.other_student)
        self.client.post(self.url, {"rating": "3", "comment": ""})
        self.course.refresh_from_db()
        self.assertEqual(float(self.course.rating), 4.0)
        self.assertEqual(self.course.reviews_count, 2)
        self.client.force_login(self.student)
        self.client.post(self.url, {"rating": "1", "comment": ""})
        self.course.refresh_from_db()
        self.assertEqual(float(self.course.rating), 2.0)
        self.assertEqual(self.course.reviews_count, 2)

    def test_non_enrolled_student_cannot_review(self):
        outsider = make_user(
            "stud_five", "stud5@example.com", "student"
        )
        self.client.force_login(outsider)
        self.client.post(self.url, {"rating": "5", "comment": ""})
        self.assertEqual(Review.objects.count(), 0)


class UnenrollTests(TestCase):
    def setUp(self):
        self.instructor = make_user(
            "inst_four", "inst4@example.com", "instructor"
        )
        self.student = make_user(
            "stud_six", "stud6@example.com", "student"
        )
        self.course = make_course(
            self.instructor, "SQL Course", "sql-course"
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, is_active=True
        )
        self.client.force_login(self.student)

    def test_unenroll_deactivates_and_reenroll_reactivates(self):
        response = self.client.post(
            reverse(
                "courses:unenroll", kwargs={"slug": self.course.slug}
            )
        )
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertFalse(self.enrollment.is_active)
        response = self.client.post(
            reverse(
                "courses:enroll", kwargs={"slug": self.course.slug}
            )
        )
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.is_active)
