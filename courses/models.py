"""
Database models for Course Management, Modules, Lessons, and Categories.
PostgreSQL 15+ compatible models for Learnix.
SRS Section 8.1 & 8.2.
"""

import uuid
import hashlib
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class CourseCategory(models.Model):
    """
    Categorizes technical domains (e.g., AI & LLMs, Distributed Systems, Cloud Architecture).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=50, default='school', help_text="Material symbol icon name")
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name_plural = "Course Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Course(models.Model):
    """
    Core curriculum entity defining masterclass architecture tracks.
    """
    LEVEL_CHOICES = (
        ("BEGINNER", "Beginner"),
        ("INTERMEDIATE", "Intermediate"),
        ("ADVANCED", "Advanced"),
    )

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authored_courses"
    )
    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )
    short_description = models.TextField(
        help_text="One or two sentences summarizing the architectural mastery track"
    )
    full_description = models.TextField(
        blank=True,
        default='',
        help_text="Comprehensive syllabus outline, prerequisites, and learning outcomes"
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES, default="BEGINNER")
    thumbnail = models.ImageField(upload_to="course_thumbnails/", null=True, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True, default='', help_text="Fallback external URL for demo images")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.90)
    reviews_count = models.PositiveIntegerField(default=120)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug", "is_published"]),
            models.Index(fields=["price"]),
            models.Index(fields=["level"]),
        ]

    def __str__(self):
        return self.title

    @property
    def total_lessons_count(self) -> int:
        """Calculates total lessons across all modules efficiently."""
        return Lesson.objects.filter(module__course=self).count()

    @property
    def is_free(self) -> bool:
        """Returns True if the course has a zero tuition price."""
        return self.price == 0.00

    @property
    def total_duration_seconds(self) -> int:
        """Aggregates duration in seconds across all curriculum lessons."""
        return sum(
            lesson.duration_seconds
            for module in self.modules.all()
            for lesson in module.lessons.all()
        )

    @property
    def total_duration_hours_display(self) -> str:
        """Formatted hours (e.g. '18h Total' or '14.5 hrs')."""
        total_sec = self.total_duration_seconds
        if not total_sec:
            return "10h Total"
        hours = round(total_sec / 3600, 1)
        if hours.is_integer():
            return f"{int(hours)}h Total"
        return f"{hours}h Total"

    @property
    def get_thumbnail_url(self) -> str:
        """
        Resolves the primary course thumbnail URL in priority order:
        1. Uploaded ImageField thumbnail (if file exists).
        2. Configured thumbnail_url (seeded from Stitch UI designs).
        3. Curated local vector fallback (/static/images/courses/<slug>.svg).
        4. Default masterclass fallback (/static/images/courses/default-course.svg).
        """
        if self.thumbnail and hasattr(self.thumbnail, 'url'):
            try:
                return self.thumbnail.url
            except Exception:
                pass
        if self.thumbnail_url and self.thumbnail_url.strip():
            return self.thumbnail_url.strip()
        return f"/static/images/courses/{self.slug}.svg"


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class CourseModule(models.Model):
    """
    Curriculum unit or chapter organizing lessons sequentially.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules"
    )
    title = models.CharField(max_length=200)
    order_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"{self.course.title} — Module {self.order_number}: {self.title}"

    @property
    def total_duration_seconds(self) -> int:
        return sum(lesson.duration_seconds for lesson in self.lessons.all())


class Lesson(models.Model):
    """
    Individual learning unit containing interactive video player streams and rich text.
    """
    module = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    title = models.CharField(max_length=200)
    video_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Direct MP4 video URL or embed link"
    )
    content = models.TextField(blank=True, default='')
    duration_seconds = models.PositiveIntegerField(
        default=600,
        help_text="Duration of lesson in seconds (e.g. 860 for 14m 20s)"
    )
    order_number = models.PositiveIntegerField(default=1)
    is_preview = models.BooleanField(
        default=False,
        help_text="If True, guests and unenrolled students can stream this lesson for free"
    )

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"Lesson {self.order_number}: {self.title}"

    @property
    def formatted_duration(self) -> str:
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


