import stripe
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice, PaymentTransaction
from .services import create_stripe_checkout_session
from .serializers import (
    CheckoutSerializer,
    PaymentDetailResponseSerializer,
    InvoiceSerializer,
    PaymentTransactionSerializer,
)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CheckoutSerializer

    def post(self, request):
        serializer = CheckoutSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            course=course,
            order_number=(PaymentTransaction.generate_order_number()),
            amount=course.price,
            currency="USD",
            status="PENDING",
        )
        success_url = (
            request.build_absolute_uri(reverse("payment-success"))
            + "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = request.build_absolute_uri(reverse("payment-cancel"))
        try:
            session = create_stripe_checkout_session(
                user=request.user,
                course=course,
                transaction=transaction,
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except stripe.error.StripeError:
            transaction.status = "FAILED"
            transaction.save(update_fields=["status"])
            return Response(
                {"detail": "Payment provider error. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {
                "checkout_url": session.url,
                "order_number": transaction.order_number,
            },
            status=201,
        )


class PaymentSuccessView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PaymentTransactionSerializer

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "Missing session_id."}, status=400)
        transaction = get_object_or_404(
            PaymentTransaction,
            stripe_checkout_session_id=session_id,
        )
        data = PaymentTransactionSerializer(transaction).data
        data["detail"] = "Payment successful."
        return Response(data)


class PaymentCancelView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PaymentDetailResponseSerializer

    def get(self, request):
        return Response({"detail": "Payment cancelled. No charge was made."})


class MyTransactionsView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaymentTransaction.objects.filter(
            user=self.request.user
        ).select_related("course__category", "course__instructor")


class MyInvoicesView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(
            transaction__user=self.request.user
        ).select_related("transaction__course")
