import csv

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import (
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
    View,
)

from ..forms import CourseForm
from ..mixins import InstructorRequiredMixin, OwnCourseObjectMixin
from payments.models import PaymentTransaction

from ..models import Course, Enrollment
from .helpers import _get_owned_course_or_403


class InstructorStudioView(InstructorRequiredMixin, TemplateView):
    template_name = "courses/instructor_studio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        authored_courses = list(
            Course.objects.filter(instructor=user)
            .select_related("category")
            .prefetch_related("modules__lessons", "enrollments")
        )

        course_data = []
        total_gross = 0.0
        total_students = 0
        rating_sum = 0.0
        rated_courses_count = 0

        for course in authored_courses:
            enrolled_count = sum(
                1
                for enrollment in course.enrollments.all()
                if enrollment.is_active
            )
            revenue = (
                PaymentTransaction.objects.filter(
                    course=course, status="COMPLETED"
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )
            revenue_float = float(revenue)

            total_gross += revenue_float
            total_students += enrolled_count

            if course.rating:
                rating_sum += float(course.rating)
                rated_courses_count += 1

            course_data.append(
                {
                    "course": course,
                    "enrolled_count": enrolled_count,
                    "gross_revenue": revenue_float,
                    "rating": (float(course.rating) if course.rating else 0.0),
                    "reviews_count": getattr(course, "reviews_count", 0) or 0,
                    "status": (
                        "PUBLISHED" if course.is_published else "DRAFT"
                    ),
                    "lessons_count": sum(
                        len(module.lessons.all())
                        for module in course.modules.all()
                    ),
                }
            )

        avg_rating = (
            round(rating_sum / rated_courses_count, 2)
            if rated_courses_count > 0
            else 0.0
        )

        context.update(
            {
                "authored_courses": authored_courses,
                "course_data": course_data,
                "total_courses_count": len(authored_courses),
                "published_courses_count": sum(
                    1 for item in course_data if item["status"] == "PUBLISHED"
                ),
                "draft_courses_count": sum(
                    1 for item in course_data if item["status"] == "DRAFT"
                ),
                "total_gross": f"{total_gross:,.2f}",
                "total_students": total_students,
                "avg_rating": avg_rating,
                "next_payout": f"{max(total_gross * 0.70, 0.0):,.2f}",
            }
        )
        return context


class ExportFinancialsCSVView(InstructorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="Learnix_Financials_Ledger.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Order Reference",
                "Date",
                "Course Title",
                "Student Username",
                "Amount",
                "Currency",
                "Status",
            ]
        )

        if request.user.is_staff:
            transactions = PaymentTransaction.objects.select_related(
                "course", "user"
            ).order_by("-created_at")[:100]
        else:
            transactions = (
                PaymentTransaction.objects.filter(
                    course__instructor=request.user
                )
                .select_related("course", "user")
                .order_by("-created_at")[:100]
            )

        for tx in transactions:
            writer.writerow(
                [
                    tx.order_number,
                    tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    (tx.course.title if tx.course else "General Masterclass"),
                    (tx.user.username if tx.user else "guest"),
                    str(tx.amount),
                    tx.currency.upper(),
                    tx.status.upper(),
                ]
            )

        return response


class InstructorCourseCreateView(InstructorRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/instructor_course_form.html"

    def form_valid(self, form):
        course = form.save(commit=False)
        course.instructor = self.request.user
        course.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()
        messages.success(
            self.request,
            f"Course '{course.title}' created successfully!",
        )
        return redirect("courses:instructor_studio")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create New Masterclass"
        context["submit_btn_text"] = "Publish Masterclass"
        return context


class InstructorCourseUpdateView(
    InstructorRequiredMixin, OwnCourseObjectMixin, UpdateView
):
    model = Course
    form_class = CourseForm
    template_name = "courses/instructor_course_form.html"
    slug_url_kwarg = "slug"

    def form_valid(self, form):
        course = form.save()
        messages.success(
            self.request,
            f"Course '{course.title}' updated successfully!",
        )
        return redirect("courses:instructor_studio")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit '{self.object.title}'"
        context["submit_btn_text"] = "Save Changes"
        context["course"] = self.object
        return context


class InstructorCourseDeleteView(InstructorRequiredMixin, View):
    def post(self, request, slug):
        course = _get_owned_course_or_403(request.user, slug)
        title = course.title
        course.delete()
        messages.success(request, f"Course '{title}' has been deleted.")
        return redirect("courses:instructor_studio")


class InstructorCourseStudentsView(
    InstructorRequiredMixin, OwnCourseObjectMixin, DetailView
):
    model = Course
    template_name = "courses/instructor_course_students.html"
    context_object_name = "course"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        active_enrollments = (
            Enrollment.objects.filter(course=course, is_active=True)
            .select_related("user", "user__profile")
            .order_by("-enrolled_at")
        )
        context["enrollments"] = active_enrollments
        context["total_students"] = active_enrollments.count()
        return context
