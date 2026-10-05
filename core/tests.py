from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from courses.models import Course, CourseCategory, CourseModule, Lesson

User = get_user_model()


class HomePageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.home_url = reverse('core:home')
        self.instructor = User.objects.create_user(
            username='instructor_jane',
            email='jane@learnix.edu',
            password='Password123!',
        )
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.instructor
        )
        self.profile.role = UserProfile.ROLE_INSTRUCTOR
        self.profile.headline = 'Principal Systems Architect'
        self.profile.save()

    def create_course(self, title, slug, is_published=True, category=None):
        return Course.objects.create(
            title=title,
            slug=slug,
            instructor=self.instructor,
            category=category,
            short_description='Short description',
            price=Decimal('99.00'),
            is_published=is_published,
        )

    def test_empty_state_when_no_published_courses(self):
        self.create_course(
            title='Draft Course',
            slug='draft-course',
            is_published=False,
        )
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['featured_courses']), 0)
        self.assertContains(response, 'Courses coming soon')
        self.assertContains(response, reverse('courses:course_list'))

    def test_only_published_courses_appear(self):
        pub_course = self.create_course(
            title='Published Architecture',
            slug='pub-arch',
            is_published=True,
        )
        draft_course = self.create_course(
            title='Hidden Draft',
            slug='hidden-draft',
            is_published=False,
        )
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        featured = response.context['featured_courses']
        self.assertEqual(len(featured), 1)
        self.assertIn(pub_course, featured)
        self.assertNotIn(draft_course, featured)
        self.assertContains(response, 'Published Architecture')
        self.assertNotContains(response, 'Hidden Draft')

    def test_maximum_six_featured_courses_appear(self):
        for i in range(8):
            self.create_course(
                title=f'Course {i}',
                slug=f'course-{i}',
                is_published=True,
            )
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        featured = response.context['featured_courses']
        self.assertEqual(len(featured), 6)

    def test_category_course_counts_are_correct(self):
        cat1 = CourseCategory.objects.create(
            name='Cloud Infrastructure',
            slug='cloud-infra',
            icon='cloud',
        )
        cat2 = CourseCategory.objects.create(
            name='AI Architecture',
            slug='ai-arch',
            icon='psychology',
        )
        CourseCategory.objects.create(
            name='Unused Category',
            slug='unused',
            icon='school',
        )
        self.create_course(
            title='Cloud 1',
            slug='cloud-1',
            category=cat1,
            is_published=True,
        )
        self.create_course(
            title='Cloud 2',
            slug='cloud-2',
            category=cat1,
            is_published=True,
        )
        self.create_course(
            title='Cloud Draft',
            slug='cloud-draft',
            category=cat1,
            is_published=False,
        )
        self.create_course(
            title='AI 1',
            slug='ai-1',
            category=cat2,
            is_published=True,
        )
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        categories = list(response.context['categories'])
        self.assertEqual(len(categories), 2)
        counts = {c.slug: c.published_courses_count for c in categories}
        self.assertEqual(counts['cloud-infra'], 2)
        self.assertEqual(counts['ai-arch'], 1)
        self.assertNotIn('unused', counts)

    def test_category_ordering_and_rendering(self):
        cat1 = CourseCategory.objects.create(
            name='Cloud Infrastructure',
            slug='cloud-infrastructure',
        )
        cat2 = CourseCategory.objects.create(
            name='AI Systems',
            slug='ai-systems',
        )
        cat3 = CourseCategory.objects.create(
            name='Distributed Systems',
            slug='distributed-systems',
        )
        self.create_course(
            title='AI Course 1', slug='ai-1', category=cat2, is_published=True
        )
        self.create_course(
            title='AI Course 2', slug='ai-2', category=cat2, is_published=True
        )
        self.create_course(
            title='Cloud Course 1',
            slug='cloud-1',
            category=cat1,
            is_published=True,
        )
        self.create_course(
            title='Dist Course 1',
            slug='dist-1',
            category=cat3,
            is_published=True,
        )
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        categories = list(response.context['categories'])
        self.assertEqual(categories[0].slug, 'ai-systems')
        self.assertEqual(categories[0].published_courses_count, 2)
        content = response.content.decode('utf-8')
        self.assertIn('AI Architecture', content)
        self.assertIn('Cloud Infrastructure', content)
        self.assertIn('Distributed Systems', content)
        self.assertIn('?category=ai-systems', content)
        self.assertIn('?category=cloud-infrastructure', content)
        self.assertIn('?category=distributed-systems', content)

    def test_lessons_count_calculated_correctly(self):
        course = self.create_course(
            title='Systems Mastery',
            slug='systems-mastery',
            is_published=True,
        )
        module1 = CourseModule.objects.create(
            course=course,
            title='Module 1',
            order_number=1,
        )
        module2 = CourseModule.objects.create(
            course=course,
            title='Module 2',
            order_number=2,
        )
        Lesson.objects.create(
            module=module1,
            title='Lesson 1',
            order_number=1,
        )
        Lesson.objects.create(
            module=module1,
            title='Lesson 2',
            order_number=2,
        )
        Lesson.objects.create(
            module=module2,
            title='Lesson 3',
            order_number=1,
        )
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        featured = response.context['featured_courses']
        self.assertEqual(featured[0].lessons_count, 3)


class AboutPageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.about_url = reverse('core:about')

    def test_about_page_renders_successfully(self):
        CourseCategory.objects.get_or_create(
            slug='ai-systems', defaults={'name': 'AI Systems'}
        )
        CourseCategory.objects.get_or_create(
            slug='distributed-systems',
            defaults={'name': 'Distributed Systems'},
        )
        CourseCategory.objects.get_or_create(
            slug='cloud-infrastructure',
            defaults={'name': 'Cloud Infrastructure'},
        )
        CourseCategory.objects.get_or_create(
            slug='system-design', defaults={'name': 'System Design'}
        )
        response = self.client.get(self.about_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/about.html')
        self.assertContains(response, 'About Learnix')
        self.assertContains(response, 'Why Learnix Exists')
        self.assertContains(response, 'OUR MISSION')
        self.assertContains(response, 'What We Believe')
        self.assertContains(response, 'Clarity over hype')
        self.assertContains(
            response, 'Practical learning over memorization'
        )
        self.assertContains(response, 'Honest course information')
        self.assertContains(response, 'Learn at your own pace')
        self.assertContains(response, 'What You Can Learn')
        self.assertContains(response, 'AI Systems')
        self.assertContains(response, 'Distributed Systems')
        self.assertContains(response, 'Cloud Infrastructure')
        self.assertContains(response, 'System Design')
        self.assertContains(
            response, 'Start Learning Modern Engineering'
        )
        self.assertContains(response, 'Explore Courses')
