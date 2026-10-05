import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice, PaymentTransaction
from .serializers import (
    CheckoutSerializer,
    InvoiceSerializer,
    PaymentTransactionSerializer,
)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data['course']
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            course=course,
            order_number=(
                PaymentTransaction.generate_order_number()
            ),
            amount=course.price,
            currency='USD',
            status='PENDING',
        )
        stripe.api_key = settings.STRIPE_SECRET_KEY
        success_url = request.build_absolute_uri(
            reverse('payment-success')
        ) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = request.build_absolute_uri(
            reverse('payment-cancel')
        )
        session = stripe.checkout.Session.create(
            mode='payment',
            line_items=[
                {
                    'price_data': {
                        'currency':
                            transaction.currency.lower(),
                        'unit_amount':
                            int(transaction.amount * 100),
                        'product_data': {
                            'name': course.title
                        },
                    },
                    'quantity': 1,
                }
            ],
            metadata={
                'order_number': transaction.order_number,
                'user_id': str(request.user.id),
                'course_id': str(course.id),
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )
        transaction.stripe_checkout_session_id = session.id
        transaction.save(
            update_fields=['stripe_checkout_session_id']
        )
        return Response(
            {
                'checkout_url': session.url,
                'order_number': transaction.order_number,
            },
            status=201,
        )


class PaymentSuccessView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'detail': 'Missing session_id.'}, status=400
            )
        transaction = get_object_or_404(
            PaymentTransaction,
            stripe_checkout_session_id=session_id,
        )
        data = PaymentTransactionSerializer(transaction).data
        data['detail'] = 'Payment successful.'
        return Response(data)


class PaymentCancelView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {'detail': 'Payment cancelled. No charge was made.'}
        )


class MyTransactionsView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaymentTransaction.objects.filter(
            user=self.request.user
        ).select_related(
            'course__category', 'course__instructor'
        )


class MyInvoicesView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(
            transaction__user=self.request.user
        ).select_related('transaction__course')
