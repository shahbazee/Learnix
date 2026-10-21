from django.contrib import admin

from .models import Course, CourseCategory, CourseModule, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = (
        "order_number",
        "title",
        "duration_seconds",
        "is_preview",
        "video_url",
    )
    ordering = ("order_number",)


class CourseModuleInline(admin.StackedInline):
    model = CourseModule
    extra = 1
    ordering = ("order_number",)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "instructor",
        "category",
        "level",
        "price",
        "is_published",
        "is_archived",
        "total_lessons_count",
        "created_at",
    )
    list_filter = ("is_published", "is_archived", "level", "category")
    search_fields = ("title", "short_description", "full_description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CourseModuleInline]
    actions = ["archive_selected_courses"]

    @admin.action(
        description="Archive selected courses (keeps student data)"
    )
    def archive_selected_courses(self, request, queryset):
        updated = queryset.update(is_archived=True, is_published=False)
        self.message_user(
            request, f"{updated} course(s) archived."
        )

    def delete_model(self, request, obj):
        obj.is_archived = True
        obj.is_published = False
        obj.save(update_fields=["is_archived", "is_published"])

    def delete_queryset(self, request, queryset):
        queryset.update(is_archived=True, is_published=False)


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order_number")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "module",
        "order_number",
        "formatted_duration",
        "is_preview",
    )
    list_filter = ("is_preview", "module__course")
    search_fields = ("title", "module__title", "module__course__title")
