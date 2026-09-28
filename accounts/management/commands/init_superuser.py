import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Initializes or updates the default administrator superuser account"

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("ADMIN_USERNAME", "shahbaz")
        email = os.environ.get("ADMIN_EMAIL", "shahbazbutt22ee@gmail.com")
        password = os.environ.get("ADMIN_PASSWORD", "12345678")

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_INSTRUCTOR
        profile.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} superuser '{username}' ({email}) successfully."))
