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


class RoleAndEnrollmentTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.category = CourseCategory.objects.create(
            name="AI Systems", slug="ai-systems"
        )

        self.student_user = User.objects.create_user(
            username="student_alice",
            email="alice@learnix.edu",
            password="StrongPassword123!"
        )
        self.student_profile, _ = UserProfile.objects.get_or_create(
            user=self.student_user
        )
        self.student_profile.role = "student"
        self.student_profile.save()

        self.instructor_1 = User.objects.create_user(
            username="instructor_bob",
            email="bob@learnix.edu",
            password="StrongPassword123!"
        )
        self.instructor_1_profile, _ = UserProfile.objects.get_or_create(
            user=self.instructor_1
        )
        self.instructor_1_profile.role = "instructor"
        self.instructor_1_profile.save()

        self.instructor_2 = User.objects.create_user(
            username="instructor_carol",
            email="carol@learnix.edu",
            password="StrongPassword123!"
        )
        self.instructor_2_profile, _ = UserProfile.objects.get_or_create(
            user=self.instructor_2
        )
        self.instructor_2_profile.role = "instructor"
        self.instructor_2_profile.save()

        self.free_course = Course.objects.create(
            title="Introduction to Neural Networks",
            slug="intro-neural-networks",
            instructor=self.instructor_1,
            category=self.category,
            price=Decimal("0.00"),
            short_description="Free intro course.",
            is_published=True
        )
        mod_free = CourseModule.objects.create(
            course=self.free_course, title="Module 1", order_number=1
        )
        self.free_lesson = Lesson.objects.create(
            module=mod_free,
            title="Lesson 1: Perceptrons",
            order_number=1,
            is_preview=True
        )

        self.paid_course = Course.objects.create(
            title="Advanced LLM Fine-Tuning",
            slug="advanced-llm-fine-tuning",
            instructor=self.instructor_1,
            category=self.category,
            price=Decimal("149.00"),
            short_description="Production LLM track.",
            is_published=True
        )
        mod_paid = CourseModule.objects.create(
            course=self.paid_course, title="Module 1", order_number=1
        )
        self.paid_lesson = Lesson.objects.create(
            module=mod_paid,
            title="Lesson 1: LoRA Architecture",
            order_number=1,
            is_preview=True
        )

        self.carol_course = Course.objects.create(
            title="Distributed Systems with Raft",
            slug="distributed-systems-raft",
            instructor=self.instructor_2,
            category=self.category,
            price=Decimal("99.00"),
            short_description="Consensus algorithms.",
            is_published=True
        )

    def test_signup_role_defaults_to_student(self):
        response = self.client.post(reverse('accounts:signup'), {
            'first_name': 'David',
            'last_name': 'Student',
            'username': 'david_student',
            'email': 'david@learnix.edu',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='david_student')
        self.assertEqual(new_user.profile.role, 'student')
        self.assertTrue(new_user.profile.is_student)
        self.assertFalse(new_user.profile.is_instructor)

    def test_signup_role_instructor_selection(self):
        response = self.client.post(reverse('accounts:signup'), {
            'first_name': 'Emma',
            'last_name': 'Teacher',
            'username': 'emma_instructor',
            'email': 'emma@learnix.edu',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'role': 'instructor',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='emma_instructor')
        self.assertEqual(new_user.profile.role, 'instructor')
        self.assertTrue(new_user.profile.is_instructor)
        self.assertFalse(new_user.profile.is_student)

    def test_student_login_with_correct_role_succeeds(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'student_alice',
            'password': 'StrongPassword123!',
            'role': 'student',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(
            int(self.client.session['_auth_user_id']),
            self.student_user.id
        )

    def test_student_login_with_instructor_role_rejected(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'student_alice',
            'password': 'StrongPassword123!',
            'role': 'instructor',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(
            response, "This account is registered as a Student"
        )

    def test_instructor_login_with_correct_role_succeeds(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'instructor_bob',
            'password': 'StrongPassword123!',
            'role': 'instructor',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(
            int(self.client.session['_auth_user_id']),
            self.instructor_1.id
        )

    def test_instructor_login_with_student_role_rejected(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'instructor_bob',
            'password': 'StrongPassword123!',
            'role': 'student',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(
            response, "This account is registered as a Instructor"
        )

    def test_student_denied_access_to_instructor_studio(self):
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse('courses:instructor_studio'), follow=True
        )
        self.assertRedirects(response, reverse('courses:dashboard'))
        self.assertContains(
            response, "Access restricted. You need an Instructor account"
        )

    def test_instructor_has_access_to_instructor_studio(self):
        self.client.login(
            username='instructor_bob', password='StrongPassword123!'
        )
        response = self.client.get(reverse('courses:instructor_studio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Instructor Studio")
        self.assertContains(response, self.paid_course.title)

    def test_instructor_can_create_course(self):
        self.client.login(
            username='instructor_bob', password='StrongPassword123!'
        )
        response = self.client.post(
            reverse('courses:instructor_course_create'),
            {
                'title': 'New Scalable Microservices',
                'category': self.category.id,
                'level': 'ADVANCED',
                'price': '79.00',
                'short_description': 'Building microservices in Go.',
                'full_description': 'Comprehensive syllabus.',
                'is_published': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        created_course = Course.objects.filter(
            title='New Scalable Microservices'
        ).first()
        self.assertIsNotNone(created_course)
        self.assertEqual(created_course.instructor, self.instructor_1)

    def test_instructor_can_edit_own_course(self):
        self.client.login(
            username='instructor_bob', password='StrongPassword123!'
        )
        response = self.client.post(
            reverse(
                'courses:instructor_course_edit',
                kwargs={'slug': self.paid_course.slug}
            ),
            {
                'title': 'Advanced LLM Fine-Tuning v2',
                'category': self.category.id,
                'level': 'ADVANCED',
                'price': '199.00',
                'short_description': 'Updated description.',
                'full_description': 'Updated outline.',
                'is_published': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.paid_course.refresh_from_db()
        self.assertEqual(
            self.paid_course.title, 'Advanced LLM Fine-Tuning v2'
        )
        self.assertEqual(self.paid_course.price, Decimal('199.00'))

    def test_instructor_cannot_edit_other_instructor_course(self):
        self.client.login(
            username='instructor_bob', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse(
                'courses:instructor_course_edit',
                kwargs={'slug': self.carol_course.slug}
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_instructor_cannot_delete_other_instructor_course(self):
        self.client.login(
            username='instructor_bob', password='StrongPassword123!'
        )
        response = self.client.post(
            reverse(
                'courses:instructor_course_delete',
                kwargs={'slug': self.carol_course.slug}
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Course.objects.filter(slug=self.carol_course.slug).exists()
        )

    def test_student_cannot_access_course_edit(self):
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse(
                'courses:instructor_course_edit',
                kwargs={'slug': self.paid_course.slug}
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_cta_non_enrolled_free_course(self):
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse(
                'courses:course_detail',
                kwargs={'slug': self.free_course.slug}
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Enroll', content)
        self.assertNotIn('Buy Now', content)
        self.assertNotIn('Continue Learning', content)
        self.assertNotIn('Resume Learning', content)

    def test_cta_non_enrolled_paid_course(self):
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse(
                'courses:course_detail',
                kwargs={'slug': self.paid_course.slug}
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Buy Now', content)
        self.assertNotIn('Continue Learning', content)
        self.assertNotIn('Resume Learning', content)

    def test_cta_enrolled_free_course(self):
        Enrollment.objects.create(
            user=self.student_user,
            course=self.free_course,
            is_active=True
        )
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse(
                'courses:course_detail',
                kwargs={'slug': self.free_course.slug}
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Continue Learning', content)
        self.assertNotIn('Buy Now', content)
        self.assertNotIn('Enroll &amp; Instant Access', content)

    def test_cta_enrolled_paid_course(self):
        Enrollment.objects.create(
            user=self.student_user,
            course=self.paid_course,
            is_active=True
        )
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        response = self.client.get(
            reverse(
                'courses:course_detail',
                kwargs={'slug': self.paid_course.slug}
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Continue Learning', content)
        self.assertNotIn('Buy Now', content)
        self.assertNotIn('Enroll &amp; Instant Access', content)

    def test_free_course_enrollment_lifecycle(self):
        self.client.login(
            username='student_alice', password='StrongPassword123!'
        )
        self.assertFalse(
            Enrollment.objects.filter(
                user=self.student_user,
                course=self.free_course,
                is_active=True
            ).exists()
        )
        enroll_resp = self.client.post(
            reverse(
                'courses:enroll',
                kwargs={'slug': self.free_course.slug}
            ),
            follow=True
        )
        self.assertEqual(enroll_resp.status_code, 200)
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.student_user,
                course=self.free_course,
                is_active=True
            ).exists()
        )
        detail_resp = self.client.get(
            reverse(
                'courses:course_detail',
                kwargs={'slug': self.free_course.slug}
            )
        )
        self.assertContains(detail_resp, 'Continue Learning')
        self.assertNotContains(detail_resp, 'Buy Now')
