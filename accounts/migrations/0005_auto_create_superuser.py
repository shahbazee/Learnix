import os
from django.db import migrations
from django.contrib.auth.hashers import make_password


def ensure_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('accounts', 'UserProfile')

    username = os.environ.get("ADMIN_USERNAME", "shahbaz")
    email = os.environ.get("ADMIN_EMAIL", "shahbazbutt22ee@gmail.com")
    password = os.environ.get("ADMIN_PASSWORD", "12345678")

    hashed = make_password(password)

    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.create(
            username=username,
            email=email,
            password=hashed,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
    else:
        user.email = email
        user.password = hashed
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

    profile, _ = UserProfile.objects.get_or_create(user_id=user.id)
    profile.role = 'instructor'
    profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_userprofile_role'),
    ]

    operations = [
        migrations.RunPython(ensure_superuser, reverse_code=migrations.RunPython.noop),
    ]
