from django.db import migrations


def create_reconcile_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model(
        "django_celery_beat", "CrontabSchedule"
    )
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="17",
        hour="*",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
    )
    PeriodicTask.objects.get_or_create(
        name="reconcile-pending-purchase-emails",
        defaults={
            "task": (
                "payments.tasks."
                "reconcile_pending_purchase_emails_task"
            ),
            "crontab": schedule,
            "enabled": True,
        },
    )


def remove_reconcile_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name="reconcile-pending-purchase-emails"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(
            create_reconcile_schedule,
            reverse_code=remove_reconcile_schedule,
        ),
    ]
