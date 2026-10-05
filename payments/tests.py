from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, CourseCategory, Enrollment
from payments.models import Invoice, PaymentTransaction

User = get_user_model()


class PaymentSuccessViewTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='prof_test',
            email='prof@learnix.edu',
            password='testpassword123'
        )
        self.instructor.profile.role = 'instructor'
        self.instructor.profile.save()
        self.student = User.objects.create_user(
            username='alice_student',
            email='alice@learnix.edu',
            password='testpassword123'
        )
        self.other_student = User.objects.create_user(
            username='bob_student',
            email='bob@learnix.edu',
            password='testpassword123'
        )
        self.category = CourseCategory.objects.create(
            name='AI Systems',
            slug='ai-systems'
        )
        self.course = Course.objects.create(
            title='Neural Networks Masterclass',
            slug='neural-networks-masterclass',
            instructor=self.instructor,
            category=self.category,
            price=Decimal('149.00'),
            is_published=True
        )
        self.transaction = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course,
            order_number='LRN-TEST01',
            stripe_payment_intent_id='pi_test_123456789',
            amount=Decimal('149.00'),
            currency='USD',
            status='COMPLETED'
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student,
            course=self.course,
            is_active=True
        )

    def test_login_required(self):
        url = reverse('payments:payment_success')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_owner_can_open_success_page_for_completed_purchase(self):
        self.client.force_login(self.student)
        url = (
            f"{reverse('payments:payment_success')}?"
            f"order={self.transaction.order_number}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/success.html')
        self.assertContains(response, 'Payment Successful')
        self.assertContains(response, 'Neural Networks Masterclass')
        self.assertContains(response, '149.00')
        self.assertContains(response, 'USD')
        self.assertContains(response, 'pi_test_123456789')
        self.assertContains(response, reverse('courses:dashboard'))

    def test_another_user_cannot_see_purchase(self):
        self.client.force_login(self.other_student)
        url = (
            f"{reverse('payments:payment_success')}?"
            f"order={self.transaction.order_number}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Neural Networks Masterclass')
        self.assertNotContains(response, 'pi_test_123456789')
        self.assertNotContains(response, 'Payment Successful')

    def test_page_shows_real_course_title_and_amount(self):
        self.client.force_login(self.student)
        url = (
            f"{reverse('payments:payment_success')}?"
            f"order={self.transaction.order_number}"
        )
        response = self.client.get(url)
        self.assertContains(response, 'Neural Networks Masterclass')
        self.assertContains(response, '$149.00 USD')

    def test_download_invoice_button_appears_when_invoice_exists(self):
        invoice = Invoice.objects.create(
            transaction=self.transaction,
            invoice_number='INV-2026-TEST1',
            billing_name='Alice Student',
            billing_email='alice@learnix.edu',
            subtotal=Decimal('149.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('149.00')
        )
        self.client.force_login(self.student)
        url = (
            f"{reverse('payments:payment_success')}?"
            f"order={self.transaction.order_number}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Download Invoice')
        download_url = reverse(
            'payments:download_invoice',
            kwargs={'invoice_number': invoice.invoice_number}
        )
        self.assertContains(response, download_url)

    def test_download_invoice_button_hidden_when_no_invoice(self):
        self.client.force_login(self.student)
        url = (
            f"{reverse('payments:payment_success')}?"
            f"order={self.transaction.order_number}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Download Invoice')

    def test_pending_purchase_does_not_show_completed_success_state(self):
        pending_tx = PaymentTransaction.objects.create(
            user=self.student,
            course=self.course,
            order_number='LRN-PENDING99',
            amount=Decimal('149.00'),
            currency='USD',
            status='PENDING'
        )
        self.enrollment.delete()
        self.client.force_login(self.student)
        url = (
            f"{reverse('payments:payment_success')}?"
            f"order={pending_tx.order_number}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Processing')
        self.assertNotContains(response, 'Payment Successful')

    def test_download_invoice_view_security(self):
        invoice = Invoice.objects.create(
            transaction=self.transaction,
            invoice_number='INV-2026-SEC01',
            billing_name='Alice Student',
            billing_email='alice@learnix.edu',
            subtotal=Decimal('149.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('149.00')
        )
        self.client.force_login(self.other_student)
        download_url = reverse(
            'payments:download_invoice',
            kwargs={'invoice_number': invoice.invoice_number}
        )
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 403)
