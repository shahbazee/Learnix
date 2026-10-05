from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from courses.models import (
    Course,
    CourseCategory,
    CourseModule,
    Enrollment,
    Lesson,
)

User = get_user_model()


class CourseDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = CourseCategory.objects.create(
            name='AI Architecture',
            slug='ai-arch',
        )
        self.instructor = User.objects.create_user(
            username='instructor_sarah',
            email='sarah@learnix.edu',
            password='Password123!',
        )
        self.instructor_profile, _ = UserProfile.objects.get_or_create(
            user=self.instructor
        )
        self.instructor_profile.role = UserProfile.ROLE_INSTRUCTOR
        self.instructor_profile.headline = 'Senior Research Scientist'
        self.instructor_profile.save()

        self.student = User.objects.create_user(
            username='student_alex',
            email='alex@learnix.edu',
            password='Password123!',
        )
        self.paid_course = Course.objects.create(
            title='Vector Databases Masterclass',
            slug='vector-databases',
            instructor=self.instructor,
            category=self.category,
            short_description='Deep dive into vector search.',
            price=Decimal('119.00'),
            is_published=True,
        )
        self.free_course = Course.objects.create(
            title='Intro to AI Free',
            slug='intro-ai-free',
            instructor=self.instructor,
            category=self.category,
            short_description='Free foundational overview.',
            price=Decimal('0.00'),
            is_published=True,
        )
        self.mod1 = CourseModule.objects.create(
            course=self.paid_course,
            title='Foundations',
            order_number=1,
        )
        self.mod2 = CourseModule.objects.create(
            course=self.paid_course,
            title='Quantization',
            order_number=2,
        )
        self.preview_lesson = Lesson.objects.create(
            module=self.mod1,
            title='Lesson 1: Math',
            order_number=1,
            duration_seconds=600,
            is_preview=True,
        )
        self.locked_lesson = Lesson.objects.create(
            module=self.mod1,
            title='Lesson 2: Indices',
            order_number=2,
            duration_seconds=900,
            is_preview=False,
        )
        self.mod2_lesson = Lesson.objects.create(
            module=self.mod2,
            title='Lesson 3: Advanced',
            order_number=1,
            duration_seconds=1200,
            is_preview=False,
        )

    def test_paid_course_shows_buy_now_to_unenrolled_student(self):
        self.client.force_login(self.student)
        url = reverse('courses:course_detail', args=[self.paid_course.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Buy Now')
        checkout_url = reverse(
            'payments:create_checkout_session',
            args=[self.paid_course.slug]
        )
        self.assertContains(response, checkout_url)

    def test_free_course_shows_enroll_now(self):
        self.client.force_login(self.student)
        url = reverse('courses:course_detail', args=[self.free_course.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enroll Now')
        enroll_url = reverse('courses:enroll', args=[self.free_course.slug])
        self.assertContains(response, enroll_url)

    def test_enrolled_student_sees_continue_learning(self):
        Enrollment.objects.create(
            user=self.student,
            course=self.paid_course,
            is_active=True,
        )
        self.client.force_login(self.student)
        url = reverse('courses:course_detail', args=[self.paid_course.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continue Learning')

    def test_unpublished_course_not_visible_to_normal_user(self):
        self.paid_course.is_published = False
        self.paid_course.save()
        self.client.force_login(self.student)
        url = reverse('courses:course_detail', args=[self.paid_course.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_preview_lesson_available_and_non_preview_locked(self):
        preview_url = reverse(
            'courses:lesson_preview_api',
            args=[self.paid_course.slug, self.preview_lesson.id]
        )
        response_preview = self.client.get(preview_url)
        self.assertEqual(response_preview.status_code, 200)
        data = response_preview.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['lesson']['title'], 'Lesson 1: Math')

        locked_url = reverse(
            'courses:lesson_preview_api',
            args=[self.paid_course.slug, self.locked_lesson.id]
        )
        response_locked = self.client.get(locked_url)
        self.assertEqual(response_locked.status_code, 403)

    def test_curriculum_modules_and_lessons_order(self):
        url = reverse('courses:course_detail', args=[self.paid_course.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        modules = response.context['modules']
        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0].title, 'Foundations')
        self.assertEqual(modules[1].title, 'Quantization')
        lessons_m1 = list(modules[0].lessons.all())
        self.assertEqual(lessons_m1[0].title, 'Lesson 1: Math')
        self.assertEqual(lessons_m1[1].title, 'Lesson 2: Indices')
