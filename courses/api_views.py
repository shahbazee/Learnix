from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile

from .models import (
    Certificate,
    Course,
    CourseCategory,
    Enrollment,
    LessonProgress,
)
from .serializers import (
    CertificateSerializer,
    CourseCategorySerializer,
    CourseCreateUpdateSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    EnrollSerializer,
    EnrollmentSerializer,
    LessonProgressSerializer,
    MarkLessonCompleteSerializer,
)


class IsInstructor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return UserProfile.objects.filter(
            user=request.user, role='instructor'
        ).exists()


class CourseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]


class CourseViewSet(viewsets.ModelViewSet):
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in (
            'create', 'update', 'partial_update', 'destroy'
        ):
            return [IsInstructor()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        if self.action in (
            'create', 'update', 'partial_update'
        ):
            return CourseCreateUpdateSerializer
        return CourseListSerializer

    def get_queryset(self):
        qs = Course.objects.select_related(
            'category', 'instructor'
        ).annotate(
            lessons_count=Count(
                'modules__lessons', distinct=True
            )
        ).prefetch_related('modules__lessons')
        if self.action in (
            'update', 'partial_update', 'destroy'
        ):
            return qs.filter(instructor=self.request.user)
        return qs.filter(is_published=True)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)


class EnrollView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrollSerializer

    def post(self, request):
        serializer = EnrollSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data['course']
        enrollment = Enrollment.objects.create(
            user=request.user, course=course
        )
        return Response(
            EnrollmentSerializer(enrollment).data, status=201
        )


class MyEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('course__category', 'course__instructor')


class MarkLessonCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MarkLessonCompleteSerializer

    def post(self, request):
        serializer = MarkLessonCompleteSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        lesson = serializer.validated_data['lesson']
        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save(
                update_fields=['is_completed', 'completed_at']
            )
        enrollment = Enrollment.objects.get(
            user=request.user, course=lesson.module.course
        )
        enrollment.calculate_progress()
        return Response(LessonProgressSerializer(progress).data)


class MyCertificatesView(generics.ListAPIView):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(
            user=self.request.user
        ).select_related('course')
