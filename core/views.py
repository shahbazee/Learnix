from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from courses.models import Course, CourseCategory


def health_check_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse(
            {"status": "error", "database": "unreachable"}, status=503
        )
    return JsonResponse({"status": "ok", "database": "ok"})


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
