from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from ..models import Course


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
