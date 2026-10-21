import logging

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from google.auth.transport import requests as google_requests
from google.oauth2.id_token import verify_oauth2_token
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .google_auth import find_or_create_google_user
from .models import UserProfile
from .otp_utils import create_and_send_otp
from .serializers import (
    ChangePasswordSerializer,
    DetailResponseSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    ProfileSerializer,
    RegisterSerializer,
    SetNewPasswordSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from .tasks import (
    send_otp_email,
    send_password_changed_email_task,
    send_password_reset_email,
    send_welcome_email,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class AuthRateThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(AuthRateThrottleMixin, generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        create_and_send_otp(user, "registration", send_otp_email)
        return Response(
            {
                "detail": "Verification code sent to your email.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(AuthRateThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        refresh = RefreshToken.for_user(user)
        data = UserSerializer(user).data
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        return Response(data)


class GoogleLoginView(AuthRateThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleLoginSerializer

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            id_info = verify_oauth2_token(
                serializer.validated_data["id_token"],
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception:
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = (id_info.get("email") or "").strip().lower()
        email_verified = id_info.get("email_verified")
        if not email or email_verified not in (True, "true"):
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user, _, _ = find_or_create_google_user(
            email,
            id_info.get("given_name") or "",
            id_info.get("family_name") or "",
        )
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        refresh = RefreshToken.for_user(user)
        data = UserSerializer(user).data
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        return Response(data)


class LogoutView(APIView):
    serializer_class = DetailResponseSerializer

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                logger.warning(
                    "Refresh token blacklist failed during logout.",
                    exc_info=True,
                )
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class VerifyOTPView(AuthRateThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.is_active = True
        user.save(update_fields=["is_active"])
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        transaction.on_commit(lambda: send_welcome_email.delay(user.id))
        return Response(UserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed successfully."})


class PasswordResetRequestView(AuthRateThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            create_and_send_otp(
                user, "password_reset", send_password_reset_email
            )
        return Response(
            {"detail": "If an account exists, a reset code has been sent."}
        )


class PasswordResetVerifyView(AuthRateThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetVerifySerializer

    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"token": serializer.validated_data["token"]})


class PasswordResetConfirmView(AuthRateThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SetNewPasswordSerializer

    def post(self, request):
        serializer = SetNewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        transaction.on_commit(
            lambda: send_password_changed_email_task.delay(user.id)
        )
        return Response({"detail": "Password reset successfully."})
