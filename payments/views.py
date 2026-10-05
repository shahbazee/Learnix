from decimal import Decimal
from io import BytesIO
import logging
import zipfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction as db_transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
import stripe

from courses.models import Course, Enrollment
from .models import Invoice, PaymentTransaction
from .services import (
    generate_invoice_pdf,
    generate_receipt_pdf,
    send_order_confirmation_email,
)

logger = logging.getLogger(__name__)


class CreateCheckoutSessionView(LoginRequiredMixin, View):
    def post(self, request, course_slug):
        course = get_object_or_404(
            Course, slug=course_slug, is_published=True
        )

        if request.user.enrollments.filter(
            course=course, is_active=True
        ).exists():
            messages.info(
                request, f"You are already enrolled in {course.title}."
            )
            return redirect('courses:dashboard')

        if course.is_free:
            with db_transaction.atomic():
                order_num = PaymentTransaction.generate_order_number()
                tx, _ = PaymentTransaction.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={
                        'order_number': order_num,
                        'amount': Decimal('0.00'),
                        'currency': 'USD',
                        'status': 'COMPLETED'
                    }
                )
                enrollment, _ = Enrollment.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={'is_active': True, 'progress_percent': 0.00}
                )
                inv, _ = Invoice.objects.get_or_create(
                    transaction=tx,
                    defaults={
                        'invoice_number': Invoice.generate_invoice_number(),
                        'billing_name': (
                            request.user.get_full_name() or
                            request.user.username
                        ),
                        'billing_email': (
                            request.user.email or
                            f"{request.user.username}@learnix.edu"
                        ),
                        'subtotal': Decimal('0.00'),
                        'tax_amount': Decimal('0.00'),
                        'total_amount': Decimal('0.00')
                    }
                )
            send_order_confirmation_email(request.user, course, tx, inv)
            messages.success(
                request,
                f"Welcome to {course.title}! "
                f"Your complimentary access is active."
            )
            return redirect(
                f"{reverse('payments:payment_success')}?"
                f"order={tx.order_number}"
            )

        order_num = PaymentTransaction.generate_order_number()
        tx, _ = PaymentTransaction.objects.get_or_create(
            user=request.user,
            course=course,
            status='PENDING',
            defaults={
                'order_number': order_num,
                'amount': course.price,
                'currency': settings.STRIPE_CURRENCY.upper(),
            }
        )

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            unit_amount = int(course.price * 100)

            success_url = request.build_absolute_uri(
                f"{reverse('payments:payment_success')}?"
                f"session_id={{CHECKOUT_SESSION_ID}}&order={tx.order_number}"
            )
            cancel_url = request.build_absolute_uri(
                f"{reverse('payments:payment_cancel')}?order={tx.order_number}"
            )

            desc = (
                course.short_description[:200]
                if course.short_description
                else 'Masterclass Architecture Track'
            )
            checkout_session = stripe.checkout.Session.create(
                customer_email=request.user.email or None,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': settings.STRIPE_CURRENCY.lower(),
                            'product_data': {
                                'name': course.title,
                                'description': desc,
                            },
                            'unit_amount': unit_amount,
                        },
                        'quantity': 1,
                    }
                ],
                mode='payment',
                metadata={
                    'user_id': str(request.user.id),
                    'course_id': str(course.id),
                    'order_number': str(tx.order_number),
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )

            tx.stripe_checkout_session_id = checkout_session.id
            tx.save(update_fields=['stripe_checkout_session_id'])

            return redirect(checkout_session.url)

        except stripe.error.AuthenticationError as e:
            logger.error(f"Stripe Authentication Error: {e}")
            messages.error(
                request,
                "Stripe configuration error: A valid Stripe sandbox secret "
                "key (sk_test_...) is required to open Stripe Checkout."
            )
            return redirect('courses:course_detail', slug=course.slug)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API call failed: {e}")
            messages.error(request, f"Stripe Checkout error: {str(e)}")
            return redirect('courses:course_detail', slug=course.slug)

        except Exception as e:
            logger.error(
                f"Unexpected error in CreateCheckoutSessionView: {e}"
            )
            messages.error(
                request,
                "Unable to initiate payment session. Please try again."
            )
            return redirect('courses:course_detail', slug=course.slug)

    def get(self, request, course_slug):
        return self.post(request, course_slug)


class CheckoutModalView(LoginRequiredMixin, View):
    def get(self, request, course_slug):
        return redirect(
            'payments:create_checkout_session', course_slug=course_slug
        )

    def post(self, request, course_slug):
        return redirect(
            'payments:create_checkout_session', course_slug=course_slug
        )


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        order_ref = self.request.GET.get('order')
        session_id = self.request.GET.get('session_id')

        tx = None
        if order_ref:
            qs = PaymentTransaction.objects.filter(order_number=order_ref)
            if not user.is_staff:
                qs = qs.filter(user=user)
            tx = qs.select_related('course', 'invoice').first()
        elif session_id:
            qs = PaymentTransaction.objects.filter(
                stripe_checkout_session_id=session_id
            )
            if not user.is_staff:
                qs = qs.filter(user=user)
            tx = qs.select_related('course', 'invoice').first()
        else:
            tx = PaymentTransaction.objects.filter(
                user=user, status='COMPLETED'
            ).select_related(
                'course', 'invoice'
            ).order_by('-created_at').first()

        is_enrolled = False
        if tx and tx.course:
            is_enrolled = Enrollment.objects.filter(
                user=tx.user,
                course=tx.course,
                is_active=True
            ).exists()

        is_completed = bool(
            tx and tx.status == 'COMPLETED' and is_enrolled
        )

        first_lesson = None
        start_course_url = None
        if tx and tx.course:
            first_module = (
                tx.course.modules.prefetch_related('lessons')
                .order_by('order_number').first()
            )
            if first_module:
                first_lesson = (
                    first_module.lessons.order_by('order_number').first()
                )
            if first_lesson:
                start_course_url = reverse(
                    'courses:lesson_view',
                    kwargs={
                        'slug': tx.course.slug,
                        'lesson_id': first_lesson.id,
                    }
                )
            else:
                start_course_url = reverse('courses:dashboard')

        transaction_id = None
        if tx:
            transaction_id = (
                tx.stripe_payment_intent_id or
                tx.stripe_checkout_session_id or
                tx.order_number
            )

        invoice = None
        if tx and hasattr(tx, 'invoice'):
            invoice = tx.invoice

        context.update({
            'transaction': tx,
            'course': tx.course if tx else None,
            'invoice': invoice,
            'first_lesson': first_lesson,
            'start_course_url': start_course_url,
            'transaction_id': transaction_id,
            'is_completed': is_completed,
            'is_enrolled': is_enrolled,
            'card_brand': None,
            'card_last4': None,
        })
        return context


