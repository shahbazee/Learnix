from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ( 
    EmailLog, FailedTask, 
    User, UserProfile, 
    RoleChangeRequest,
    InstructorRegistrationRequest,
    )
from django.utils import timezone


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


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


@admin.register(RoleChangeRequest)
class RoleChangeRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "from_role", "to_role", "status", "created_at"]
    list_filter = ["status"]
    actions = ["approve_requests", "reject_requests"]

    @admin.action(description="Approve selected requests")
    def approve_requests(self, request, queryset):
        pending = queryset.filter(status=RoleChangeRequest.Status.PENDING)
        approved = 0
        for role_request in pending:
            if role_request.user == request.user:
                continue
            role_request.status = RoleChangeRequest.Status.APPROVED
            role_request.reviewed_by = request.user
            role_request.reviewed_at = timezone.now()
            role_request.save()
            profile = role_request.user.profile
            profile.role = role_request.to_role
            profile.save()
            approved += 1
        self.message_user(request, f"{approved} requests approved.")


    @admin.action(description="Reject selected requests")
    def reject_requests(self, request, queryset):
        pending = queryset.filter(status=RoleChangeRequest.Status.PENDING)
        rejected = 0
        for role_request in pending:
            if role_request.user == request.user:
                continue
            role_request.status = RoleChangeRequest.Status.REJECTED
            role_request.reviewed_by = request.user
            role_request.reviewed_at = timezone.now()
            role_request.save()
            rejected += 1
        self.message_user(request, f"{rejected} requests rejected.")


@admin.register(InstructorRegistrationRequest)
class InstructorRegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "expertise", "status", "created_at"]
    list_filter = ["status"]
    actions = ["approve_requests", "reject_requests"]

    @admin.action(description="Approve selected requests")
    def approve_requests(self, request, queryset):
        pending = queryset.filter(
            status=InstructorRegistrationRequest.Status.PENDING
        )
        approved = 0
        for reg_request in pending:
            if reg_request.user == request.user:
                continue
            reg_request.status = (
                InstructorRegistrationRequest.Status.APPROVED
            )
            reg_request.reviewed_by = request.user
            reg_request.reviewed_at = timezone.now()
            reg_request.save()
            profile = reg_request.user.profile
            profile.role = UserProfile.ROLE_INSTRUCTOR
            profile.save()
            approved += 1
        self.message_user(request, f"{approved} requests approved.")

    @admin.action(description="Reject selected requests")
    def reject_requests(self, request, queryset):
        pending = queryset.filter(
            status=InstructorRegistrationRequest.Status.PENDING
        )
        rejected = 0
        for reg_request in pending:
            if reg_request.user == request.user:
                continue
            reg_request.status = (
                InstructorRegistrationRequest.Status.REJECTED
            )
            reg_request.reviewed_by = request.user
            reg_request.reviewed_at = timezone.now()
            reg_request.save()
            rejected += 1
        self.message_user(request, f"{rejected} requests rejected.")