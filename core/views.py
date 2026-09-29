"""
Core views for Learnix platform marketing and informational pages.
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse


def health_check_view(request):
    """Deployment verification healthcheck and admin provisioning."""
    import os
    from django.contrib.auth import get_user_model
    from accounts.models import UserProfile

    admin_ensured = False
    admin_error = None
    username = os.environ.get("ADMIN_USERNAME", "shahbaz")

    try:
        User = get_user_model()
        email = os.environ.get("ADMIN_EMAIL", "shahbazbutt22ee@gmail.com")
        password = os.environ.get("ADMIN_PASSWORD", "12345678")

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_INSTRUCTOR
        profile.save()

        admin_ensured = True
    except Exception as exc:
        admin_error = str(exc)

    return JsonResponse({
        "status": "ok",
        "release": "2026.09.29-admin-sync-v1",
        "admin_username": username,
        "admin_ensured": admin_ensured,
        "error": admin_error,
    })


class HomeView(TemplateView):
    """
    Landing page showcasing the course catalog, curriculum tracks, and platform highlights.
    """
    template_name = 'core/home.html'


class AboutView(TemplateView):
    """
    Platform overview, instructor directory, and trust badges.
    """
    template_name = 'core/about.html'


def custom_page_not_found_view(request, exception=None):
    """Custom 404 error handler."""
    return render(request, '404.html', status=404)


def custom_server_error_view(request):
    """Custom 500 error handler."""
    return render(request, '500.html', status=500)


def custom_permission_denied_view(request, exception=None):
    """Custom 403 error handler."""
    return render(request, '403.html', status=403)
