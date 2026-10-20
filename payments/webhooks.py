import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.emails import send_payment_failed_email
from courses.models import Course

from .services import fulfill_order_and_dispatch_emails

User = get_user_model()
logger = logging.getLogger(__name__)


def _event_field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_event(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    is_mock_mode = not sig_header and (
        settings.DEBUG
        or not settings.STRIPE_WEBHOOK_SECRET
        or settings.STRIPE_WEBHOOK_SECRET.endswith("_placeholder")
    )
    if is_mock_mode:
        try:
            return json.loads(payload.decode("utf-8")), None
        except Exception:
            return None, HttpResponse(status=400)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event, None
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(
            f"Stripe Webhook Signature Verification failed: {e}"
        )
        return None, HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Unexpected webhook error: {e}")
        return None, HttpResponse(status=400)


def _session_and_metadata(event):
    session = _event_field(_event_field(event, "data", {}), "object", {})
    metadata = _event_field(session, "metadata", {})
    if hasattr(metadata, "to_dict"):
        metadata = metadata.to_dict()
    return session, metadata


def _handle_checkout_completed(event):
    session, metadata = _session_and_metadata(event)
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")
    order_number = metadata.get("order_number")
    if not (user_id and course_id):
        logger.info(
            "Stripe webhook: 'checkout.session.completed' received "
            "without user/course metadata (e.g. from 'stripe trigger "
            "checkout.session.completed'). Event acknowledged."
        )
        return None
    try:
        customer_details = _event_field(session, "customer_details", {})
        result = fulfill_order_and_dispatch_emails(
            user_id=int(user_id),
            course_id=int(course_id),
            order_number=order_number,
            session_id=_event_field(session, "id"),
            stripe_payment_intent=_event_field(session, "payment_intent"),
            billing_name=_event_field(customer_details, "name"),
            billing_email=_event_field(customer_details, "email"),
        )
        if not result:
            logger.error(
                f"Fulfillment returned None for order #{order_number}"
            )
            return HttpResponse(status=500)
    except Exception as e:
        logger.error(f"Error fulfilling webhook order: {e}")
        return HttpResponse(status=500)
    return None


def _handle_payment_failed(event):
    session, metadata = _session_and_metadata(event)
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")
    if not (user_id and course_id):
        return
    last_error = _event_field(session, "last_payment_error", {})
    default_err = (
        "The payment was declined by your bank or the session expired."
    )
    if isinstance(last_error, dict):
        error_msg = last_error.get("message")
    else:
        error_msg = getattr(last_error, "message", default_err)
    try:
        user = User.objects.get(id=int(user_id))
        course = Course.objects.get(id=int(course_id))
        send_payment_failed_email(user, course, error_reason=error_msg)
        logger.info(
            f"Dispatched payment failed email for user "
            f"{user.username}, course {course.title}"
        )
    except Exception as e:
        logger.error(f"Error dispatching payment failure email: {e}")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    event, error_response = _extract_event(request)
    if error_response is not None:
        return error_response
    event_type = _event_field(event, "type")
    if event_type == "checkout.session.completed":
        response = _handle_checkout_completed(event)
        if response is not None:
            return response
    elif event_type in [
        "payment_intent.payment_failed",
        "checkout.session.expired",
    ]:
        _handle_payment_failed(event)
    return HttpResponse(status=200)
