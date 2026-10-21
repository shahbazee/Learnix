from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from ..models import Course, CourseCategory, Lesson, Review
from .helpers import _ordered_lessons


def _published_course_queryset():
    return Course.objects.filter(is_archived=False).select_related(
        "instructor", "category", "instructor__profile"
    ).prefetch_related("modules__lessons")


class CourseListView(ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    paginate_by = 6

    def get_queryset(self):
        queryset = _published_course_queryset().filter(is_published=True)

        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(short_description__icontains=q)
                | Q(category__name__icontains=q)
                | Q(instructor__username__icontains=q)
                | Q(instructor__first_name__icontains=q)
                | Q(instructor__last_name__icontains=q)
            )

        category_slug = self.request.GET.get("category", "").strip()
        if category_slug and category_slug != "all":
            queryset = queryset.filter(category__slug=category_slug)

        level = self.request.GET.get("level", "").strip().upper()
        if level in ["BEGINNER", "INTERMEDIATE", "ADVANCED"]:
            queryset = queryset.filter(level=level)

        sort = self.request.GET.get("sort", "highest_rated").strip()
        if sort == "highest_rated":
            queryset = queryset.order_by("-rating", "-reviews_count")
        elif sort == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort == "price_low":
            queryset = queryset.order_by("price")
        elif sort == "price_high":
            queryset = queryset.order_by("-price")
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = CourseCategory.objects.all()
        context["selected_category"] = self.request.GET.get("category", "all")
        context["selected_level"] = self.request.GET.get("level", "ALL")
        context["selected_sort"] = self.request.GET.get(
            "sort", "highest_rated"
        )
        context["search_query"] = self.request.GET.get("q", "")
        context["total_published_count"] = Course.objects.filter(
            is_published=True, is_archived=False
        ).count()

        if self.request.user.is_authenticated:
            context["enrolled_course_ids"] = set(
                self.request.user.enrollments.filter(
                    is_active=True
                ).values_list("course_id", flat=True)
            )
        else:
            context["enrolled_course_ids"] = set()
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"

    def get_queryset(self):
        queryset = _published_course_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        modules = list(
            course.modules.prefetch_related("lessons").order_by("order_number")
        )
        all_lessons = _ordered_lessons(modules)

        first_preview = next(
            (lesson for lesson in all_lessons if lesson.is_preview),
            None,
        )
        preview_count = sum(1 for lesson in all_lessons if lesson.is_preview)

        context["modules"] = modules
        context["first_preview_lesson"] = first_preview
        context["first_lesson"] = all_lessons[0] if all_lessons else None
        context["total_preview_count"] = preview_count
        context["total_lessons_count"] = len(all_lessons)

        enrollment = None
        next_lesson = None
        if self.request.user.is_authenticated:
            enrollment = self.request.user.enrollments.filter(
                course=course, is_active=True
            ).first()
            if enrollment:
                next_lesson = enrollment.next_uncompleted_lesson

        is_owner = (
            self.request.user.is_authenticated
            and self.request.user == course.instructor
        )
        is_staff = (
            self.request.user.is_authenticated and self.request.user.is_staff
        )
        has_access = bool(enrollment or is_owner or is_staff)

        context["is_enrolled"] = has_access
        context["has_purchased"] = bool(enrollment)
        context["is_owner"] = is_owner
        context["is_staff"] = is_staff
        context["enrollment"] = enrollment
        context["next_lesson"] = next_lesson or (
            all_lessons[0] if all_lessons else None
        )
        context["reviews"] = course.reviews.select_related(
            "user", "user__profile"
        )[:10]
        user_review = None
        if self.request.user.is_authenticated:
            user_review = course.reviews.filter(
                user=self.request.user
            ).first()
        context["user_review"] = user_review
        context["can_review"] = bool(enrollment)
        return context


class CourseReviewView(LoginRequiredMixin, View):
    def post(self, request, slug):
        course = get_object_or_404(
            Course, slug=slug, is_published=True, is_archived=False
        )
        enrollment = request.user.enrollments.filter(
            course=course, is_active=True
        ).first()
        if enrollment is None:
            messages.error(
                request,
                "Only enrolled students can review this course.",
            )
            return redirect("courses:course_detail", slug=course.slug)
        try:
            rating = int(request.POST.get("rating", ""))
        except (TypeError, ValueError):
            rating = 0
        if rating < 1 or rating > 5:
            messages.error(
                request, "Please select a rating from 1 to 5."
            )
            return redirect("courses:course_detail", slug=course.slug)
        Review.objects.update_or_create(
            user=request.user,
            course=course,
            defaults={
                "rating": rating,
                "comment": (request.POST.get("comment") or "").strip(),
            },
        )
        messages.success(request, "Thanks! Your review has been saved.")
        return redirect("courses:course_detail", slug=course.slug)


def course_search_api(request):
    q = request.GET.get("q", "").strip()
    if not q or len(q) < 2:
        return JsonResponse({"results": []})

    courses = (
        Course.objects.filter(is_published=True, is_archived=False)
        .filter(
            Q(title__icontains=q)
            | Q(short_description__icontains=q)
            | Q(category__name__icontains=q)
            | Q(instructor__first_name__icontains=q)
            | Q(instructor__last_name__icontains=q)
        )
        .select_related("category", "instructor")[:6]
    )

    results = []
    for course in courses:
        results.append(
            {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
                "category": (
                    course.category.name if course.category else "General"
                ),
                "level": course.get_level_display(),
                "price": (str(course.price) if not course.is_free else "Free"),
                "rating": str(course.rating),
                "thumbnail_url": course.get_thumbnail_url,
                "url": reverse(
                    "courses:course_detail",
                    kwargs={"slug": course.slug},
                ),
            }
        )

    return JsonResponse({"results": results})


def lesson_preview_api(request, slug, lesson_id):
    course = get_object_or_404(
        Course, slug=slug, is_published=True, is_archived=False
    )
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    is_staff_or_owner = request.user.is_authenticated and (
        request.user.is_staff or request.user == course.instructor
    )

    if not lesson.is_preview and not is_staff_or_owner:
        return JsonResponse(
            {
                "success": False,
                "error": ("Enrolled access required to view this lesson."),
                "is_preview": False,
            },
            status=403,
        )

    return JsonResponse(
        {
            "success": True,
            "lesson": {
                "id": lesson.id,
                "title": lesson.title,
                "module_title": lesson.module.title,
                "module_number": lesson.module.order_number,
                "order_number": lesson.order_number,
                "duration": lesson.formatted_duration,
                "duration_seconds": lesson.duration_seconds,
                "video_url": lesson.video_url,
                "content": lesson.content,
                "is_preview": lesson.is_preview,
            },
        }
    )
