from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Enrollment, Lesson, Review


def _recalculate_course_progress(course):
    enrollments = Enrollment.objects.filter(course=course)
    for enrollment in enrollments:
        enrollment.calculate_progress()


@receiver(post_save, sender=Lesson)
def lesson_saved(sender, instance, **kwargs):
    _recalculate_course_progress(instance.module.course)


@receiver(post_delete, sender=Lesson)
def lesson_deleted(sender, instance, **kwargs):
    _recalculate_course_progress(instance.module.course)


def _refresh_course_rating(course):
    stats = course.reviews.aggregate(
        average=Avg("rating"), total=Count("id")
    )
    course.rating = round(stats["average"], 2) if stats["average"] else 0
    course.reviews_count = stats["total"] or 0
    course.save(update_fields=["rating", "reviews_count"])


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    _refresh_course_rating(instance.course)


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    _refresh_course_rating(instance.course)
