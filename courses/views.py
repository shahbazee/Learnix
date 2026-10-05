import csv
import logging
from collections import Counter
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from accounts.mixins import (
    EnrolledCourseRequiredMixin,
    InstructorRequiredMixin,
)
from core.emails import send_course_enrollment_email
from payments.models import PaymentTransaction

from .forms import CourseForm
from .models import (
    Certificate,
    Course,
    CourseCategory,
    Enrollment,
    Lesson,
    LessonProgress,
)
from .services import generate_certificate_pdf

logger = logging.getLogger(__name__)


def _published_course_queryset():
    return Course.objects.select_related(
        'instructor', 'category', 'instructor__profile'
    ).prefetch_related('modules__lessons')


def _ordered_lessons(modules):
    lessons = []
    for module in modules:
        lessons.extend(
            sorted(
                module.lessons.all(),
                key=lambda lesson: (lesson.order_number, lesson.id),
            )
        )
    return lessons


def _get_owned_course_or_403(user, slug):
    course = get_object_or_404(Course, slug=slug)
    if course.instructor != user and not user.is_staff:
        raise PermissionDenied(
            "You do not have authorization to access another "
            "instructor's course."
        )
    return course


class OwnCourseObjectMixin:
    def get_object(self, queryset=None):
        course = super().get_object(queryset)
        if (
            course.instructor != self.request.user
            and not self.request.user.is_staff
        ):
            raise PermissionDenied(
                "You do not have authorization to access another "
                "instructor's course."
            )
        return course


class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 6

    def get_queryset(self):
        queryset = _published_course_queryset().filter(is_published=True)

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(short_description__icontains=q)
                | Q(category__name__icontains=q)
                | Q(instructor__username__icontains=q)
                | Q(instructor__first_name__icontains=q)
                | Q(instructor__last_name__icontains=q)
            )

        category_slug = self.request.GET.get('category', '').strip()
        if category_slug and category_slug != 'all':
            queryset = queryset.filter(category__slug=category_slug)

        level = self.request.GET.get('level', '').strip().upper()
        if level in ['BEGINNER', 'INTERMEDIATE', 'ADVANCED']:
            queryset = queryset.filter(level=level)

        sort = self.request.GET.get('sort', 'highest_rated').strip()
        if sort == 'highest_rated':
            queryset = queryset.order_by('-rating', '-reviews_count')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'price_low':
            queryset = queryset.order_by('price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-price')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = CourseCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category', 'all')
        context['selected_level'] = self.request.GET.get('level', 'ALL')
        context['selected_sort'] = self.request.GET.get(
            'sort', 'highest_rated'
        )
        context['search_query'] = self.request.GET.get('q', '')
        context['total_published_count'] = Course.objects.filter(
            is_published=True
        ).count()

        if self.request.user.is_authenticated:
            context['enrolled_course_ids'] = set(
                self.request.user.enrollments.filter(
                    is_active=True
                ).values_list('course_id', flat=True)
            )
        else:
            context['enrolled_course_ids'] = set()
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        queryset = _published_course_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        modules = list(
            course.modules.prefetch_related('lessons').order_by(
                'order_number'
            )
        )
        all_lessons = _ordered_lessons(modules)

        first_preview = next(
            (lesson for lesson in all_lessons if lesson.is_preview),
            None,
        )
        preview_count = sum(
            1 for lesson in all_lessons if lesson.is_preview
        )

        context['modules'] = modules
        context['first_preview_lesson'] = first_preview
        context['first_lesson'] = (
            all_lessons[0] if all_lessons else None
        )
        context['total_preview_count'] = preview_count
        context['total_lessons_count'] = len(all_lessons)

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
            self.request.user.is_authenticated
            and self.request.user.is_staff
        )
        has_access = bool(enrollment or is_owner or is_staff)

        context['is_enrolled'] = has_access
        context['has_purchased'] = bool(enrollment)
        context['is_owner'] = is_owner
        context['is_staff'] = is_staff
        context['enrollment'] = enrollment
        context['next_lesson'] = next_lesson or (
            all_lessons[0] if all_lessons else None
        )
        return context


