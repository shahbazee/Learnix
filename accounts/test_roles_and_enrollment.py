"""
Automated unit and integration test suite for:
1. Student & Instructor Role System (Signup toggle, Login role matching & spoofing prevention,
   Instructor Studio access control, Course creation & strict ownership authorization).
2. Course Detail Enrollment CTA Button Logic (Free vs Paid courses, Enrolled vs Non-Enrolled states).
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from accounts.models import UserProfile, EmailOTP
from accounts.forms import StudentRegistrationForm, UserLoginForm
from courses.models import Course, CourseCategory, CourseModule, Lesson, Enrollment

User = get_user_model()


class RoleAndEnrollmentTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Category
        self.category = CourseCategory.objects.create(name="AI Systems", slug="ai-systems")

        # 1. Create Student User
        self.student_user = User.objects.create_user(
            username="student_alice",
            email="alice@learnix.edu",
            password="StrongPassword123!"
        )
        self.student_profile, _ = UserProfile.objects.get_or_create(user=self.student_user)
        self.student_profile.role = "student"
        self.student_profile.save()

        # 2. Create Instructor 1 User
        self.instructor_1 = User.objects.create_user(
            username="instructor_bob",
            email="bob@learnix.edu",
            password="StrongPassword123!"
        )
        self.instructor_1_profile, _ = UserProfile.objects.get_or_create(user=self.instructor_1)
        self.instructor_1_profile.role = "instructor"
        self.instructor_1_profile.save()

        # 3. Create Instructor 2 User
        self.instructor_2 = User.objects.create_user(
            username="instructor_carol",
            email="carol@learnix.edu",
            password="StrongPassword123!"
        )
        self.instructor_2_profile, _ = UserProfile.objects.get_or_create(user=self.instructor_2)
        self.instructor_2_profile.role = "instructor"
        self.instructor_2_profile.save()

        # 4. Create Free Course (Authored by Instructor 1)
        self.free_course = Course.objects.create(
            title="Introduction to Neural Networks",
            slug="intro-neural-networks",
            instructor=self.instructor_1,
            category=self.category,
            price=Decimal("0.00"),
            short_description="Free intro course.",
            is_published=True
        )
        mod_free = CourseModule.objects.create(course=self.free_course, title="Module 1", order_number=1)
        self.free_lesson = Lesson.objects.create(
            module=mod_free,
            title="Lesson 1: Perceptrons",
            order_number=1,
            is_preview=True
        )

        # 5. Create Paid Course (Authored by Instructor 1)
        self.paid_course = Course.objects.create(
            title="Advanced LLM Fine-Tuning",
            slug="advanced-llm-fine-tuning",
            instructor=self.instructor_1,
            category=self.category,
            price=Decimal("149.00"),
            short_description="Production LLM track.",
            is_published=True
        )
        mod_paid = CourseModule.objects.create(course=self.paid_course, title="Module 1", order_number=1)
        self.paid_lesson = Lesson.objects.create(
            module=mod_paid,
            title="Lesson 1: LoRA Architecture",
            order_number=1,
            is_preview=True
        )

        # 6. Create Course authored by Instructor 2
        self.carol_course = Course.objects.create(
            title="Distributed Systems with Raft",
            slug="distributed-systems-raft",
            instructor=self.instructor_2,
            category=self.category,
            price=Decimal("99.00"),
            short_description="Consensus algorithms.",
            is_published=True
        )

    # --------------------------------------------------------------------------
    # 1. REGISTRATION ROLE TOGGLE TESTS
    # --------------------------------------------------------------------------

    def test_signup_role_defaults_to_student(self):
        """Registering without explicit role defaults to student."""
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
        """Registering with role='instructor' stores instructor role in DB."""
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

    # --------------------------------------------------------------------------
    # 2. LOGIN ROLE MATCHING & ROLE-SPOOFING PREVENTION TESTS
    # --------------------------------------------------------------------------

    def test_student_login_with_correct_role_succeeds(self):
        """A registered student logging in with role='student' succeeds."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'student_alice',
            'password': 'StrongPassword123!',
            'role': 'student',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.student_user.id)

    def test_student_login_with_instructor_role_rejected(self):
        """A student selecting 'Instructor' role is rejected to prevent role spoofing."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'student_alice',
            'password': 'StrongPassword123!',
            'role': 'instructor',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, "This account is registered as a Student")

    def test_instructor_login_with_correct_role_succeeds(self):
        """A registered instructor logging in with role='instructor' succeeds."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'instructor_bob',
            'password': 'StrongPassword123!',
            'role': 'instructor',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.instructor_1.id)

    def test_instructor_login_with_student_role_rejected(self):
        """An instructor selecting 'Student' role is rejected to prevent role spoofing."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'instructor_bob',
            'password': 'StrongPassword123!',
            'role': 'student',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, "This account is registered as a Instructor")

    # --------------------------------------------------------------------------
    # 3. ACCESS CONTROL: STUDENT VS INSTRUCTOR PERMISSIONS
    # --------------------------------------------------------------------------

    def test_student_denied_access_to_instructor_studio(self):
        """Student cannot access /courses/instructor/studio/ and is redirected to dashboard."""
        self.client.login(username='student_alice', password='StrongPassword123!')
        response = self.client.get(reverse('courses:instructor_studio'), follow=True)
        self.assertRedirects(response, reverse('courses:dashboard'))
        self.assertContains(response, "Access restricted. You need an Instructor account")

    def test_instructor_has_access_to_instructor_studio(self):
        """Instructor has full access to /courses/instructor/studio/."""
        self.client.login(username='instructor_bob', password='StrongPassword123!')
        response = self.client.get(reverse('courses:instructor_studio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Instructor Studio")
        # Should see their own authored courses
        self.assertContains(response, self.paid_course.title)

    def test_instructor_can_create_course(self):
        """Instructor can create a new course via instructor_course_create."""
        self.client.login(username='instructor_bob', password='StrongPassword123!')
        response = self.client.post(reverse('courses:instructor_course_create'), {
            'title': 'New Scalable Microservices',
            'category': self.category.id,
            'level': 'ADVANCED',
            'price': '79.00',
            'short_description': 'Building microservices in Go.',
            'full_description': 'Comprehensive syllabus.',
            'is_published': True,
        })
        self.assertEqual(response.status_code, 302)
        created_course = Course.objects.filter(title='New Scalable Microservices').first()
        self.assertIsNotNone(created_course)
        self.assertEqual(created_course.instructor, self.instructor_1)

    def test_instructor_can_edit_own_course(self):
        """Instructor can edit their own course."""
        self.client.login(username='instructor_bob', password='StrongPassword123!')
        response = self.client.post(reverse('courses:instructor_course_edit', kwargs={'slug': self.paid_course.slug}), {
            'title': 'Advanced LLM Fine-Tuning v2',
            'category': self.category.id,
            'level': 'ADVANCED',
            'price': '199.00',
            'short_description': 'Updated description.',
            'full_description': 'Updated outline.',
            'is_published': True,
        })
        self.assertEqual(response.status_code, 302)
        self.paid_course.refresh_from_db()
        self.assertEqual(self.paid_course.title, 'Advanced LLM Fine-Tuning v2')
        self.assertEqual(self.paid_course.price, Decimal('199.00'))

    def test_instructor_cannot_edit_other_instructor_course(self):
        """Instructor Bob cannot edit Carol's course (raises 403 Forbidden)."""
        self.client.login(username='instructor_bob', password='StrongPassword123!')
        response = self.client.get(reverse('courses:instructor_course_edit', kwargs={'slug': self.carol_course.slug}))
        self.assertEqual(response.status_code, 403)

    def test_instructor_cannot_delete_other_instructor_course(self):
        """Instructor Bob cannot delete Carol's course (raises 403 Forbidden)."""
        self.client.login(username='instructor_bob', password='StrongPassword123!')
        response = self.client.post(reverse('courses:instructor_course_delete', kwargs={'slug': self.carol_course.slug}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Course.objects.filter(slug=self.carol_course.slug).exists())

    def test_student_cannot_access_course_edit(self):
        """Student cannot access course edit view."""
        self.client.login(username='student_alice', password='StrongPassword123!')
        response = self.client.get(reverse('courses:instructor_course_edit', kwargs={'slug': self.paid_course.slug}))
        self.assertEqual(response.status_code, 302)  # Redirected by InstructorRequiredMixin to dashboard

    # --------------------------------------------------------------------------
    # 4. ENROLLMENT CTA BUTTON LOGIC TESTS
    # --------------------------------------------------------------------------

    def test_cta_non_enrolled_free_course(self):
        """Non-enrolled logged-in user on a FREE course sees 'Enroll', NOT 'Buy Now' or 'View Course'."""
        self.client.login(username='student_alice', password='StrongPassword123!')
        response = self.client.get(reverse('courses:course_detail', kwargs={'slug': self.free_course.slug}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Primary CTA button: Should have "Enroll"
        self.assertIn('Enroll', content)
        # Should NOT have "Buy Now"
        self.assertNotIn('Buy Now', content)
        # Should NOT have "View Course" (or "Resume Learning")
        self.assertNotIn('View Course', content)
        self.assertNotIn('Resume Learning', content)

    def test_cta_non_enrolled_paid_course(self):
        """Non-enrolled logged-in user on a PAID course sees 'Buy Now', NOT 'Enroll' or 'View Course'."""
        self.client.login(username='student_alice', password='StrongPassword123!')
        response = self.client.get(reverse('courses:course_detail', kwargs={'slug': self.paid_course.slug}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Primary CTA button: Should have "Buy Now"
        self.assertIn('Buy Now', content)
        # Should NOT have "View Course"
        self.assertNotIn('View Course', content)
        self.assertNotIn('Resume Learning', content)

    def test_cta_enrolled_free_course(self):
        """Enrolled user on a FREE course sees 'View Course', NOT 'Enroll' or 'Buy Now'."""
        # Grant enrollment
        Enrollment.objects.create(
            user=self.student_user,
            course=self.free_course,
            is_active=True
        )
        self.client.login(username='student_alice', password='StrongPassword123!')
        response = self.client.get(reverse('courses:course_detail', kwargs={'slug': self.free_course.slug}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Primary CTA button: Should have "View Course"
        self.assertIn('View Course', content)
        # Should NOT have "Buy Now"
        self.assertNotIn('Buy Now', content)
        # Primary CTA should not have "Enroll" as an action button
        self.assertNotIn('Enroll &amp; Instant Access', content)

    def test_cta_enrolled_paid_course(self):
        """Enrolled user on a PAID course sees 'View Course', NOT 'Enroll' or 'Buy Now'."""
        # Grant enrollment (as done by Stripe webhook in DB)
        Enrollment.objects.create(
            user=self.student_user,
            course=self.paid_course,
            is_active=True
        )
        self.client.login(username='student_alice', password='StrongPassword123!')
        response = self.client.get(reverse('courses:course_detail', kwargs={'slug': self.paid_course.slug}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Primary CTA button: Should have "View Course"
        self.assertIn('View Course', content)
        # Should NOT have "Buy Now"
        self.assertNotIn('Buy Now', content)
        # Should NOT have "Enroll & Instant Access"
        self.assertNotIn('Enroll &amp; Instant Access', content)

    def test_free_course_enrollment_lifecycle(self):
        """Non-enrolled student clicks Enroll on Free course, gets enrolled in DB, and sees View Course."""
        self.client.login(username='student_alice', password='StrongPassword123!')

        # 1. Initially non-enrolled
        self.assertFalse(Enrollment.objects.filter(user=self.student_user, course=self.free_course, is_active=True).exists())

        # 2. Post to enroll endpoint
        enroll_resp = self.client.post(reverse('courses:enroll', kwargs={'slug': self.free_course.slug}), follow=True)
        self.assertEqual(enroll_resp.status_code, 200)

        # 3. Check DB has active enrollment
        self.assertTrue(Enrollment.objects.filter(user=self.student_user, course=self.free_course, is_active=True).exists())

        # 4. Now detail page shows View Course
        detail_resp = self.client.get(reverse('courses:course_detail', kwargs={'slug': self.free_course.slug}))
        self.assertContains(detail_resp, 'View Course')
        self.assertNotContains(detail_resp, 'Buy Now')