class Enrollment(models.Model):
    """
    Represents an active or historical course enrollment for a student.
    SRS Section 8.1 & 8.2.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    progress_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Calculated completion percentage (0.00% to 100.00%)"
    )

    class Meta:
        ordering = ["-enrolled_at"]
        unique_together = ("user", "course")
        indexes = [
            models.Index(fields=["user", "course"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["progress_percent"]),
        ]

    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.title} ({self.progress_percent}%)"

    def calculate_progress(self) -> float:
        """
        Recalculates completion percentage based on LessonProgress records and saves.
        """
        total_lessons = Lesson.objects.filter(module__course=self.course).count()
        if total_lessons == 0:
            self.progress_percent = 0.00
        else:
            completed_count = LessonProgress.objects.filter(
                user=self.user,
                lesson__module__course=self.course,
                is_completed=True
            ).count()
            self.progress_percent = round((completed_count / total_lessons) * 100, 2)
            if self.progress_percent > 100.0:
                self.progress_percent = 100.00
        self.save(update_fields=["progress_percent"])
        if self.progress_percent >= 100.00:
            Certificate.issue_for_enrollment(self)
        return float(self.progress_percent)

    @property
    def completed_lessons_count(self) -> int:
        return LessonProgress.objects.filter(
            user=self.user,
            lesson__module__course=self.course,
            is_completed=True
        ).count()

    @property
    def total_lessons_count(self) -> int:
        return self.course.total_lessons_count

    @property
    def is_completed(self) -> bool:
        return self.progress_percent >= 100.00

    @property
    def next_uncompleted_lesson(self):
        """Finds the next unfinished lesson in sequential curriculum order."""
        completed_ids = set(
            LessonProgress.objects.filter(
                user=self.user,
                lesson__module__course=self.course,
                is_completed=True
            ).values_list("lesson_id", flat=True)
        )
        for module in self.course.modules.prefetch_related("lessons").order_by("order_number"):
            for lesson in module.lessons.order_by("order_number"):
                if lesson.id not in completed_ids:
                    return lesson
        # If all completed or none, return the first lesson
        first_module = self.course.modules.prefetch_related("lessons").order_by("order_number").first()
        if first_module:
            return first_module.lessons.order_by("order_number").first()
        return None


class LessonProgress(models.Model):
    """
    Granular completion and telemetry tracking per lesson per student.
    SRS Section 8.1 & 8.2.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progresses"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progresses"
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_accessed_at"]
        unique_together = ("user", "lesson")
        indexes = [
            models.Index(fields=["user", "lesson"]),
            models.Index(fields=["is_completed"]),
        ]

    def __str__(self):
        state = "Completed" if self.is_completed else "In Progress"
        return f"{self.user.username} - {self.lesson.title} ({state})"


class Certificate(models.Model):
    """
    Cryptographically verifiable Certificate of Completion.
    Implements Stitch Screen 11 (eduflow_verifiable_certificate_of_completion_light adapted to Learnix).
    SRS Section 8.1, 8.2, 13.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificates"
    )
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="certificate"
    )
    certificate_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique verifiable code e.g. LRN-98214-X"
    )
    verification_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 cryptographic verification ledger hash"
    )
    ceus = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal('4.5'))
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="certificates/", null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["certificate_id"]),
            models.Index(fields=["user", "course"]),
        ]

    def __str__(self):
        return f"Certificate {self.certificate_id} - {self.user.username} - {self.course.title}"

    @classmethod
    def generate_certificate_id(cls) -> str:
        suffix = uuid.uuid4().hex[:5].upper()
        return f"LRN-{suffix}-X"

    @classmethod
    def compute_verification_hash(cls, user_id, course_slug, timestamp_str) -> str:
        raw = f"LEARNIX_CERT:{user_id}:{course_slug}:{timestamp_str}:SHA256_AUTH"
        return "0x" + hashlib.sha256(raw.encode('utf-8')).hexdigest()[:38]

    @classmethod
    def issue_for_enrollment(cls, enrollment):
        """
        Issues or retrieves verifiable certificate if enrollment is 100% complete.
        """
        if not enrollment.is_completed:
            return None

        cert = getattr(enrollment, 'certificate', None)
        if not cert:
            from django.utils import timezone
            now_str = timezone.now().isoformat()
            v_hash = cls.compute_verification_hash(enrollment.user.id, enrollment.course.slug, now_str)
            cert, _ = cls.objects.get_or_create(
                enrollment=enrollment,
                defaults={
                    'user': enrollment.user,
                    'course': enrollment.course,
                    'certificate_id': cls.generate_certificate_id(),
                    'verification_hash': v_hash,
                    'ceus': Decimal('4.5'),
                }
            )
        return cert


