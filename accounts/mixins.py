from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages


class EnrolledCourseRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(
                request,
                "Please authenticate to access the classroom lessons."
            )
            return self.handle_no_permission()

        course_slug = self.kwargs.get("slug")
        if not course_slug:
            return super().dispatch(request, *args, **kwargs)

        if request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)

        has_access = (
            hasattr(request.user, 'enrollments') and
            request.user.enrollments.filter(
                course__slug=course_slug,
                is_active=True
            ).exists()
        )

        if not has_access:
            messages.warning(
                request,
                "You must enroll in this course to access "
                "the classroom lessons."
            )
            return redirect("courses:course_detail", slug=course_slug)

        return super().dispatch(request, *args, **kwargs)


class InstructorRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(
                request,
                "Please authenticate to access the Instructor Studio."
            )
            return self.handle_no_permission()

        profile = getattr(request.user, 'profile', None)
        is_instructor = (
            (profile and profile.is_instructor) or request.user.is_staff
        )

        if not is_instructor:
            messages.error(
                request,
                "Access restricted. You need an Instructor account "
                "to access the Studio."
            )
            return redirect("courses:dashboard")

        return super().dispatch(request, *args, **kwargs)
