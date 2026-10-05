from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    CourseCategoryViewSet,
    CourseViewSet,
    EnrollView,
    MarkLessonCompleteView,
    MyCertificatesView,
    MyEnrollmentsView,
)

router = DefaultRouter()
router.register('categories', CourseCategoryViewSet)
router.register('', CourseViewSet, basename='course')

urlpatterns = [
    path(
        'enroll/', EnrollView.as_view(), name='course-enroll'
    ),
    path(
        'my-enrollments/',
        MyEnrollmentsView.as_view(),
        name='my-enrollments',
    ),
    path(
        'lessons/complete/',
        MarkLessonCompleteView.as_view(),
        name='lesson-complete',
    ),
    path(
        'my-certificates/',
        MyCertificatesView.as_view(),
        name='my-certificates',
    ),
    path('', include(router.urls)),
]