class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'courses/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        enrollments = list(
            Enrollment.objects.filter(user=user, is_active=True)
            .select_related(
                'course',
                'course__category',
                'course__instructor',
                'course__instructor__profile',
                'certificate',
            )
            .prefetch_related('course__modules__lessons')
        )

        featured_preview_course = None
        if not enrollments:
            featured_preview_course = (
                Course.objects.filter(is_published=True)
                .select_related('category', 'instructor')
                .prefetch_related('modules__lessons')
                .first()
            )

        active_enrollment = next(
            (e for e in enrollments if not e.is_completed),
            enrollments[0] if enrollments else None,
        )

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
                    ).aggregate(total=Sum('duration_seconds'))['total']
                    or 0
                )
                if total_seconds:
                    remaining_minutes = int(
                        (total_seconds + 59) // 60
                    )

        completed_enrollments = [
            e for e in enrollments if e.is_completed
        ]
        completed_courses_count = len(completed_enrollments)

        completed_progresses = LessonProgress.objects.filter(
            user=user, is_completed=True
        ).select_related('lesson')
        total_completed_lessons = completed_progresses.count()
        total_seconds = (
            completed_progresses.aggregate(
                total=Sum('lesson__duration_seconds')
            )['total']
            or 0
        )
        learning_hours = round(total_seconds / 3600, 1)

        verified_certs_count = sum(
            1 for e in enrollments if hasattr(e, 'certificate')
        )

        if enrollments:
            aggregate_progress_percent = int(
                round(
                    sum(
                        float(e.progress_percent)
                        for e in enrollments
                    )
                    / len(enrollments)
                )
            )
        else:
            aggregate_progress_percent = 0

        hours_dashoffset = int(
            415
            - (415 * (min(100, aggregate_progress_percent) / 100))
        )
        if enrollments:
            certs_percent = (
                verified_certs_count / len(enrollments)
            ) * 100
        else:
            certs_percent = 0
        certs_dashoffset = int(
            314 - (314 * (min(100, certs_percent) / 100))
        )

        weekly_activity = self._generate_study_velocity_grid(user)

        recent_purchases = list(
            PaymentTransaction.objects.filter(user=user)
            .select_related('course', 'invoice')
            .order_by('-created_at')[:5]
        )

        other_enrollments = [
            e
            for e in enrollments
            if active_enrollment and e.id != active_enrollment.id
        ]

        hero_thumbnail_url = "/static/images/courses/default-course.svg"
        if active_enrollment and active_enrollment.course:
            hero_thumbnail_url = (
                active_enrollment.course.get_thumbnail_url
            )
        elif featured_preview_course:
            hero_thumbnail_url = (
                featured_preview_course.get_thumbnail_url
            )

        latest_purchase = recent_purchases[0] if recent_purchases else None

        context.update(
            {
                'enrollments': enrollments,
                'active_enrollment': active_enrollment,
                'featured_preview_course': featured_preview_course,
                'hero_thumbnail_url': hero_thumbnail_url,
                'active_lesson': active_lesson,
                'active_module': active_module,
                'remaining_minutes': remaining_minutes,
                'other_enrollments': other_enrollments,
                'completed_courses_count': completed_courses_count,
                'total_completed_lessons': total_completed_lessons,
                'learning_hours': learning_hours,
                'verified_certs_count': verified_certs_count,
                'aggregate_progress_percent': aggregate_progress_percent,
                'hours_dashoffset': hours_dashoffset,
                'certs_dashoffset': certs_dashoffset,
                'weekly_activity': weekly_activity,
                'recent_purchases': recent_purchases,
                'stripe_customer_id': (
                    getattr(latest_purchase, 'stripe_customer_id', None)
                    if latest_purchase
                    else None
                ),
                'streak_days': 0,
                'xp_points': 0,
                'upcoming_session': None,
            }
        )
        return context

    def _generate_study_velocity_grid(self, user):
        today = timezone.localdate()
        start_date = today - timedelta(days=83)

        counts = Counter()
        completed_dates = LessonProgress.objects.filter(
            user=user,
            is_completed=True,
            completed_at__isnull=False,
            completed_at__date__gte=start_date,
        ).values_list('completed_at', flat=True)

        for completed_at in completed_dates:
            if timezone.is_aware(completed_at):
                completed_date = timezone.localtime(completed_at).date()
            else:
                completed_date = completed_at.date()
            counts[completed_date] += 1

        color_classes = {
            0: "bg-slate-100",
            1: "bg-purple-200",
            2: "bg-cyan-300",
            3: "bg-purple-400",
            4: "bg-violet-600",
        }

        weeks_data = []
        for week_index in range(12):
            week_start = start_date + timedelta(days=week_index * 7)
            days_data = []
            for day_offset in range(7):
                day = week_start + timedelta(days=day_offset)
                level = min(counts.get(day, 0), 4)
                is_current = day == today
                css_class = color_classes.get(level, "bg-slate-100")
                if is_current:
                    css_class = (
                        "bg-violet-600 animate-pulse "
                        "shadow-[0_0_10px_rgba(124,58,237,0.7)]"
                    )
                days_data.append(
                    {
                        'level': level,
                        'class': css_class,
                        'is_current': is_current,
                    }
                )
            weeks_data.append(
                {'week_number': week_index + 1, 'days': days_data}
            )

        return weeks_data


