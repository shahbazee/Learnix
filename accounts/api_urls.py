from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from . import api_views

urlpatterns = [
    path('register/', api_views.RegisterView.as_view(), name='api-register'),
    path('verify-otp/', api_views.VerifyOTPView.as_view(), name='api-verify-otp'),
    path('login/', api_views.LoginView.as_view(), name='api-login'),
    path('logout/', api_views.LogoutView.as_view(), name='api-logout'),
    path('me/', api_views.MeView.as_view(), name='api-me'),
    path('change-password/', api_views.ChangePasswordView.as_view(), name='api-change-password'),
    path('password-reset/request/', api_views.PasswordResetRequestView.as_view(), name='api-password-reset-request'),
    path('password-reset/verify/', api_views.PasswordResetVerifyView.as_view(), name='api-password-reset-verify'),
    path('password-reset/confirm/', api_views.PasswordResetConfirmView.as_view(), name='api-password-reset-confirm'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
]
