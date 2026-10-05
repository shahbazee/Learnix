import uuid

from django.conf import settings
from django.db import models


class PaymentTransaction(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="payments"
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Human-readable reference e.g. LRN-98214"
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="COMPLETED"
    )
    confirmation_emails_sent = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Ensures purchase confirmation and invoice emails "
            "are dispatched exactly once."
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["order_number"]),
        ]

    def __str__(self):
        return (
            f"Order #{self.order_number} - {self.course.title} "
            f"(${self.amount} {self.currency})"
        )

    @classmethod
    def generate_order_number(cls) -> str:
        return f"LRN-{uuid.uuid4().hex[:6].upper()}"


class Invoice(models.Model):
    transaction = models.OneToOneField(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="invoice"
    )
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="e.g. INV-2026-00481"
    )
    billing_name = models.CharField(max_length=200)
    billing_email = models.EmailField()
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    tax_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00
    )
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="invoices/", null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.billing_name})"

    @classmethod
    def generate_invoice_number(cls) -> str:
        from django.utils import timezone
        year = timezone.now().year
        suffix = uuid.uuid4().hex[:5].upper()
        return f"INV-{year}-{suffix}"
