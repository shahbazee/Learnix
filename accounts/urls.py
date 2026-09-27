"""
URL routing configuration for accounts application.
Provides endpoints for Signup, Login, Logout, Two-Phase OTP Verification,
Password Reset Lifecycle, Profile Management, and Google OAuth 2.0.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Registration & Verification
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),

    # Credentials Authentication
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # Profile & Account Settings
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # Forgot Password & Reset Flow
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('forgot-password/verify-otp/', views.VerifyResetOTPView.as_view(), name='verify_reset_otp'),
    path('forgot-password/resend-otp/', views.ResendResetOTPView.as_view(), name='resend_reset_otp'),
    path('forgot-password/reset/', views.ResetPasswordView.as_view(), name='reset_password'),

    # Google OAuth 2.0
    path('google/login/', views.GoogleLoginView.as_view(), name='google_login'),
    path('google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),
]
