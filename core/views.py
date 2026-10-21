from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import ListView, TemplateView

from accounts.models import UserProfile
from courses.mixins import AdminRequiredMixin
from courses.models import Course, CourseCategory, Enrollment
from payments.models import PaymentTransaction

User = get_user_model()


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
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        featured_courses = (
            Course.objects.filter(is_published=True, is_archived=False)
            .select_related(
                "instructor",
                "instructor__profile",
                "category",
            )
            .annotate(lessons_count=Count("modules__lessons", distinct=True))
            .order_by("-rating", "-reviews_count", "-created_at")[:6]
        )
        categories = (
            CourseCategory.objects.annotate(
                published_courses_count=Count(
                    "courses",
                    filter=Q(courses__is_published=True),
                    distinct=True,
                )
            )
            .filter(published_courses_count__gt=0)
            .order_by("-published_courses_count", "name")
        )
        preview_course = (
            Course.objects.filter(
                is_published=True,
                is_archived=False,
                modules__lessons__is_preview=True,
            )
            .distinct()
            .first()
        )
        context["featured_courses"] = featured_courses
        context["categories"] = categories
        context["preview_course"] = preview_course
        return context


class AboutView(TemplateView):
    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target_slugs = [
            "ai-systems",
            "distributed-systems",
            "cloud-infrastructure",
            "system-design",
        ]
        cats = {
            c.slug: c
            for c in CourseCategory.objects.filter(slug__in=target_slugs)
        }
        context["categories"] = [cats[s] for s in target_slugs if s in cats]
        return context


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = "core/admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        revenue = PaymentTransaction.objects.filter(
            status="COMPLETED"
        ).aggregate(total=Sum("amount"))["total"]
        context["stats"] = {
            "total_users": User.objects.count(),
            "students": UserProfile.objects.filter(
                role=UserProfile.ROLE_STUDENT
            ).count(),
            "instructors": UserProfile.objects.filter(
                role=UserProfile.ROLE_INSTRUCTOR
            ).count(),
            "admins": UserProfile.objects.filter(
                role=UserProfile.ROLE_ADMIN
            ).count(),
            "total_courses": Course.objects.count(),
            "published_courses": Course.objects.filter(
                is_published=True
            ).count(),
            "total_enrollments": Enrollment.objects.count(),
            "total_revenue": revenue or 0,
        }
        context["recent_users"] = User.objects.select_related(
            "profile"
        ).order_by("-date_joined")[:5]
        context["recent_payments"] = (
            PaymentTransaction.objects.select_related("user", "course")
            .order_by("-created_at")[:5]
        )
        return context


class AdminUserListView(AdminRequiredMixin, ListView):
    template_name = "core/admin_users.html"
    context_object_name = "platform_users"

    def get_queryset(self):
        queryset = User.objects.select_related("profile").order_by(
            "-date_joined"
        )
        role = self.request.GET.get("role")
        valid_roles = [
            UserProfile.ROLE_STUDENT,
            UserProfile.ROLE_INSTRUCTOR,
            UserProfile.ROLE_ADMIN,
        ]
        if role in valid_roles:
            queryset = queryset.filter(profile__role=role)
        return queryset


class AdminCourseListView(AdminRequiredMixin, ListView):
    template_name = "core/admin_courses.html"
    context_object_name = "courses"

    def get_queryset(self):
        return (
            Course.objects.select_related("instructor", "category")
            .annotate(enrollments_count=Count("enrollments"))
            .order_by("-created_at")
        )


class AdminPaymentListView(AdminRequiredMixin, ListView):
    template_name = "core/admin_payments.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        return PaymentTransaction.objects.select_related(
            "user", "course"
        ).order_by("-created_at")


def custom_page_not_found_view(request, exception=None):
    return render(request, "404.html", status=404)


def custom_server_error_view(request):
    return render(request, "500.html", status=500)


def custom_permission_denied_view(request, exception=None):
    return render(request, "403.html", status=403)
