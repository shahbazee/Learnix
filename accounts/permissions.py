from rest_framework import permissions

from .models import UserProfile


class IsInstructor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return UserProfile.objects.filter(
            user=request.user, role="instructor"
        ).exists()


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return UserProfile.objects.filter(
            user=request.user, role="student"
        ).exists()
