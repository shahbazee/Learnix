from django.conf import settings
from django.contrib import admin, messages

import stripe

from core.emails import (
    send_course_purchase_success_email,
    send_payment_receipt_invoice_email,
)

from .models import Invoice, PaymentTransaction
from .services import generate_invoice_pdf


@admin.action(
    description="Resend Invoice & Confirmation Emails to Customer via Brevo"
)
def resend_purchase_emails_action(modeladmin, request, queryset):
    sent_count = 0
    fail_count = 0
    for tx in queryset:
        try:
            inv = getattr(tx, "invoice", None)
            if not inv and tx.status == "COMPLETED":
                inv, _ = Invoice.objects.get_or_create(
                    transaction=tx,
                    defaults={
                        "invoice_number": Invoice.generate_invoice_number(),
                        "billing_name": (
                            tx.user.get_full_name() or tx.user.username
                        ),
                        "billing_email": (
                            tx.user.email or f"{tx.user.username}@learnix.edu"
                        ),
                        "subtotal": tx.amount,
                        "tax_amount": 0.00,
                        "total_amount": tx.amount,
                    },
                )
            pdf_bytes = generate_invoice_pdf(inv) if inv else None
            ok1 = send_course_purchase_success_email(
                tx.user, tx.course, tx, invoice=inv
            )
            ok2 = (
                send_payment_receipt_invoice_email(
                    tx.user, tx.course, tx, inv, pdf_bytes=pdf_bytes
                )
                if inv
                else False
            )
            if ok1 or ok2:
                tx.confirmation_emails_sent = True
                tx.save(update_fields=["confirmation_emails_sent"])
                sent_count += 1
            else:
                fail_count += 1
        except Exception:
            fail_count += 1

    if sent_count:
        messages.success(
            request,
            f"Successfully dispatched invoice/confirmation emails for "
            f"{sent_count} transaction(s).",
        )
    if fail_count:
        messages.error(
            request,
            f"Failed to dispatch emails for {fail_count} transaction(s). "
            f"Check server logs for details.",
        )


@admin.action(
    description="Refund selected completed payments via Stripe"
)
def refund_payments_action(modeladmin, request, queryset):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    refunded_count = 0
    skipped_count = 0
    fail_count = 0
    for tx in queryset:
        if tx.status != "COMPLETED" or not tx.stripe_payment_intent_id:
            skipped_count += 1
            continue
        try:
            stripe.Refund.create(
                payment_intent=tx.stripe_payment_intent_id
            )
            refunded_count += 1
        except Exception:
            fail_count += 1

    if refunded_count:
        messages.success(
            request,
            f"Refund requested at Stripe for {refunded_count} "
            f"transaction(s). Status changes to REFUNDED when "
            f"Stripe confirms via webhook.",
        )
    if skipped_count:
        messages.warning(
            request,
            f"Skipped {skipped_count} transaction(s) — only "
            f"COMPLETED payments with a payment intent can be "
            f"refunded.",
        )
    if fail_count:
        messages.error(
            request,
            f"Stripe refused refunds for {fail_count} "
            f"transaction(s). Check the Stripe dashboard.",
        )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "course",
        "amount",
        "currency",
        "status",
        "confirmation_emails_sent",
        "created_at",
    )
    list_filter = ("status", "confirmation_emails_sent", "created_at")
    search_fields = (
        "order_number",
        "user__username",
        "user__email",
        "course__title",
        "stripe_checkout_session_id",
    )
    actions = [resend_purchase_emails_action, refund_payments_action]
    readonly_fields = ("created_at",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "billing_name",
        "billing_email",
        "total_amount",
        "issued_at",
    )
    search_fields = (
        "invoice_number",
        "billing_name",
        "billing_email",
        "transaction__order_number",
    )
    readonly_fields = ("issued_at",)
