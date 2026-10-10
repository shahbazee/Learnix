from django.contrib import admin

from .models import EmailLog, FailedTask


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["kind", "recipient", "status", "created_at"]
    list_filter = ["status", "kind"]
    search_fields = ["recipient", "idempotency_key"]


@admin.register(FailedTask)
class FailedTaskAdmin(admin.ModelAdmin):
    list_display = ["task_name", "failed_at", "resolved"]
    list_filter = ["resolved", "task_name"]