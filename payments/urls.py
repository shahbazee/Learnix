from django.urls import path

from . import views
from . import webhooks

app_name = 'payments'

urlpatterns = [
    path('billing/', views.BillingHubView.as_view(), name='billing_hub'),
    path(
        'invoice/<str:invoice_number>/download/',
        views.DownloadInvoicePDFView.as_view(),
        name='download_invoice'
    ),
    path(
        'receipt/<str:order_number>/download/',
        views.DownloadReceiptPDFView.as_view(),
        name='download_receipt'
    ),
    path(
        'billing/export-all/',
        views.ExportAllInvoicesZipView.as_view(),
        name='export_all_invoices'
    ),
    path(
        'checkout/<slug:course_slug>/',
        views.CreateCheckoutSessionView.as_view(),
        name='create_checkout_session'
    ),
    path(
        'checkout/<slug:course_slug>/modal/',
        views.CheckoutModalView.as_view(),
        name='checkout_modal'
    ),
    path(
        'success/',
        views.PaymentSuccessView.as_view(),
        name='payment_success'
    ),
    path(
        'cancel/',
        views.PaymentCancelView.as_view(),
        name='payment_cancel'
    ),
    path('webhook/stripe/', webhooks.stripe_webhook, name='stripe_webhook'),
]
