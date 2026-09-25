"""
Automated unit and integration test suite for Learnix Course Management.
Validates Course models, custom template tags/filters, catalog filtering, search, and decorators.
"""

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from decimal import Decimal

from courses.models import CourseCategory, Course, CourseModule, Lesson, Enrollment, LessonProgress, Certificate
from payments.models import PaymentTransaction, Invoice
from courses.templatetags.course_extras import format_duration, calculate_progress_badge
from courses.decorators import enrolled_required

User = get_user_model()


class CourseManagementTestCase(TestCase):
    """
    Test suite for courses models, catalog search/filter, and access control.
    """

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Instructor
        self.instructor = User.objects.create_user(
            username='instructor_marcus',
            email='marcus@learnix.com',
            password='Password123!'
        )

        # Categories
        self.cat_python = CourseCategory.objects.create(
            name='Python & Django',
            slug='python-django',
            icon='terminal'
        )
        self.cat_dist = CourseCategory.objects.create(
            name='Distributed Systems',
            slug='distributed-systems',
            icon='lan'
        )

        # Course 1: Paid Intermediate
        self.course_django = Course.objects.create(
            title='Full-Stack Django 5 & Multi-Agent AI',
            category=self.cat_python,
            instructor=self.instructor,
            level='INTERMEDIATE',
            price=Decimal('89.00'),
            short_description='Autonomous agent workflows and websockets.',
            is_published=True,
            rating=Decimal('4.98'),
            reviews_count=100
        )

        # Module and Lessons for Course 1
        self.mod1 = CourseModule.objects.create(
            course=self.course_django,
            title='Foundations of Asynchronous Django',
            order_number=1
        )
        self.les1 = Lesson.objects.create(
            module=self.mod1,
            title='Architecture Overview',
            duration_seconds=860,
            order_number=1,
            is_preview=True
        )
        self.les2 = Lesson.objects.create(
            module=self.mod1,
            title='WebSockets Setup',
            duration_seconds=1335,
            order_number=2,
            is_preview=False
        )

        # Course 2: Advanced Free Course
        self.course_rust = Course.objects.create(
            title='Distributed Systems in Rust & Go',
            category=self.cat_dist,
            instructor=self.instructor,
            level='ADVANCED',
            price=Decimal('0.00'),
            short_description='Raft consensus and sharding.',
            is_published=True,
            rating=Decimal('4.94'),
            reviews_count=50
        )

        # Course 3: Draft (Unpublished)
        self.course_draft = Course.objects.create(
            title='Unpublished Quantum Course',
            category=self.cat_python,
            instructor=self.instructor,
            level='ADVANCED',
            price=Decimal('150.00'),
            short_description='Draft quantum course.',
            is_published=False
        )

    def test_course_model_properties_and_slug(self):
        """Validates auto-slugify, lesson counts, is_free, and duration display."""
        self.assertEqual(self.course_django.slug, 'full-stack-django-5-multi-agent-ai')
        self.assertEqual(self.course_django.total_lessons_count, 2)
        self.assertFalse(self.course_django.is_free)
        self.assertTrue(self.course_rust.is_free)
        self.assertEqual(self.les1.formatted_duration, '14:20')
        # Thumbnail fallback when thumbnail_url is empty
        self.assertEqual(self.course_django.get_thumbnail_url, f"/static/images/courses/{self.course_django.slug}.svg")
        # Thumbnail returns explicit URL when set
        self.course_django.thumbnail_url = 'https://example.com/test.png'
        self.assertEqual(self.course_django.get_thumbnail_url, 'https://example.com/test.png')

    def test_template_tags_and_filters(self):
        """Validates format_duration and calculate_progress_badge filters (SRS Section 11.2)."""
        self.assertEqual(format_duration(860), '14m')
        self.assertEqual(format_duration(3665), '1h 1m')
        self.assertEqual(format_duration(0), '0m')

        badge_zero = calculate_progress_badge(0, 10)
        self.assertIn('0% Done', badge_zero)

        badge_half = calculate_progress_badge(5, 10)
        self.assertIn('50% Done', badge_half)

        badge_full = calculate_progress_badge(10, 10)
        self.assertIn('100% Done', badge_full)

    def test_course_catalog_view_and_publishing_filter(self):
        """Catalog should display published courses and omit drafts."""
        url = reverse('courses:course_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full-Stack Django 5 &amp; Multi-Agent AI')
        self.assertContains(response, 'Distributed Systems in Rust &amp; Go')
        self.assertNotContains(response, 'Unpublished Quantum Course')

    def test_catalog_category_filtering(self):
        """Filtering by category returns only courses in that domain."""
        url = f"{reverse('courses:course_list')}?category=python-django"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full-Stack Django 5')
        self.assertNotContains(response, 'Distributed Systems in Rust &amp; Go')

    def test_catalog_difficulty_filtering(self):
        """Filtering by level returns only courses matching the difficulty."""
        url = f"{reverse('courses:course_list')}?level=ADVANCED"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Distributed Systems in Rust &amp; Go')
        self.assertNotContains(response, 'Full-Stack Django 5')

    def test_catalog_search_filtering(self):
        """Search query filters across title, description, and instructor."""
        url = f"{reverse('courses:course_list')}?q=Raft"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Distributed Systems in Rust &amp; Go')
        self.assertNotContains(response, 'Full-Stack Django 5')

    def test_enrolled_required_decorator(self):
        """Enforces access control: unauthenticated -> login; unenrolled -> blocked; staff -> allowed."""
        @enrolled_required
        def dummy_classroom_view(request, slug):
            return HttpResponse("Access Granted to Classroom")

        # 1. Anonymous visitor
        req_anon = self.factory.get(f'/courses/{self.course_django.slug}/learn/1/')
        req_anon.user = AnonymousUser()
        res_anon = dummy_classroom_view(req_anon, slug=self.course_django.slug)
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn('/accounts/login/', res_anon.url)

        # 2. Staff member bypass
        staff_user = User.objects.create_user(
            username='admin_staff',
            password='Password123!',
            is_staff=True
        )
        req_staff = self.factory.get(f'/courses/{self.course_django.slug}/learn/1/')
        req_staff.user = staff_user
        res_staff = dummy_classroom_view(req_staff, slug=self.course_django.slug)
        self.assertEqual(res_staff.status_code, 200)
        self.assertEqual(res_staff.content.decode(), "Access Granted to Classroom")

        # 3. Unenrolled authenticated student
        student_user = User.objects.create_user(
            username='unenrolled_student',
            password='Password123!'
        )
        req_student = self.factory.get(f'/courses/{self.course_django.slug}/learn/1/')
        req_student.user = student_user
        res_student = dummy_classroom_view(req_student, slug=self.course_django.slug)
        self.assertEqual(res_student.status_code, 302)
        self.assertEqual(res_student.url, f"/courses/{self.course_django.slug}/")

    def test_course_detail_view_success_and_context(self):
        """CourseDetailView should render syllabus, instructor card, and preview indicators."""
        url = reverse('courses:course_detail', kwargs={'slug': self.course_django.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full-Stack Django 5 &amp; Multi-Agent AI')
        self.assertContains(response, 'Foundations of Asynchronous Django')
        self.assertContains(response, 'Architecture Overview')
        self.assertContains(response, 'Stream Free')
        self.assertContains(response, 'Enrolled Only')
        self.assertContains(response, 'Interactive Sandbox Included')

        # Context assertions
        self.assertEqual(response.context['first_preview_lesson'], self.les1)
        self.assertEqual(response.context['total_preview_count'], 1)
        self.assertEqual(response.context['total_lessons_count'], 2)
        self.assertEqual(response.context['seats_remaining'], 14)

    def test_course_detail_view_draft_permissions(self):
        """Unpublished draft courses should return 404 to anonymous users, but 200 to staff."""
        url = reverse('courses:course_detail', kwargs={'slug': self.course_draft.slug})
        
        # 1. Anonymous visitor
        res_anon = self.client.get(url)
        self.assertEqual(res_anon.status_code, 404)

        # 2. Staff user
        staff_user = User.objects.create_user(
            username='staff_auditor',
            password='Password123!',
            is_staff=True
        )
        self.client.force_login(staff_user)
        res_staff = self.client.get(url)
        self.assertEqual(res_staff.status_code, 200)
        self.assertContains(res_staff, 'Unpublished Quantum Course')

    def test_course_search_api(self):
        """Search API returns structured JSON for the ⌘K quick-search modal."""
        # Query matching 'Django'
        url = f"{reverse('courses:search_api')}?q=Django"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'Full-Stack Django 5 & Multi-Agent AI')
        self.assertEqual(data['results'][0]['slug'], 'full-stack-django-5-multi-agent-ai')

        # Short query (<2 chars) returns empty list
        url_short = f"{reverse('courses:search_api')}?q=a"
        res_short = self.client.get(url_short)
        self.assertEqual(res_short.status_code, 200)
        self.assertEqual(res_short.json()['results'], [])

    def test_lesson_preview_api_allowed_and_forbidden(self):
        """Free preview lessons can be streamed by guests; locked lessons require enrollment."""
        # 1. Previewable lesson (les1: is_preview=True)
        url_preview = reverse('courses:lesson_preview_api', kwargs={
            'slug': self.course_django.slug,
            'lesson_id': self.les1.id
        })
        res_preview = self.client.get(url_preview)
        self.assertEqual(res_preview.status_code, 200)
        data = res_preview.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['lesson']['title'], 'Architecture Overview')
        self.assertEqual(data['lesson']['duration'], '14:20')

        # 2. Locked lesson (les2: is_preview=False) by anonymous guest
        url_locked = reverse('courses:lesson_preview_api', kwargs={
            'slug': self.course_django.slug,
            'lesson_id': self.les2.id
        })
        res_locked = self.client.get(url_locked)
        self.assertEqual(res_locked.status_code, 403)
        data_locked = res_locked.json()
        self.assertFalse(data_locked['success'])

        # 3. Locked lesson by instructor
        self.client.force_login(self.instructor)
        res_instructor = self.client.get(url_locked)
        self.assertEqual(res_instructor.status_code, 200)
        self.assertTrue(res_instructor.json()['success'])

    def test_additional_course_extras_filters(self):
        """Tests two_digits, preview_count, and original_price filters."""
        from courses.templatetags.course_extras import two_digits, preview_count, original_price

        self.assertEqual(two_digits(1), '01')
        self.assertEqual(two_digits(12), '12')
        self.assertEqual(preview_count(self.mod1), 1)
        self.assertEqual(original_price(89.00), '$178')
        self.assertEqual(original_price(0.00), '$199')

    def test_enrollment_model_creation_and_progress_calculation(self):
        """Validates Enrollment creation, uniqueness, and automated progress percentage calculation."""
        student = User.objects.create_user(
            username='test_student_1',
            email='student1@example.com',
            password='Password123!'
        )

        enrollment = Enrollment.objects.create(
            user=student,
            course=self.course_django,
            is_active=True
        )
        self.assertEqual(enrollment.progress_percent, Decimal('0.00'))
        self.assertEqual(enrollment.completed_lessons_count, 0)
        self.assertEqual(enrollment.total_lessons_count, 2)
        self.assertFalse(enrollment.is_completed)

        # Mark first lesson completed
        LessonProgress.objects.create(
            user=student,
            lesson=self.les1,
            is_completed=True
        )
        pct = enrollment.calculate_progress()
        self.assertEqual(pct, 50.00)
        self.assertEqual(enrollment.progress_percent, Decimal('50.00'))
        self.assertEqual(enrollment.completed_lessons_count, 1)

        # Mark second lesson completed -> 100%
        LessonProgress.objects.create(
            user=student,
            lesson=self.les2,
            is_completed=True
        )
        pct2 = enrollment.calculate_progress()
        self.assertEqual(pct2, 100.00)
        self.assertTrue(enrollment.is_completed)

    def test_student_dashboard_view_login_required(self):
        """Dashboard requires authentication; anonymous guests are redirected to login."""
        url = reverse('courses:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_student_dashboard_view_authenticated(self):
        """Authenticated student accesses dashboard with telemetry, study velocity, and metrics."""
        student = User.objects.create_user(
            username='sarah_test',
            first_name='Sarah',
            email='sarah_test@learnix.edu',
            password='Password123!'
        )
        Enrollment.objects.create(
            user=student,
            course=self.course_django,
            is_active=True,
            progress_percent=Decimal('50.00')
        )
        self.client.force_login(student)
        url = reverse('courses:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'Sarah')
        self.assertContains(response, 'Weekly Study Velocity')
        self.assertContains(response, 'Full-Stack Django 5')
        self.assertContains(response, 'Telemetry Metrics')
        self.assertContains(response, 'Spatial Workspace // Tier 1')
        # Strict branding enforcement
        self.assertNotContains(response, 'EduFlow')

    def test_enroll_course_view(self):
        """Logged-in student can enroll in a course, creating enrollment and billing records."""
        student = User.objects.create_user(
            username='enroll_student',
            email='enroll@example.com',
            password='Password123!'
        )
        self.client.force_login(student)

        url = reverse('courses:enroll', kwargs={'slug': self.course_django.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('courses:dashboard'))

        # Check database records
        self.assertTrue(Enrollment.objects.filter(user=student, course=self.course_django, is_active=True).exists())
        self.assertTrue(PaymentTransaction.objects.filter(user=student, course=self.course_django, status='COMPLETED').exists())

    def test_lesson_view_access_control(self):
        """Lesson player requires enrollment; unenrolled users are redirected."""
        student = User.objects.create_user(
            username='unenrolled_student',
            email='unenrolled@example.com',
            password='Password123!'
        )
        self.client.force_login(student)

        url = reverse('courses:lesson_view', kwargs={
            'slug': self.course_django.slug,
            'lesson_id': self.les1.id
        })
        # Unenrolled student redirected to course_detail
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('courses:course_detail', kwargs={'slug': self.course_django.slug}), res.url)

        # Enroll student
        Enrollment.objects.create(user=student, course=self.course_django, is_active=True)
        res_enrolled = self.client.get(url)
        self.assertEqual(res_enrolled.status_code, 200)
        self.assertContains(res_enrolled, 'Architecture Overview')
        self.assertContains(res_enrolled, 'Curriculum Progress')

    def test_mark_complete_ajax_api(self):
        """Enrolled student can toggle lesson completion via AJAX POST."""
        student = User.objects.create_user(
            username='complete_tester',
            email='complete@example.com',
            password='Password123!'
        )
        Enrollment.objects.create(user=student, course=self.course_django, is_active=True)
        self.client.force_login(student)

        url = reverse('courses:mark_complete', kwargs={'lesson_id': self.les1.id})
        res = self.client.post(url, {'is_completed': 'true'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_completed'])
        self.assertEqual(data['completed_count'], 1)
        self.assertEqual(data['total_count'], 2)
        self.assertEqual(data['progress_percent'], 50.0)

        # Check DB
        prog = LessonProgress.objects.get(user=student, lesson=self.les1)
        self.assertTrue(prog.is_completed)

    def test_certificate_issuance_at_100_percent_progress(self):
        """Verifies automatic Certificate issuance upon achieving 100% course progress."""
        student = User.objects.create_user(
            username='graduating_student',
            email='graduate@learnix.com',
            password='Password123!'
        )
        enrollment = Enrollment.objects.create(user=student, course=self.course_django, is_active=True)

        # Complete both lessons
        LessonProgress.objects.create(user=student, lesson=self.les1, is_completed=True)
        LessonProgress.objects.create(user=student, lesson=self.les2, is_completed=True)

        progress = enrollment.calculate_progress()
        self.assertEqual(progress, 100.0)
        self.assertTrue(enrollment.is_completed)

        # Check Certificate was issued
        cert = Certificate.objects.filter(enrollment=enrollment).first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.user, student)
        self.assertEqual(cert.course, self.course_django)
        self.assertTrue(cert.certificate_id.startswith('LRN-'))
        self.assertTrue(cert.verification_hash.startswith('0x'))

    def test_certificate_public_verification_view(self):
        """Public verification portal is accessible by unauthenticated recruiters."""
        student = User.objects.create_user(
            username='certified_engineer',
            email='certified@learnix.com',
            password='Password123!'
        )
        enrollment = Enrollment.objects.create(user=student, course=self.course_django, is_active=True, progress_percent=Decimal('100.0'))
        cert = Certificate.issue_for_enrollment(enrollment)

        # Unauthenticated client accesses verification portal
        self.client.logout()
        url = reverse('courses:certificate_detail', kwargs={'certificate_id': cert.certificate_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, cert.certificate_id)
        self.assertContains(res, 'Full-Stack Django 5')
        self.assertContains(res, 'VERIFIED LEDGER')
        self.assertContains(res, 'SHA-256')

    def test_download_certificate_pdf_view(self):
        """Streams landscape certificate PDF with correct Content-Type."""
        student = User.objects.create_user(
            username='pdf_receiver',
            email='pdf@learnix.com',
            password='Password123!'
        )
        enrollment = Enrollment.objects.create(user=student, course=self.course_django, is_active=True, progress_percent=Decimal('100.0'))
        cert = Certificate.issue_for_enrollment(enrollment)

        url = reverse('courses:download_certificate_pdf', kwargs={'certificate_id': cert.certificate_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn(f'Learnix_Certificate_{cert.certificate_id}.pdf', res['Content-Disposition'])
        self.assertTrue(res.content.startswith(b'%PDF'))

    def test_instructor_studio_view_requires_login(self):
        """Anonymous users must be redirected to login from instructor studio."""
        self.client.logout()
        url = reverse('courses:instructor_studio')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res.url)

    def test_instructor_studio_view_authenticated(self):
        """Logged-in instructors can view real-time studio telemetry and roster."""
        self.client.force_login(self.instructor)
        url = reverse('courses:instructor_studio')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Instructor Studio')
        self.assertContains(res, 'INSTRUCTOR CONTROL PLANE')
        self.assertContains(res, 'Total Gross Revenue')
        self.assertContains(res, 'Active Students')
        self.assertContains(res, 'Full-Stack Django 5')

    def test_export_financials_csv(self):
        """Instructors can export financials as a downloadable CSV."""
        self.client.force_login(self.instructor)
        url = reverse('courses:export_financials_csv')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn('Learnix_Financials_Ledger.csv', res['Content-Disposition'])
        self.assertIn(b'Order Reference', res.content)


