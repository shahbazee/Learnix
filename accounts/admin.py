from django.contrib import admin

from .models import EmailLog, FailedTask, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "google_email", "created_at"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__email", "google_email"]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["kind", "recipient", "status", "created_at"]
    list_filter = ["status", "kind"]
    search_fields = ["recipient", "idempotency_key"]


@admin.register(FailedTask)
class FailedTaskAdmin(admin.ModelAdmin):
    list_display = ["task_name", "failed_at", "resolved"]
    list_filter = ["resolved", "task_name"]
