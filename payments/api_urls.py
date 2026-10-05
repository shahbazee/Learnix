from django.urls import path

from .api_views import (
    CheckoutView,
    MyInvoicesView,
    MyTransactionsView,
    PaymentCancelView,
    PaymentSuccessView,
)

urlpatterns = [
    path(
        'checkout/', CheckoutView.as_view(), name='checkout'
    ),
    path(
        'success/',
        PaymentSuccessView.as_view(),
        name='payment-success',
    ),
    path(
        'cancel/',
        PaymentCancelView.as_view(),
        name='payment-cancel',
    ),
    path(
        'my-transactions/',
        MyTransactionsView.as_view(),
        name='my-transactions',
    ),
    path(
        'my-invoices/',
        MyInvoicesView.as_view(),
        name='my-invoices',
    ),
]
