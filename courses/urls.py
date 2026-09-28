"""
URL routing configuration for courses application.
"""

from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.CourseListView.as_view(), name='course_list'),
    path('dashboard/', views.StudentDashboardView.as_view(), name='dashboard'),
    path('api/search/', views.course_search_api, name='search_api'),
    path('lesson/<int:lesson_id>/complete/', views.MarkCompleteView.as_view(), name='mark_complete'),
    path('certificates/<str:certificate_id>/', views.CertificateDetailView.as_view(), name='certificate_detail'),
    path('certificates/<str:certificate_id>/download/', views.DownloadCertificatePDFView.as_view(), name='download_certificate_pdf'),
    path('instructor/studio/', views.InstructorStudioView.as_view(), name='instructor_studio'),
    path('instructor/studio/export-financials/', views.ExportFinancialsCSVView.as_view(), name='export_financials_csv'),
    path('instructor/course/create/', views.InstructorCourseCreateView.as_view(), name='instructor_course_create'),
    path('instructor/course/<slug:slug>/edit/', views.InstructorCourseUpdateView.as_view(), name='instructor_course_edit'),
    path('instructor/course/<slug:slug>/delete/', views.InstructorCourseDeleteView.as_view(), name='instructor_course_delete'),
    path('instructor/course/<slug:slug>/students/', views.InstructorCourseStudentsView.as_view(), name='instructor_course_students'),
    path('<slug:slug>/enroll/', views.EnrollCourseView.as_view(), name='enroll'),
    path('<slug:slug>/learn/<int:lesson_id>/', views.LessonView.as_view(), name='lesson_view'),
    path('<slug:slug>/preview/<int:lesson_id>/', views.lesson_preview_api, name='lesson_preview_api'),
    path('<slug:slug>/', views.CourseDetailView.as_view(), name='course_detail'),
]
