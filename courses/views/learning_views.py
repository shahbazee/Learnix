import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView, TemplateView, View

from core.emails import send_course_enrollment_email
from payments.models import PaymentTransaction

from ..mixins import EnrolledCourseRequiredMixin
from ..models import (
    Certificate,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
)
from ..services import generate_certificate_pdf
from .helpers import _ordered_lessons

logger = logging.getLogger(__name__)


class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "courses/dashboard.html"

    def _get_enrollments(self, user):
        enrollments = list(
            Enrollment.objects.filter(user=user, is_active=True)
            .select_related(
                "course",
                "course__category",
                "course__instructor",
                "course__instructor__profile",
                "certificate",
            )
            .prefetch_related("course__modules__lessons")
        )
        featured_preview_course = None
        if not enrollments:
            featured_preview_course = (
                Course.objects.filter(
                    is_published=True, is_archived=False
                )
                .select_related("category", "instructor")
                .prefetch_related("modules__lessons")
                .first()
            )
        return enrollments, featured_preview_course

    def _active_info(self, user, active_enrollment):
        active_lesson = None
        active_module = None
        remaining_minutes = 0
        if active_enrollment:
            active_lesson = active_enrollment.next_uncompleted_lesson
            if active_lesson:
                active_module = active_lesson.module
                total_seconds = (
                    active_module.lessons.exclude(
                        progresses__user=user,
                        progresses__is_completed=True,
                    ).aggregate(total=Sum("duration_seconds"))["total"]
                    or 0
                )
                if total_seconds:
                    remaining_minutes = int((total_seconds + 59) // 60)
        return active_lesson, active_module, remaining_minutes

    def _learning_stats(self, user, enrollments):
        completed_enrollments = [e for e in enrollments if e.is_completed]
        completed_progresses = LessonProgress.objects.filter(
            user=user, is_completed=True
        ).select_related("lesson")
        total_seconds = (
            completed_progresses.aggregate(
                total=Sum("lesson__duration_seconds")
            )["total"]
            or 0
        )
        verified_certs_count = sum(
            1 for e in enrollments if hasattr(e, "certificate")
        )
        if enrollments:
            aggregate_progress_percent = int(
                round(
                    sum(float(e.progress_percent) for e in enrollments)
                    / len(enrollments)
                )
            )
            certs_percent = (verified_certs_count / len(enrollments)) * 100
        else:
            aggregate_progress_percent = 0
            certs_percent = 0
        return {
            "completed_courses_count": len(completed_enrollments),
            "total_completed_lessons": completed_progresses.count(),
            "learning_hours": round(total_seconds / 3600, 1),
            "verified_certs_count": verified_certs_count,
            "aggregate_progress_percent": aggregate_progress_percent,
            "hours_dashoffset": int(
                415 - (415 * (min(100, aggregate_progress_percent) / 100))
            ),
            "certs_dashoffset": int(
                314 - (314 * (min(100, certs_percent) / 100))
            ),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        enrollments, featured_preview_course = self._get_enrollments(user)

        active_enrollment = next(
            (e for e in enrollments if not e.is_completed),
            enrollments[0] if enrollments else None,
        )
        active_lesson, active_module, remaining_minutes = (
            self._active_info(user, active_enrollment)
        )
        stats = self._learning_stats(user, enrollments)

        recent_purchases = list(
            PaymentTransaction.objects.filter(user=user)
            .select_related("course", "invoice")
            .order_by("-created_at")[:5]
        )

        other_enrollments = [
            e
            for e in enrollments
            if active_enrollment and e.id != active_enrollment.id
        ]

        hero_thumbnail_url = "/static/images/courses/default-course.svg"
        if active_enrollment and active_enrollment.course:
            hero_thumbnail_url = active_enrollment.course.get_thumbnail_url
        elif featured_preview_course:
            hero_thumbnail_url = featured_preview_course.get_thumbnail_url

        latest_purchase = recent_purchases[0] if recent_purchases else None

        context.update(
            {
                "enrollments": enrollments,
                "active_enrollment": active_enrollment,
                "featured_preview_course": featured_preview_course,
                "hero_thumbnail_url": hero_thumbnail_url,
                "active_lesson": active_lesson,
                "active_module": active_module,
                "remaining_minutes": remaining_minutes,
                "other_enrollments": other_enrollments,
                "completed_courses_count": stats["completed_courses_count"],
                "total_completed_lessons": stats["total_completed_lessons"],
                "learning_hours": stats["learning_hours"],
                "verified_certs_count": stats["verified_certs_count"],
                "aggregate_progress_percent": (
                    stats["aggregate_progress_percent"]
                ),
                "hours_dashoffset": stats["hours_dashoffset"],
                "certs_dashoffset": stats["certs_dashoffset"],
                "recent_purchases": recent_purchases,
                "stripe_customer_id": (
                    getattr(latest_purchase, "stripe_customer_id", None)
                    if latest_purchase
                    else None
                ),
            }
        )
        return context


class EnrollCourseView(LoginRequiredMixin, View):
    def post(self, request, slug):
        course = get_object_or_404(
            Course, slug=slug, is_published=True, is_archived=False
        )

        is_free_course = bool(
            getattr(course, "is_free", False)
            or not course.price
            or course.price == 0
        )
        if not is_free_course:
            messages.warning(
                request,
                "Please complete the payment to enroll in this course.",
            )
            return redirect("courses:course_detail", slug=course.slug)

        with transaction.atomic():
            enrollment, created = Enrollment.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={
                    "is_active": True,
                    "progress_percent": 0.00,
                },
            )

            if not created and enrollment.is_active:
                messages.info(
                    request,
                    f"You are already actively enrolled in "
                    f"'{course.title}'.",
                )
                return redirect("courses:dashboard")

            enrollment.is_active = True
            enrollment.save(update_fields=["is_active"])

        try:
            send_course_enrollment_email(request.user, course, enrollment)
        except Exception as exc:
            logger.warning(
                f"Could not dispatch course enrollment email: {exc}"
            )

        messages.success(
            request,
            f"Congratulations! You have enrolled in "
            f"'{course.title}'. Your learning journey begins now.",
        )
        return redirect("courses:dashboard")


class UnenrollView(LoginRequiredMixin, View):
    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        enrollment = request.user.enrollments.filter(
            course=course, is_active=True
        ).first()
        if enrollment is None:
            messages.error(
                request, "You are not enrolled in this course."
            )
            return redirect("courses:dashboard")
        enrollment.is_active = False
        enrollment.save(update_fields=["is_active"])
        messages.success(
            request,
            f"You have unenrolled from '{course.title}'. "
            f"You can re-enroll any time from the course page.",
        )
        return redirect("courses:dashboard")


class LessonView(EnrolledCourseRequiredMixin, DetailView):
    model = Lesson
    template_name = "courses/lesson_player.html"
    context_object_name = "lesson"
    pk_url_kwarg = "lesson_id"

    def get_queryset(self):
        return Lesson.objects.filter(
            module__course__slug=self.kwargs["slug"],
            module__course__is_published=True,
        ).select_related("module", "module__course")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        course = lesson.module.course
        context["course"] = course

        progress, _ = LessonProgress.objects.get_or_create(
            user=self.request.user, lesson=lesson
        )
        context["lesson_progress"] = progress

        enrollment = Enrollment.objects.filter(
            user=self.request.user, course=course
        ).first()
        context["enrollment"] = enrollment

        completed_lesson_ids = set(
            LessonProgress.objects.filter(
                user=self.request.user,
                lesson__module__course=course,
                is_completed=True,
            ).values_list("lesson_id", flat=True)
        )
        context["completed_lesson_ids"] = completed_lesson_ids

        modules = list(
            course.modules.prefetch_related("lessons").order_by("order_number")
        )
        context["modules"] = modules

        all_lessons = _ordered_lessons(modules)
        current_idx = next(
            (
                idx
                for idx, item in enumerate(all_lessons)
                if item.id == lesson.id
            ),
            -1,
        )

        context["prev_lesson"] = (
            all_lessons[current_idx - 1] if current_idx > 0 else None
        )
        context["next_lesson"] = (
            all_lessons[current_idx + 1]
            if 0 <= current_idx < len(all_lessons) - 1
            else None
        )
        context["total_lessons_count"] = len(all_lessons)
        context["current_lesson_number"] = current_idx + 1
        return context


class MarkCompleteView(View):
    def post(self, request, lesson_id):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Authentication required.",
                },
                status=401,
            )

        lesson = get_object_or_404(Lesson, id=lesson_id)
        course = lesson.module.course

        if (
            not request.user.is_staff
            and not request.user.enrollments.filter(
                course=course, is_active=True
            ).exists()
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Enrollment required.",
                },
                status=403,
            )

        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        is_completed = request.POST.get("is_completed", "true").lower() in [
            "true",
            "1",
            "yes",
        ]
        progress.is_completed = is_completed
        progress.completed_at = timezone.now() if is_completed else None
        progress.save()

        enrollment = request.user.enrollments.filter(
            course=course, is_active=True
        ).first()
        progress_pct = 0.00
        completed_count = 0
        total_count = course.total_lessons_count

        if enrollment:
            progress_pct = enrollment.calculate_progress()
            completed_count = enrollment.completed_lessons_count
            if is_completed and getattr(enrollment, "is_completed", False):
                try:
                    Certificate.issue_for_enrollment(enrollment)
                except Exception as exc:
                    logger.warning(
                        "Could not issue certificate for "
                        f"enrollment {enrollment.pk}: {exc}"
                    )

        return JsonResponse(
            {
                "success": True,
                "is_completed": progress.is_completed,
                "progress_percent": float(progress_pct),
                "completed_count": completed_count,
                "total_count": total_count,
            }
        )


class CertificateDetailView(DetailView):
    model = Certificate
    slug_field = "certificate_id"
    slug_url_kwarg = "certificate_id"
    template_name = "courses/certificate_detail.html"
    context_object_name = "certificate"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verification_url"] = self.request.build_absolute_uri()
        return context


class DownloadCertificatePDFView(View):
    def get(self, request, certificate_id, *args, **kwargs):
        certificate = get_object_or_404(
            Certificate, certificate_id=certificate_id
        )
        pdf_bytes = generate_certificate_pdf(certificate)
        if not pdf_bytes:
            raise Http404("Certificate PDF could not be generated.")

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = f"Learnix_Certificate_{certificate.certificate_id}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
