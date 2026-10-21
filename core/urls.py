from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path(
        "admin-dashboard/",
        views.AdminDashboardView.as_view(),
        name="admin_dashboard",
    ),
    path(
        "admin-dashboard/users/",
        views.AdminUserListView.as_view(),
        name="admin_users",
    ),
    path(
        "admin-dashboard/courses/",
        views.AdminCourseListView.as_view(),
        name="admin_courses",
    ),
    path(
        "admin-dashboard/payments/",
        views.AdminPaymentListView.as_view(),
        name="admin_payments",
    ),
]
