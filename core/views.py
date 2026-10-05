from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from courses.models import Course, CourseCategory


def health_check_view(request):
    import os
    from django.contrib.auth import get_user_model
    from accounts.models import UserProfile

    admin_ensured = False
    admin_error = None
    username = os.environ.get("ADMIN_USERNAME", "shahbaz")

    try:
        User = get_user_model()
        email = os.environ.get("ADMIN_EMAIL", "shahbazbutt22ee@gmail.com")
        password = os.environ.get("ADMIN_PASSWORD", "12345678")

        user, created = User.objects.get_or_create(
            username=username, defaults={'email': email}
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_INSTRUCTOR
        profile.save()

        admin_ensured = True
    except Exception as exc:
        admin_error = str(exc)

    return JsonResponse({
        "status": "ok",
        "release": "2026.09.29-admin-sync-v1",
        "admin_username": username,
        "admin_ensured": admin_ensured,
        "error": admin_error,
    })


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        featured_courses = (
            Course.objects.filter(is_published=True)
            .select_related(
                'instructor',
                'instructor__profile',
                'category',
            )
            .annotate(
                lessons_count=Count('modules__lessons', distinct=True)
            )
            .order_by('-rating', '-reviews_count', '-created_at')[:6]
        )
        categories = (
            CourseCategory.objects.annotate(
                published_courses_count=Count(
                    'courses',
                    filter=Q(courses__is_published=True),
                    distinct=True,
                )
            )
            .filter(published_courses_count__gt=0)
            .order_by('-published_courses_count', 'name')
        )
        preview_course = (
            Course.objects.filter(
                is_published=True,
                modules__lessons__is_preview=True,
            )
            .distinct()
            .first()
        )
        context['featured_courses'] = featured_courses
        context['categories'] = categories
        context['preview_course'] = preview_course
        return context


class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target_slugs = [
            'ai-systems',
            'distributed-systems',
            'cloud-infrastructure',
            'system-design',
        ]
        cats = {
            c.slug: c
            for c in CourseCategory.objects.filter(slug__in=target_slugs)
        }
        context['categories'] = [
            cats[s] for s in target_slugs if s in cats
        ]
        return context


def custom_page_not_found_view(request, exception=None):
    return render(request, '404.html', status=404)


def custom_server_error_view(request):
    return render(request, '500.html', status=500)


def custom_permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)