class EnrollCourseView(LoginRequiredMixin, View):
    def post(self, request, slug):
        course = get_object_or_404(
            Course, slug=slug, is_published=True
        )

        is_free_course = bool(
            getattr(course, 'is_free', False)
            or not course.price
            or course.price == 0
        )
        if not is_free_course:
            messages.warning(
                request,
                "Please complete the payment to enroll in this course.",
            )
            return redirect(
                'courses:course_detail', slug=course.slug
            )

        with transaction.atomic():
            enrollment, created = Enrollment.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={
                    'is_active': True,
                    'progress_percent': 0.00,
                },
            )

            if not created and enrollment.is_active:
                messages.info(
                    request,
                    f"You are already actively enrolled in "
                    f"'{course.title}'.",
                )
                return redirect('courses:dashboard')

            enrollment.is_active = True
            enrollment.save(update_fields=['is_active'])

        try:
            send_course_enrollment_email(
                request.user, course, enrollment
            )
        except Exception as exc:
            logger.warning(
                f"Could not dispatch course enrollment email: {exc}"
            )

        messages.success(
            request,
            f"Congratulations! You have enrolled in "
            f"'{course.title}'. Your learning journey begins now.",
        )
        return redirect('courses:dashboard')


class LessonView(EnrolledCourseRequiredMixin, DetailView):
    model = Lesson
    template_name = 'courses/lesson_player.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'

    def get_queryset(self):
        return Lesson.objects.filter(
            module__course__slug=self.kwargs['slug'],
            module__course__is_published=True,
        ).select_related('module', 'module__course')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        course = lesson.module.course
        context['course'] = course

        progress, _ = LessonProgress.objects.get_or_create(
            user=self.request.user, lesson=lesson
        )
        context['lesson_progress'] = progress

        enrollment = Enrollment.objects.filter(
            user=self.request.user, course=course
        ).first()
        context['enrollment'] = enrollment

        completed_lesson_ids = set(
            LessonProgress.objects.filter(
                user=self.request.user,
                lesson__module__course=course,
                is_completed=True,
            ).values_list('lesson_id', flat=True)
        )
        context['completed_lesson_ids'] = completed_lesson_ids

        modules = list(
            course.modules.prefetch_related('lessons').order_by(
                'order_number'
            )
        )
        context['modules'] = modules

        all_lessons = _ordered_lessons(modules)
        current_idx = next(
            (
                idx
                for idx, item in enumerate(all_lessons)
                if item.id == lesson.id
            ),
            -1,
        )

        context['prev_lesson'] = (
            all_lessons[current_idx - 1] if current_idx > 0 else None
        )
        context['next_lesson'] = (
            all_lessons[current_idx + 1]
            if 0 <= current_idx < len(all_lessons) - 1
            else None
        )
        context['total_lessons_count'] = len(all_lessons)
        context['current_lesson_number'] = current_idx + 1
        return context