class PaymentCancelView(TemplateView):
    template_name = 'payments/cancel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_ref = self.request.GET.get('order')
        tx = None
        if order_ref:
            tx = PaymentTransaction.objects.filter(
                order_number=order_ref
            ).select_related('course').first()
        context['transaction'] = tx
        return context


class BillingHubView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/billing_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        transactions = PaymentTransaction.objects.filter(
            user=user
        ).select_related('course', 'invoice').order_by('-created_at')

        for tx in transactions:
            if tx.status == 'COMPLETED' and not hasattr(tx, 'invoice'):
                Invoice.objects.get_or_create(
                    transaction=tx,
                    defaults={
                        'invoice_number': Invoice.generate_invoice_number(),
                        'billing_name': (
                            user.get_full_name() or user.username
                        ),
                        'billing_email': (
                            user.email or f"{user.username}@learnix.edu"
                        ),
                        'subtotal': tx.amount,
                        'tax_amount': Decimal('0.00'),
                        'total_amount': tx.amount
                    }
                )

        transactions = PaymentTransaction.objects.filter(
            user=user
        ).select_related('course', 'invoice').order_by('-created_at')
        completed_txs = [
            tx for tx in transactions if tx.status == 'COMPLETED'
        ]

        total_courses = len(completed_txs)
        lifetime_spend = sum(
            (tx.amount for tx in completed_txs), Decimal('0.00')
        )

        context.update({
            'transactions': transactions,
            'total_courses': total_courses,
            'completed_count': total_courses,
            'lifetime_spend': lifetime_spend,
            'customer_id': f"cus_{user.id:06d}",
            'default_payment_method': "Visa •••• 4242",
        })
        return context


class DownloadInvoicePDFView(LoginRequiredMixin, View):
    def get(self, request, invoice_number):
        invoice = get_object_or_404(
            Invoice.objects.select_related(
                'transaction',
                'transaction__user',
                'transaction__course'
            ),
            invoice_number=invoice_number
        )

        if (
            invoice.transaction.user != request.user and
            not request.user.is_staff
        ):
            raise PermissionDenied("You do not have access to this invoice.")

        pdf_bytes = generate_invoice_pdf(invoice)
        if not pdf_bytes:
            messages.error(
                request, "Could not generate invoice PDF. Please try again."
            )
            return redirect('payments:billing_hub')

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Learnix_Invoice_{invoice.invoice_number}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class DownloadReceiptPDFView(LoginRequiredMixin, View):
    def get(self, request, order_number):
        tx = get_object_or_404(
            PaymentTransaction.objects.select_related(
                'user', 'course', 'invoice'
            ),
            order_number=order_number
        )

        if tx.user != request.user and not request.user.is_staff:
            raise PermissionDenied("You do not have access to this receipt.")

        pdf_bytes = generate_receipt_pdf(tx)
        if not pdf_bytes:
            messages.error(
                request, "Could not generate receipt PDF. Please try again."
            )
            return redirect('payments:billing_hub')

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Learnix_Receipt_{tx.order_number}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ExportAllInvoicesZipView(LoginRequiredMixin, View):
    def get(self, request):
        transactions = PaymentTransaction.objects.filter(
            user=request.user
        ).select_related('course', 'invoice').order_by('-created_at')
        if not transactions.exists():
            messages.info(request, "No transaction records found to export.")
            return redirect('payments:billing_hub')

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for tx in transactions:
                rec_bytes = generate_receipt_pdf(tx)
                if rec_bytes:
                    archive.writestr(
                        f"Receipt_{tx.order_number}.pdf", rec_bytes
                    )

                inv = getattr(tx, 'invoice', None)
                if not inv and tx.status == 'COMPLETED':
                    inv, _ = Invoice.objects.get_or_create(
                        transaction=tx,
                        defaults={
                            'invoice_number': (
                                Invoice.generate_invoice_number()
                            ),
                            'billing_name': (
                                request.user.get_full_name() or
                                request.user.username
                            ),
                            'billing_email': (
                                request.user.email or
                                f"{request.user.username}@learnix.edu"
                            ),
                            'subtotal': tx.amount,
                            'tax_amount': Decimal('0.00'),
                            'total_amount': tx.amount
                        }
                    )
                if inv:
                    inv_bytes = generate_invoice_pdf(inv)
                    if inv_bytes:
                        archive.writestr(
                            f"Invoice_{inv.invoice_number}.pdf", inv_bytes
                        )

        zip_buffer.seek(0)
        response = HttpResponse(
            zip_buffer.getvalue(), content_type='application/zip'
        )
        filename = f"Learnix_Billing_Archive_{request.user.username}.zip"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
