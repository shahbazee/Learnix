from django.core.management.base import BaseCommand

from core.emails import (
    send_course_purchase_success_email,
    send_payment_receipt_invoice_email,
)
from payments.models import Invoice, PaymentTransaction
from payments.services import generate_invoice_pdf


class Command(BaseCommand):
    help = (
        "Dispatches missing invoice and purchase confirmation "
        "emails for completed orders via Brevo"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--order',
            type=str,
            help='Specific order number to resend e.g. LRN-12345'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Resend to all completed orders without confirmation'
        )

    def handle(self, *args, **options):
        order_ref = options.get('order')
        resend_all = options.get('all')

        if order_ref:
            qs = PaymentTransaction.objects.filter(order_number=order_ref)
        elif resend_all:
            qs = PaymentTransaction.objects.filter(
                status='COMPLETED', confirmation_emails_sent=False
            )
        else:
            self.stdout.write(
                self.style.WARNING("Please specify --order <order> or --all")
            )
            return

        if not qs.exists():
            self.stdout.write(
                self.style.NOTICE("No matching transactions found.")
            )
            return

        for tx in qs:
            self.stdout.write(
                f"Processing order #{tx.order_number} "
                f"for user {tx.user.email}..."
            )
            inv = getattr(tx, 'invoice', None)
            if not inv and tx.status == 'COMPLETED':
                inv, _ = Invoice.objects.get_or_create(
                    transaction=tx,
                    defaults={
                        'invoice_number': Invoice.generate_invoice_number(),
                        'billing_name': (
                            tx.user.get_full_name() or tx.user.username
                        ),
                        'billing_email': (
                            tx.user.email or f"{tx.user.username}@learnix.edu"
                        ),
                        'subtotal': tx.amount,
                        'tax_amount': 0.00,
                        'total_amount': tx.amount
                    }
                )

            pdf_bytes = generate_invoice_pdf(inv) if inv else None
            ok1 = send_course_purchase_success_email(
                tx.user, tx.course, tx, invoice=inv
            )
            ok2 = (
                send_payment_receipt_invoice_email(
                    tx.user, tx.course, tx, inv, pdf_bytes=pdf_bytes
                )
                if inv else False
            )

            if ok2 or ok1:
                tx.confirmation_emails_sent = True
                tx.save(update_fields=['confirmation_emails_sent'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [OK] Successfully sent invoice to {tx.user.email} "
                        f"for order #{tx.order_number}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"  [FAIL] Could not send email for order "
                        f"#{tx.order_number}"
                    )
                )
