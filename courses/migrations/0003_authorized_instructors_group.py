from django.db import migrations


def create_authorized_instructors(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type, _ = ContentType.objects.get_or_create(
        app_label="courses", model="course"
    )
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename="publish_course",
        defaults={"name": "Can publish course"},
    )
    group, _ = Group.objects.get_or_create(
        name="Authorized Instructors"
    )
    group.permissions.add(permission)


def remove_authorized_instructors(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Authorized Instructors").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_alter_course_options"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(
            create_authorized_instructors,
            reverse_code=remove_authorized_instructors,
        ),
    ]
