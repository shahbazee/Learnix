"""
Django Admin configuration for courses, modules, lessons, and categories.
"""

from django.contrib import admin
from .models import CourseCategory, Course, CourseModule, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('order_number', 'title', 'duration_seconds', 'is_preview', 'video_url')
    ordering = ('order_number',)


class CourseModuleInline(admin.StackedInline):
    model = CourseModule
    extra = 1
    ordering = ('order_number',)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'level', 'price', 'is_published', 'total_lessons_count', 'created_at')
    list_filter = ('is_published', 'level', 'category')
    search_fields = ('title', 'short_description', 'full_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [CourseModuleInline]


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order_number')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order_number', 'formatted_duration', 'is_preview')
    list_filter = ('is_preview', 'module__course')
    search_fields = ('title', 'module__title', 'module__course__title')
