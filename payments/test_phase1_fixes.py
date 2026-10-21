import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from courses.models import Course, Enrollment

from .models import PaymentTransaction

User = get_user_model()

TEST_PASSWORD = "Str0ng!Passw0rd"


def make_user(username, email):
    return User.objects.create_user(
        username=username, email=email, password=TEST_PASSWORD
    )


def make_paid_course(instructor):
    return Course.objects.create(
        title="Paid Course",
        slug="paid-course",
        instructor=instructor,
        short_description="A paid course.",
        price=Decimal("49.00"),
        is_published=True,
    )


def make_transaction(user, course, status="PENDING", session_id=None):
    return PaymentTransaction.objects.create(
        user=user,
        course=course,
        order_number=PaymentTransaction.generate_order_number(),
        amount=Decimal("49.00"),
        currency="USD",
        status=status,
        stripe_checkout_session_id=session_id,
    )


class WebhookFailClosedTests(TestCase):
    def setUp(self):
        self.instructor = make_user("wh_inst", "whi@example.com")
        self.student = make_user("wh_stud", "whs@example.com")
        self.course = make_paid_course(self.instructor)

    def event_payload(self, event_type, session_id, order_number):
        return {
            "type": event_type,
            "data": {
                "object": {
                    "id": session_id,
                    "metadata": {
                        "user_id": str(self.student.id),
                        "course_id": str(self.course.id),
                        "order_number": order_number,
                    },
                }
            },
        }

    def test_unsigned_event_rejected_when_debug_off(self):
        transaction = make_transaction(
            self.student, self.course, session_id="cs_closed"
        )
        payload = self.event_payload(
            "checkout.session.expired",
            "cs_closed",
            transaction.order_number,
        )
        response = self.client.post(
            reverse("payments:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "PENDING")

    @override_settings(DEBUG=True)
    def test_expired_session_marks_transaction_failed(self):
        transaction = make_transaction(
            self.student, self.course, session_id="cs_open"
        )
        payload = self.event_payload(
            "checkout.session.expired",
            "cs_open",
            transaction.order_number,
        )
        response = self.client.post(
            reverse("payments:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "FAILED")


@override_settings(DEBUG=True)
class WebhookRefundTests(TestCase):
    def setUp(self):
        self.instructor = make_user("rf_inst", "rfi@example.com")
        self.student = make_user("rf_stud", "rfs@example.com")
        self.course = make_paid_course(self.instructor)
        self.transaction = make_transaction(
            self.student, self.course, status="COMPLETED"
        )
        self.transaction.stripe_payment_intent_id = "pi_refund_1"
        self.transaction.save(
            update_fields=["stripe_payment_intent_id"]
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, is_active=True
        )

    def test_charge_refunded_marks_refunded_and_unenrolls(self):
        payload = {
            "type": "charge.refunded",
            "data": {"object": {"payment_intent": "pi_refund_1"}},
        }
        response = self.client.post(
            reverse("payments:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "REFUNDED")
        self.enrollment.refresh_from_db()
        self.assertFalse(self.enrollment.is_active)


class RefundAdminActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="root_admin",
            email="root@example.com",
            password=TEST_PASSWORD,
        )
        self.instructor = make_user("ra_inst", "rai@example.com")
        self.student = make_user("ra_stud", "ras@example.com")
        self.course = make_paid_course(self.instructor)
        self.transaction = make_transaction(
            self.student, self.course, status="COMPLETED"
        )
        self.transaction.stripe_payment_intent_id = "pi_admin_1"
        self.transaction.save(
            update_fields=["stripe_payment_intent_id"]
        )
        self.client.force_login(self.admin)

    @patch("payments.admin.stripe.Refund.create")
    def test_refund_action_calls_stripe(self, mock_refund):
        mock_refund.return_value = MagicMock()
        response = self.client.post(
            "/admin/payments/paymenttransaction/",
            {
                "action": "refund_payments_action",
                "_selected_action": [str(self.transaction.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)
        mock_refund.assert_called_once_with(
            payment_intent="pi_admin_1"
        )


class ApiCheckoutStripeErrorTests(TestCase):
    def setUp(self):
        self.instructor = make_user("ac_inst", "aci@example.com")
        self.student = make_user("ac_stud", "acs@example.com")
        self.course = make_paid_course(self.instructor)
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    @patch("payments.api_views.stripe.checkout.Session.create")
    def test_stripe_error_returns_502_and_marks_failed(
        self, mock_create
    ):
        mock_create.side_effect = stripe.error.StripeError("down")
        response = self.api.post(
            reverse("checkout"),
            {"course_id": self.course.id},
            format="json",
        )
        self.assertEqual(response.status_code, 502)
        transaction = PaymentTransaction.objects.get(
            user=self.student, course=self.course
        )
        self.assertEqual(transaction.status, "FAILED")
