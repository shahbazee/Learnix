from celery import shared_task

from .services import reconcile_pending_purchase_emails


@shared_task(queue="emails")
def reconcile_pending_purchase_emails_task():
    return reconcile_pending_purchase_emails()
