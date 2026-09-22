"""
Custom view decorators for Course access and authorization.
SRS Section 10.2.
"""

from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Course


def enrolled_required(view_func):
    """
    Decorator for views that checks that the user is logged in and enrolled
    in the course corresponding to the 'slug' parameter in the URL.
    Staff members bypass enrollment checks for inspection.
    """
    @wraps(view_func)
    def _wrapped_view(request, slug, *args, **kwargs):
        if not request.user.is_authenticated:
            try:
                messages.info(request, "Please authenticate to access the classroom lessons.")
            except Exception:
                pass
            return redirect(f"/accounts/login/?next={request.path}")

        course = get_object_or_404(Course, slug=slug)

        # Check enrollment
        has_enrollment = (
            hasattr(request.user, 'enrollments') and
            request.user.enrollments.filter(course=course, is_active=True).exists()
        )

        if not has_enrollment and not request.user.is_staff:
            try:
                messages.error(request, "You must be enrolled in this course to access the classroom lessons.")
            except Exception:
                pass
            return redirect("courses:course_detail", slug=slug)

        return view_func(request, slug, *args, **kwargs)

    return _wrapped_view


def instructor_required(view_func):
    """
    Decorator for views that ensures the user is logged in with the Instructor role
    or is a staff member.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            try:
                messages.info(request, "Please authenticate to access this instructor area.")
            except Exception:
                pass
            return redirect(f"/accounts/login/?next={request.path}")

        profile = getattr(request.user, 'profile', None)
        is_instructor = (profile and profile.is_instructor) or request.user.is_staff
        if not is_instructor:
            try:
                messages.error(request, "Access restricted. You need an Instructor account to access this area.")
            except Exception:
                pass
            return redirect("courses:dashboard")

        return view_func(request, *args, **kwargs)

    return _wrapped_view

