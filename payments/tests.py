"""
Automated unit and integration test suite for Learnix Payments & Email Subsystem.
Validates Stripe Checkout in Test/Sandbox Mode, Webhook lifecycle, and centralized email sender.
"""

import json
import zipfile
import stripe
from unittest.mock import patch, MagicMock
from io import BytesIO
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.conf import settings

from courses.models import CourseCategory, Course, CourseModule, Lesson, Enrollment
from payments.models import PaymentTransaction, Invoice
from payments.services import (
    send_order_confirmation_email,
    send_registration_welcome_email,
    send_password_reset_otp_email
)

User = get_user_model()


class StripePaymentsTestCase(TestCase):
    """
    Test suite for Stripe sandbox checkout, modal simulation, webhooks, and email dispatchers.
    """
    def setUp(self):
        self.client = Client()

        # Instructor
        self.instructor = User.objects.create_user(
            username='instructor_elena',
            email='elena@learnix.com',
            password='Password123!'
        )

        # Student
        self.student = User.objects.create_user(
            username='student_mark',
            first_name='Mark',
            email='mark@example.com',
            password='Password123!'
        )

        # Category
        self.category = CourseCategory.objects.create(
            name='AI & Multi-Agent Swarms',
            slug='ai-swarms',
            icon='psychology'
        )

        # Paid Course
        self.course_paid = Course.objects.create(
            title='Full-Stack Django 5 & Multi-Agent AI',
            slug='full-stack-django-5-multi-agent-ai',
            category=self.category,
            instructor=self.instructor,
            level='INTERMEDIATE',
            price=Decimal('89.00'),
            short_description='Autonomous agent workflows and websockets.',
            is_published=True
        )

        # Free Course
        self.course_free = Course.objects.create(
            title='Intro to Vector Databases',
            slug='intro-vector-databases',
            category=self.category,
            instructor=self.instructor,
            level='BEGINNER',
            price=Decimal('0.00'),
            short_description='Foundational vector search concepts.',
            is_published=True
        )

        # Module & Lessons
        self.module = CourseModule.objects.create(
            course=self.course_paid,
            title='Module 1: Foundations',
            order_number=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson 1.1: Architecture',
            duration_seconds=600,
            order_number=1
        )

    def test_centralized_email_sender_configuration(self):
        """Verifies that all emails are strictly dispatched from shahbazbutt22ee@gmail.com."""
        mail.outbox = []

        # 1. Order confirmation email
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-TEST01',
            amount=self.course_paid.price,
            status='COMPLETED'
        )
        send_order_confirmation_email(self.student, self.course_paid, tx)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('shahbazbutt22ee@gmail.com', mail.outbox[0].from_email)
        self.assertTrue('Order Confirmed' in mail.outbox[0].subject or 'Payment Confirmed' in mail.outbox[0].subject)

        # 2. Registration welcome email
        send_registration_welcome_email(self.student)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('shahbazbutt22ee@gmail.com', mail.outbox[1].from_email)
        self.assertIn('Welcome to Learnix', mail.outbox[1].subject)

        # 3. Password reset OTP email
        send_password_reset_otp_email(self.student, '489201')
        self.assertEqual(len(mail.outbox), 3)
        self.assertIn('shahbazbutt22ee@gmail.com', mail.outbox[2].from_email)
        self.assertIn('Password Reset Code', mail.outbox[2].subject)

    def test_create_checkout_session_free_course(self):
        """Free course enrolls student immediately, generates transaction & invoice, and sends email."""
        mail.outbox = []
        self.client.force_login(self.student)

        url = reverse('payments:create_checkout_session', kwargs={'course_slug': self.course_free.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/payments/success/', response.url)

        # Verify DB
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course_free, is_active=True).exists())
        tx = PaymentTransaction.objects.get(user=self.student, course=self.course_free)
        self.assertEqual(tx.status, 'COMPLETED')
        self.assertTrue(hasattr(tx, 'invoice'))

        # Verify Email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('shahbazbutt22ee@gmail.com', mail.outbox[0].from_email)

    def test_create_checkout_session_already_enrolled(self):
        """Already enrolled students are redirected to the dashboard without duplicate charges."""
        Enrollment.objects.create(user=self.student, course=self.course_paid, is_active=True)
        self.client.force_login(self.student)

        url = reverse('payments:create_checkout_session', kwargs={'course_slug': self.course_paid.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('courses:dashboard'))

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_hosted_stripe_redirect(self, mock_stripe_create):
        """Verifies paid course checkout opens official Stripe hosted Checkout page with cards only."""
        mock_session = MagicMock()
        mock_session.id = 'cs_test_mock_session_abc123'
        mock_session.url = 'https://checkout.stripe.com/c/pay/cs_test_mock_session_abc123'
        mock_stripe_create.return_value = mock_session

        self.client.force_login(self.student)
        url = reverse('payments:create_checkout_session', kwargs={'course_slug': self.course_paid.slug})
        response = self.client.post(url)

        # Asserts redirect to Stripe's hosted URL
        self.assertIn(response.status_code, [302, 303])
        self.assertEqual(response.url, 'https://checkout.stripe.com/c/pay/cs_test_mock_session_abc123')

        # Verifies Stripe checkout was invoked with card only (disabling Apple/Google Pay) and correct data
        mock_stripe_create.assert_called_once()
        _, kwargs = mock_stripe_create.call_args
        self.assertEqual(kwargs['payment_method_types'], ['card'])
        self.assertEqual(kwargs['customer_email'], self.student.email)
        self.assertEqual(kwargs['mode'], 'payment')
        self.assertEqual(kwargs['line_items'][0]['price_data']['unit_amount'], 8900)
        self.assertIn('/payments/success/', kwargs['success_url'])
        self.assertIn('/payments/cancel/', kwargs['cancel_url'])
        self.assertEqual(kwargs['metadata']['user_id'], str(self.student.id))
        self.assertEqual(kwargs['metadata']['course_id'], str(self.course_paid.id))

        # Check transaction in DB
        tx = PaymentTransaction.objects.get(user=self.student, course=self.course_paid)
        self.assertEqual(tx.status, 'PENDING')
        self.assertEqual(tx.stripe_checkout_session_id, 'cs_test_mock_session_abc123')

    def test_checkout_modal_redirects_to_create_session(self):
        """Verifies legacy checkout modal view redirects to create_checkout_session, removing on-site form."""
        self.client.force_login(self.student)
        url = reverse('payments:checkout_modal', kwargs={'course_slug': self.course_paid.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('payments:create_checkout_session', kwargs={'course_slug': self.course_paid.slug})
        self.assertEqual(response.url, expected_url)

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_auth_error_handling(self, mock_stripe_create):
        """Verifies that an invalid Stripe API key displays a friendly error without on-site forms or crashing."""
        mock_stripe_create.side_effect = stripe.error.AuthenticationError("Invalid API Key provided")

        self.client.force_login(self.student)
        url = reverse('payments:create_checkout_session', kwargs={'course_slug': self.course_paid.slug})
        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('courses:course_detail', kwargs={'slug': self.course_paid.slug}))
        self.assertContains(response, 'Stripe configuration error')

    def test_payment_success_view(self):
        """Payment success view renders Screen 8 with celebratory tiles and onboarding guide."""
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-CONFIRM99',
            amount=self.course_paid.price,
            status='COMPLETED'
        )
        Invoice.objects.create(
            transaction=tx,
            invoice_number='INV-2026-99',
            billing_name='Mark Jenkins',
            billing_email='mark@example.com',
            subtotal=tx.amount,
            total_amount=tx.amount
        )
        self.client.force_login(self.student)

        url = f"{reverse('payments:payment_success')}?order={tx.order_number}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enrollment &amp; Transaction Confirmed')
        self.assertContains(response, 'PAID IN FULL')
        self.assertContains(response, 'Launch Course Classroom')
        self.assertContains(response, 'Verify Discord Access')
        self.assertContains(response, 'Configure CLI Sandbox')
        # Strict branding
        self.assertNotContains(response, 'EduFlow')

    def test_payment_cancel_view(self):
        """Payment cancel view renders aborted checkout notice with retry action."""
        url = reverse('payments:payment_cancel')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Checkout Not Completed')

    def test_stripe_webhook_listener_fulfillment(self):
        """Simulates Stripe checkout.session.completed webhook fulfilling enrollment atomically."""
        mail.outbox = []

        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_mock_webhook_123",
                    "payment_intent": "pi_test_intent_456",
                    "metadata": {
                        "user_id": str(self.student.id),
                        "course_id": str(self.course_paid.id),
                        "order_number": "LRN-WHSEC01",
                    }
                }
            }
        }

        url = reverse('payments:stripe_webhook')
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # Verify DB updates
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course_paid, is_active=True).exists())
        tx = PaymentTransaction.objects.get(order_number='LRN-WHSEC01')
        self.assertEqual(tx.status, 'COMPLETED')
        self.assertEqual(tx.stripe_payment_intent_id, 'pi_test_intent_456')

        # Verify 3 fulfillment emails dispatched from shahbazbutt22ee@gmail.com (Purchase, Invoice, Enrollment)
        self.assertEqual(len(mail.outbox), 3)
        for msg in mail.outbox:
            self.assertIn('shahbazbutt22ee@gmail.com', msg.from_email)

    def test_billing_hub_view_authenticated(self):
        """Billing Hub view renders metrics, transaction table, and documents correctly."""
        # Create completed transaction and invoice
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-BILL01',
            amount=self.course_paid.price,
            currency='USD',
            status='COMPLETED'
        )
        Invoice.objects.create(
            transaction=tx,
            invoice_number='INV-2026-TEST01',
            billing_name='Mark Spencer',
            billing_email='mark@example.com',
            subtotal=tx.amount,
            total_amount=tx.amount
        )

        self.client.force_login(self.student)
        url = reverse('payments:billing_hub')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Assert visual elements and contents
        self.assertContains(response, 'Billing &amp; Payment History')
        self.assertContains(response, 'Recent Academic Invoices')
        self.assertContains(response, 'Total Courses Purchased')
        self.assertContains(response, 'Default Payment Method')
        self.assertContains(response, 'Lifetime Investment')
        self.assertContains(response, '1-Click Receipts')
        self.assertContains(response, 'INV-2026-TEST01')
        self.assertContains(response, 'LRN-BILL01')
        self.assertContains(response, '[PDF] Tax Invoice')
        self.assertContains(response, '[PDF] Stripe Receipt')
        self.assertContains(response, 'Export All (ZIP)')
        # Strict branding check
        self.assertNotContains(response, 'EduFlow')

    def test_billing_hub_view_requires_login(self):
        """Unauthenticated user accessing billing hub is redirected to login."""
        url = reverse('payments:billing_hub')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_download_invoice_pdf_view(self):
        """Streams authentic, valid PDF tax invoice with proper HTTP headers."""
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-INVTEST',
            amount=self.course_paid.price,
            currency='USD',
            status='COMPLETED'
        )
        inv = Invoice.objects.create(
            transaction=tx,
            invoice_number='INV-2026-PDF01',
            billing_name='Mark Spencer',
            billing_email='mark@example.com',
            subtotal=tx.amount,
            total_amount=tx.amount
        )

        self.client.force_login(self.student)
        url = reverse('payments:download_invoice', kwargs={'invoice_number': inv.invoice_number})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('Learnix_Invoice_INV-2026-PDF01.pdf', response['Content-Disposition'])

        # Verify PDF header magic bytes
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreater(len(response.content), 1000)

    def test_download_invoice_pdf_security_permission(self):
        """A user cannot download an invoice belonging to a different user."""
        other_user = User.objects.create_user(
            username='student_stranger',
            email='stranger@example.com',
            password='Password123!'
        )
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-SEC01',
            amount=self.course_paid.price,
            currency='USD',
            status='COMPLETED'
        )
        inv = Invoice.objects.create(
            transaction=tx,
            invoice_number='INV-2026-SEC01',
            billing_name='Mark Spencer',
            billing_email='mark@example.com',
            subtotal=tx.amount,
            total_amount=tx.amount
        )

        # Log in as other user
        self.client.force_login(other_user)
        url = reverse('payments:download_invoice', kwargs={'invoice_number': inv.invoice_number})
        response = self.client.get(url)
        # Should be forbidden 403
        self.assertEqual(response.status_code, 403)

    def test_download_receipt_pdf_view(self):
        """Streams authentic, valid PDF payment receipt with proper HTTP headers."""
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-RECTEST',
            amount=self.course_paid.price,
            currency='USD',
            status='COMPLETED'
        )

        self.client.force_login(self.student)
        url = reverse('payments:download_receipt', kwargs={'order_number': tx.order_number})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('Learnix_Receipt_LRN-RECTEST.pdf', response['Content-Disposition'])

        # Verify PDF header magic bytes
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreater(len(response.content), 1000)

    def test_export_all_invoices_zip(self):
        """Exports all student invoices and receipts into a valid .ZIP bundle."""
        tx1 = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-ZIP01',
            amount=self.course_paid.price,
            currency='USD',
            status='COMPLETED'
        )
        Invoice.objects.create(
            transaction=tx1,
            invoice_number='INV-2026-ZIP01',
            billing_name='Mark Spencer',
            billing_email='mark@example.com',
            subtotal=tx1.amount,
            total_amount=tx1.amount
        )

        self.client.force_login(self.student)
        url = reverse('payments:export_all_invoices')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('Learnix_Billing_Archive_student_mark.zip', response['Content-Disposition'])

        # Unpack zip and verify contents
        zip_file = zipfile.ZipFile(BytesIO(response.content))
        names = zip_file.namelist()
        self.assertIn('Receipt_LRN-ZIP01.pdf', names)
        self.assertIn('Invoice_INV-2026-ZIP01.pdf', names)

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_signature_verification_success(self, mock_construct_event):
        """Verifies that signed webhook payloads are parsed via stripe.Webhook.construct_event."""
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_signed_123",
                    "payment_intent": "pi_test_signed_456",
                    "metadata": {
                        "user_id": str(self.student.id),
                        "course_id": str(self.course_paid.id),
                        "order_number": "LRN-SIGNED01",
                    }
                }
            }
        }

        url = reverse('payments:stripe_webhook')
        raw_payload = b'{"type": "checkout.session.completed"}'
        response = self.client.post(
            url,
            data=raw_payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=1600000000,v1=valid_mock_signature'
        )
        self.assertEqual(response.status_code, 200)
        mock_construct_event.assert_called_once()
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course_paid, is_active=True).exists())

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_signature_verification_failure(self, mock_construct_event):
        """Verifies that an invalid signature rejects the webhook with HTTP 400 Bad Request."""
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError(
            "Signature verification failed", "bad_sig_header"
        )

        url = reverse('payments:stripe_webhook')
        raw_payload = b'{"type": "checkout.session.completed"}'
        response = self.client.post(
            url,
            data=raw_payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=1600000000,v1=invalid_signature'
        )
        self.assertEqual(response.status_code, 400)
        # Enrollment was not granted
        self.assertFalse(Enrollment.objects.filter(user=self.student, course=self.course_paid).exists())

    def test_stripe_webhook_idempotency_prevents_duplicate_emails_and_invoices(self):
        """Receiving duplicate webhook events does not duplicate enrollments, invoices, or emails."""
        mail.outbox = []

        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_idempotent_123",
                    "payment_intent": "pi_test_idempotent_456",
                    "metadata": {
                        "user_id": str(self.student.id),
                        "course_id": str(self.course_paid.id),
                        "order_number": "LRN-IDEMPOTENT",
                    }
                }
            }
        }
        url = reverse('payments:stripe_webhook')

        # First delivery: exactly 3 emails dispatched (Purchase, Invoice, Enrollment)
        res1 = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.course_paid).count(), 1)
        self.assertEqual(Invoice.objects.filter(transaction__order_number='LRN-IDEMPOTENT').count(), 1)

        # Duplicate/retry delivery: no additional emails, enrollments, or invoices created
        res2 = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        # Still exactly 3 emails dispatched (zero duplicate emails on retry)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.course_paid).count(), 1)
        self.assertEqual(Invoice.objects.filter(transaction__order_number='LRN-IDEMPOTENT').count(), 1)

    def test_stripe_webhook_trigger_dummy_metadata_acknowledged(self):
        """Simulates 'stripe trigger checkout.session.completed' with no metadata; returns 200 gracefully."""
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_trigger_dummy",
                    "metadata": {}
                }
            }
        }
        url = reverse('payments:stripe_webhook')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_stripe_course_purchase_emails_content_and_sender(self):
        """
        Validates that paid course purchase triggers both purchase confirmation
        and invoice/receipt emails to the customer's registered email with sender
        shahbazbutt22ee@gmail.com and all mandatory details.
        """
        mail.outbox = []

        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_purchase_full_details",
                    "payment_intent": "pi_test_stripe_ref_789",
                    "customer_details": {
                        "name": "Mark Jenkins",
                        "email": self.student.email,
                    },
                    "metadata": {
                        "user_id": str(self.student.id),
                        "course_id": str(self.course_paid.id),
                        "order_number": "LRN-DETAILS99",
                    }
                }
            }
        }

        url = reverse('payments:stripe_webhook')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # 3 emails sent: Purchase Confirmation, Tax Invoice, Enrollment
        self.assertEqual(len(mail.outbox), 3)

        # 1. Purchase confirmation email
        purchase_email = next(m for m in mail.outbox if 'Payment Confirmed' in m.subject)
        self.assertEqual(purchase_email.from_email, 'shahbazbutt22ee@gmail.com')
        self.assertIn(self.student.email, purchase_email.to)
        import html
        purchase_body = html.unescape(purchase_email.body)
        self.assertIn(self.student.first_name, purchase_body)
        self.assertIn(self.course_paid.title, purchase_body)
        self.assertIn(str(self.course_paid.price), purchase_body)
        self.assertIn('COMPLETED', purchase_body)
        self.assertIn('LRN-DETAILS99', purchase_body)
        self.assertIn('pi_test_stripe_ref_789', purchase_body)

        # 2. Invoice / receipt email
        invoice_email = next(m for m in mail.outbox if 'Official Tax Invoice' in m.subject)
        self.assertEqual(invoice_email.from_email, 'shahbazbutt22ee@gmail.com')
        self.assertIn(self.student.email, invoice_email.to)
        # Content checks
        invoice_body = html.unescape(invoice_email.body)
        self.assertIn('Mark Jenkins', invoice_body)
        self.assertIn(self.course_paid.title, invoice_body)
        self.assertIn(str(self.course_paid.price), invoice_body)
        self.assertIn('COMPLETED', invoice_body)
        self.assertIn('LRN-DETAILS99', invoice_body)
        self.assertIn('INV-2026-', invoice_body)
        self.assertIn('pi_test_stripe_ref_789', invoice_body)

        # 3. PDF Invoice attachment verification (Udemy / Shopify standard)
        self.assertEqual(len(invoice_email.attachments), 1)
        att_filename, att_content, att_mimetype = invoice_email.attachments[0]
        self.assertTrue(att_filename.startswith('Learnix_Invoice_'))
        self.assertTrue(att_filename.endswith('.pdf'))
        self.assertEqual(att_mimetype, 'application/pdf')
        self.assertTrue(att_content.startswith(b'%PDF-'))

    @patch('stripe.checkout.Session.retrieve')
    def test_payment_success_view_and_webhook_race_condition_never_duplicates(self, mock_retrieve):
        """
        If user returns to payment_success view and Stripe confirms payment,
        and webhook subsequently triggers, confirmation emails are sent exactly once.
        """
        mail.outbox = []

        # Create pending transaction
        tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course_paid,
            order_number='LRN-RACE01',
            amount=self.course_paid.price,
            status='PENDING',
            stripe_checkout_session_id='cs_test_race_session'
        )

        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.payment_intent = 'pi_test_race_intent'
        mock_retrieve.return_value = mock_session

        # 1. User redirects to PaymentSuccessView
        self.client.force_login(self.student)
        success_url = f"{reverse('payments:payment_success')}?session_id=cs_test_race_session&order={tx.order_number}"
        res1 = self.client.get(success_url)
        self.assertEqual(res1.status_code, 200)

        # Verify transaction completed and emails sent
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'COMPLETED')
        self.assertTrue(tx.confirmation_emails_sent)
        self.assertEqual(len(mail.outbox), 3)
        inv_mail = next(m for m in mail.outbox if 'Official Tax Invoice' in m.subject)
        self.assertEqual(len(inv_mail.attachments), 1)
        self.assertTrue(inv_mail.attachments[0][0].startswith('Learnix_Invoice_'))
        self.assertEqual(inv_mail.attachments[0][2], 'application/pdf')

        # 2. Subsequent Stripe Webhook arrives with same session
        webhook_payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_race_session",
                    "payment_intent": "pi_test_race_intent",
                    "metadata": {
                        "user_id": str(self.student.id),
                        "course_id": str(self.course_paid.id),
                        "order_number": tx.order_number,
                    }
                }
            }
        }
        webhook_url = reverse('payments:stripe_webhook')
        res2 = self.client.post(webhook_url, data=json.dumps(webhook_payload), content_type='application/json')
        self.assertEqual(res2.status_code, 200)

        # Still exactly 3 emails (zero duplicate emails on webhook delivery)
        self.assertEqual(len(mail.outbox), 3)

        # 3. User refreshes success page again
        res3 = self.client.get(success_url)
        self.assertEqual(res3.status_code, 200)
        # Still exactly 3 emails
        self.assertEqual(len(mail.outbox), 3)



