from django.test import SimpleTestCase
from django.urls import reverse
from core.views import custom_page_not_found_view, custom_server_error_view, custom_permission_denied_view
from django.test import RequestFactory


class CoreViewsTestCase(SimpleTestCase):
    """
    Validates foundational URL routing, Bento grid components, search modal,
    and error handling for Learnix.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def test_home_page_status_and_branding(self):
        """Home page should return 200 OK and include Learnix branding and Bento cards."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Learnix')
        self.assertContains(response, 'Master Modern Engineering')
        self.assertContains(response, 'Interactive Curriculum')
        self.assertContains(response, 'Full-Stack Django &amp; Scalable AI Architecture')
        self.assertContains(response, 'tasks.py')
        self.assertContains(response, 'Peer-Verified Mastery')
        self.assertContains(response, 'Zero Latency Global Clusters')

    def test_about_page_status_and_branding(self):
        """About page should return 200 OK and include Learnix branding."""
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Learnix')
        self.assertContains(response, 'PLATFORM MANIFESTO')

    def test_search_modal_presence(self):
        """The ⌘K quick-search modal should be present in the base layout."""
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'id="searchModal"')
        self.assertContains(response, 'modalSearchInput')

    def test_custom_404_view(self):
        """Custom 404 view returns status 404 and Page Not Found template."""
        request = self.factory.get('/nonexistent-dimension/')
        response = custom_page_not_found_view(request)
        self.assertEqual(response.status_code, 404)
        self.assertIn('Page Not Found', response.content.decode())

    def test_custom_403_view(self):
        """Custom 403 view returns status 403 and access denied theme."""
        request = self.factory.get('/restricted-zone/')
        response = custom_permission_denied_view(request)
        self.assertEqual(response.status_code, 403)
        self.assertIn('Access Denied', response.content.decode())

    def test_custom_500_view(self):
        """Custom 500 view returns status 500 and internal server error template."""
        request = self.factory.get('/faulty-reactor/')
        response = custom_server_error_view(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn('Internal Server Error', response.content.decode())


from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from core.emails import (
    send_registration_success_email,
    send_otp_verification_email,
    send_forgot_password_otp_email,
    send_password_changed_email,
    send_course_purchase_success_email,
    send_payment_receipt_invoice_email,
    send_course_enrollment_email,
    send_payment_failed_email,
)

User = get_user_model()


class CentralizedEmailSubsystemTestCase(TestCase):
    """
    Automated verification of the centralized email service across all 8 platform events.
    Verifies template rendering, fallback text generation, and defensive error handling.
    """

    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            username='email_tester',
            email='tester@learnix.edu',
            first_name='Alex',
            last_name='Tester',
            password='TestPassword123!'
        )

        class DummyCourse:
            title = 'Distributed High-Concurrency Microservices'
            slug = 'distributed-microservices'
            level = 'Advanced'
            short_description = 'Scale resilient backend systems with Python and Kafka.'

        class DummyTransaction:
            order_number = 'LRN-TEST-9988'
            amount = Decimal('149.00')
            currency = 'USD'
            status = 'COMPLETED'
            stripe_checkout_session_id = 'cs_test_mock_9988'
            stripe_payment_intent_id = 'pi_test_mock_9988'
            created_at = timezone.now()

        class DummyInvoice:
            invoice_number = 'INV-2026-TEST99'
            billing_name = 'Alex Tester'
            billing_email = 'tester@learnix.edu'
            issued_at = timezone.now()
            pdf_file = None

        self.mock_course = DummyCourse()
        self.mock_tx = DummyTransaction()
        self.mock_invoice = DummyInvoice()
        self.mock_invoice.transaction = self.mock_tx

    def test_event_1_registration_success_email(self):
        """1. Registration Success email renders and dispatches successfully."""
        success = send_registration_success_email(self.user)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('tester@learnix.edu', sent.to)
        self.assertIn('Registration Confirmed', sent.subject)
        self.assertIn('Alex', sent.body)

    def test_event_2_otp_verification_email(self):
        """2. OTP Verification email contains 6-digit code and expiry."""
        success = send_otp_verification_email(self.user, '829104', expires_minutes=10)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('829104', sent.subject)
        self.assertIn('829104', sent.body)
        self.assertIn('10 minutes', sent.body)

    def test_event_3_forgot_password_otp_email(self):
        """3. Forgot Password OTP email contains reset code and expiry."""
        success = send_forgot_password_otp_email(self.user, '471920', expires_minutes=10)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Password Reset Code: 471920', sent.subject)
        self.assertIn('471920', sent.body)

    def test_event_4_password_changed_email(self):
        """4. Password Changed security notice email alerts the user."""
        success = send_password_changed_email(self.user)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Password Was Changed', sent.subject)
        self.assertIn('tester@learnix.edu', sent.to)

    def test_event_5_course_purchase_success_email(self):
        """5. Course Purchase Successful email contains course title and order reference."""
        success = send_course_purchase_success_email(self.user, self.mock_course, self.mock_tx)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Payment Confirmed', sent.subject)
        self.assertIn('Distributed High-Concurrency Microservices', sent.subject)
        self.assertIn('LRN-TEST-9988', sent.body)

    def test_event_6_payment_receipt_invoice_email(self):
        """6. Payment Receipt / Invoice email details amount, invoice number, and exact format."""
        fake_pdf = b"%PDF-1.4 Mock PDF Content"
        success = send_payment_receipt_invoice_email(
            self.user, self.mock_course, self.mock_tx, self.mock_invoice, pdf_bytes=fake_pdf
        )
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Official Tax Invoice & Receipt: #INV-2026-TEST99', sent.subject)
        self.assertIn('LRN-TEST-9988', sent.body)
        self.assertIn('149.00', sent.body)
        self.assertIn('COMPLETED (Paid via Stripe)', sent.body)
        self.assertIn('Learnix_Invoice_INV-2026-TEST99.pdf', sent.body)
        # Verify PDF attachment
        self.assertEqual(len(sent.attachments), 1)
        self.assertEqual(sent.attachments[0][0], 'Learnix_Invoice_INV-2026-TEST99.pdf')

    def test_event_6_dual_recipients_account_and_stripe_hosted_email(self):
        """Payment Receipt & Invoice dispatches to both account email and Stripe checkout email if different."""
        self.mock_invoice.billing_email = 'stripe_guest@example.com'
        success = send_payment_receipt_invoice_email(
            self.user, self.mock_course, self.mock_tx, self.mock_invoice
        )
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('tester@learnix.edu', sent.to)
        self.assertIn('stripe_guest@example.com', sent.to)

    def test_event_7_course_enrollment_email(self):
        """7. Course Enrollment email confirms student access."""
        success = send_course_enrollment_email(self.user, self.mock_course)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Enrollment Active', sent.subject)
        self.assertIn('Distributed High-Concurrency Microservices', sent.body)

    def test_event_8_payment_failed_email(self):
        """8. Payment Failed email alerts the user with error reason."""
        success = send_payment_failed_email(
            self.user,
            self.mock_course,
            error_reason='Insufficient funds on card'
        )
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Payment Incomplete', sent.subject)
        self.assertIn('Insufficient funds on card', sent.body)

    @patch('core.emails.send_mail')
    def test_email_dispatch_failure_is_handled_safely(self, mock_send_mail):
        """Email delivery failures (e.g. SMTP down) return False and never crash the caller."""
        mock_send_mail.side_effect = Exception("SMTP Connection Refused")
        success = send_registration_success_email(self.user)
        # Asserts it safely returned False without raising an uncaught exception
        self.assertFalse(success)

