from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),

    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    path(
        'forgot-password/',
        views.ForgotPasswordView.as_view(),
        name='forgot_password'
    ),
    path(
        'forgot-password/verify-otp/',
        views.VerifyResetOTPView.as_view(),
        name='verify_reset_otp'
    ),
    path(
        'forgot-password/resend-otp/',
        views.ResendResetOTPView.as_view(),
        name='resend_reset_otp'
    ),
    path(
        'forgot-password/reset/',
        views.ResetPasswordView.as_view(),
        name='reset_password'
    ),

    path(
        'google/login/',
        views.GoogleLoginView.as_view(),
        name='google_login'
    ),
    path(
        'google/callback/',
        views.GoogleCallbackView.as_view(),
        name='google_callback'
    ),
]