class MarkCompleteView(View):
    def post(self, request, lesson_id):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Authentication required.',
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
                    'success': False,
                    'error': 'Enrollment required.',
                },
                status=403,
            )

        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        is_completed = request.POST.get(
            'is_completed', 'true'
        ).lower() in ['true', '1', 'yes']
        progress.is_completed = is_completed
        progress.completed_at = (
            timezone.now() if is_completed else None
        )
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
            if is_completed and getattr(
                enrollment, 'is_completed', False
            ):
                try:
                    Certificate.issue_for_enrollment(enrollment)
                except Exception as exc:
                    logger.warning(
                        "Could not issue certificate for "
                        f"enrollment {enrollment.pk}: {exc}"
                    )

        return JsonResponse(
            {
                'success': True,
                'is_completed': progress.is_completed,
                'progress_percent': float(progress_pct),
                'completed_count': completed_count,
                'total_count': total_count,
            }
        )


def course_search_api(request):
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'results': []})

    courses = Course.objects.filter(is_published=True).filter(
        Q(title__icontains=q)
        | Q(short_description__icontains=q)
        | Q(category__name__icontains=q)
        | Q(instructor__first_name__icontains=q)
        | Q(instructor__last_name__icontains=q)
    ).select_related('category', 'instructor')[:6]

    results = []
    for course in courses:
        results.append(
            {
                'id': course.id,
                'title': course.title,
                'slug': course.slug,
                'category': (
                    course.category.name
                    if course.category
                    else 'General'
                ),
                'level': course.get_level_display(),
                'price': (
                    str(course.price)
                    if not course.is_free
                    else 'Free'
                ),
                'rating': str(course.rating),
                'thumbnail_url': course.get_thumbnail_url,
                'url': reverse(
                    'courses:course_detail',
                    kwargs={'slug': course.slug},
                ),
            }
        )

    return JsonResponse({'results': results})


def lesson_preview_api(request, slug, lesson_id):
    course = get_object_or_404(
        Course, slug=slug, is_published=True
    )
    lesson = get_object_or_404(
        Lesson, id=lesson_id, module__course=course
    )

    is_staff_or_owner = request.user.is_authenticated and (
        request.user.is_staff or request.user == course.instructor
    )

    if not lesson.is_preview and not is_staff_or_owner:
        return JsonResponse(
            {
                'success': False,
                'error': (
                    'Enrolled access required to view this lesson.'
                ),
                'is_preview': False,
            },
            status=403,
        )

    return JsonResponse(
        {
            'success': True,
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'module_title': lesson.module.title,
                'module_number': lesson.module.order_number,
                'order_number': lesson.order_number,
                'duration': lesson.formatted_duration,
                'duration_seconds': lesson.duration_seconds,
                'video_url': lesson.video_url,
                'content': lesson.content,
                'is_preview': lesson.is_preview,
            },
        }
    )


class CertificateDetailView(DetailView):
    model = Certificate
    slug_field = 'certificate_id'
    slug_url_kwarg = 'certificate_id'
    template_name = 'courses/certificate_detail.html'
    context_object_name = 'certificate'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verification_url'] = (
            self.request.build_absolute_uri()
        )
        return context


class DownloadCertificatePDFView(View):
    def get(self, request, certificate_id, *args, **kwargs):
        certificate = get_object_or_404(
            Certificate, certificate_id=certificate_id
        )
        pdf_bytes = generate_certificate_pdf(certificate)
        if not pdf_bytes:
            raise Http404("Certificate PDF could not be generated.")

        response = HttpResponse(
            pdf_bytes, content_type='application/pdf'
        )
        filename = (
            f"Learnix_Certificate_{certificate.certificate_id}.pdf"
        )
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"'
        )
        return response


