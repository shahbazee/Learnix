"""
Core views for Learnix platform marketing and informational pages.
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse


def health_check_view(request):
    """Deployment verification healthcheck."""
    return JsonResponse({"status": "ok", "release": "2026.09.28-async-otp-v2"})


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