class InstructorStudioView(InstructorRequiredMixin, TemplateView):
    template_name = 'courses/instructor_studio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        authored_courses = list(
            Course.objects.filter(instructor=user)
            .select_related('category')
            .prefetch_related('modules__lessons', 'enrollments')
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
                    course=course, status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total']
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
                    'course': course,
                    'enrolled_count': enrolled_count,
                    'gross_revenue': revenue_float,
                    'rating': (
                        float(course.rating) if course.rating else 0.0
                    ),
                    'reviews_count': getattr(
                        course, 'reviews_count', 0
                    )
                    or 0,
                    'status': (
                        'PUBLISHED'
                        if course.is_published
                        else 'DRAFT'
                    ),
                    'lessons_count': sum(
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
                'authored_courses': authored_courses,
                'course_data': course_data,
                'total_courses_count': len(authored_courses),
                'published_courses_count': sum(
                    1
                    for item in course_data
                    if item['status'] == 'PUBLISHED'
                ),
                'draft_courses_count': sum(
                    1
                    for item in course_data
                    if item['status'] == 'DRAFT'
                ),
                'total_gross': f"{total_gross:,.2f}",
                'total_students': total_students,
                'avg_rating': avg_rating,
                'next_payout': f"{max(total_gross * 0.70, 0.0):,.2f}",
            }
        )
        return context


class ExportFinancialsCSVView(InstructorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="Learnix_Financials_Ledger.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                'Order Reference',
                'Date',
                'Course Title',
                'Student Email',
                'Amount',
                'Currency',
                'Status',
            ]
        )

        if request.user.is_staff:
            transactions = PaymentTransaction.objects.select_related(
                'course', 'user'
            ).order_by('-created_at')[:100]
        else:
            transactions = PaymentTransaction.objects.filter(
                course__instructor=request.user
            ).select_related('course', 'user').order_by(
                '-created_at'
            )[:100]

        for tx in transactions:
            writer.writerow(
                [
                    tx.order_number,
                    tx.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    (
                        tx.course.title
                        if tx.course
                        else 'General Masterclass'
                    ),
                    (
                        tx.user.email
                        if tx.user
                        else 'guest@learnix.internal'
                    ),
                    str(tx.amount),
                    tx.currency.upper(),
                    tx.status.upper(),
                ]
            )

        return response


class InstructorCourseCreateView(InstructorRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/instructor_course_form.html'

    def form_valid(self, form):
        course = form.save(commit=False)
        course.instructor = self.request.user
        course.save()
        if hasattr(form, 'save_m2m'):
            form.save_m2m()
        messages.success(
            self.request,
            f"Course '{course.title}' created successfully!",
        )
        return redirect('courses:instructor_studio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Create New Masterclass"
        context['submit_btn_text'] = "Publish Masterclass"
        return context


class InstructorCourseUpdateView(
    InstructorRequiredMixin, OwnCourseObjectMixin, UpdateView
):
    model = Course
    form_class = CourseForm
    template_name = 'courses/instructor_course_form.html'
    slug_url_kwarg = 'slug'

    def form_valid(self, form):
        course = form.save()
        messages.success(
            self.request,
            f"Course '{course.title}' updated successfully!",
        )
        return redirect('courses:instructor_studio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Edit '{self.object.title}'"
        context['submit_btn_text'] = "Save Changes"
        context['course'] = self.object
        return context


class InstructorCourseDeleteView(InstructorRequiredMixin, View):
    def post(self, request, slug):
        course = _get_owned_course_or_403(request.user, slug)
        title = course.title
        course.delete()
        messages.success(
            request, f"Course '{title}' has been deleted."
        )
        return redirect('courses:instructor_studio')


class InstructorCourseStudentsView(
    InstructorRequiredMixin, OwnCourseObjectMixin, DetailView
):
    model = Course
    template_name = 'courses/instructor_course_students.html'
    context_object_name = 'course'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        active_enrollments = Enrollment.objects.filter(
            course=course, is_active=True
        ).select_related('user', 'user__profile').order_by(
            '-enrolled_at'
        )
        context['enrollments'] = active_enrollments
        context['total_students'] = active_enrollments.count()
        return context
