from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.contrib.auth import update_session_auth_hash
from django.core import signing

from rest_framework import serializers

from .models import EmailOTP, UserProfile
from .otp_utils import verify_otp

User = get_user_model()

OTP_TOKEN_SALT = 'learnix_otp_verify'
OTP_TOKEN_MAX_AGE = 1800


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=['student', 'instructor'], default='student'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password', 'password2']

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                'This username is already taken.'
            )
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(
            email__iexact=value, is_active=True
        ).exists():
            raise serializers.ValidationError(
                'An account with this email already exists.'
            )
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role', 'student')
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save(update_fields=['role'])
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs['username'],
            password=attrs['password'],
        )
        if user is None:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Account is not active.')
        attrs['user'] = user
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        try:
            user = User.objects.get(email__iexact=email, is_active=False)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'No pending registration found for this email.'
            )
        success, error, _ = verify_otp(
            user, attrs['otp_code'], 'registration'
        )
        if not success:
            raise serializers.ValidationError({'otp_code': error})
        attrs['user'] = user
        return attrs


class ProfileUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class ProfileSerializer(serializers.ModelSerializer):
    user = ProfileUserSerializer(required=False)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'role', 'avatar', 'bio', 'headline',
            'phone_number', 'country_code', 'location_timezone',
            'academic_suffix', 'public_directory', 'google_email',
            'github_username', 'storage_used_gb', 'storage_total_gb',
            'two_factor_enabled', 'preferred_currency',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'role', 'storage_used_gb', 'storage_total_gb',
            'created_at', 'updated_at',
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        password_validation.validate_password(
            value, self.context['request'].user
        )
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Current password is incorrect.'}
            )
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {'new_password2': 'New passwords do not match.'}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        update_session_auth_hash(self.context['request'], user)
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or code.')
        success, error, _ = verify_otp(
            user, attrs['otp_code'], 'password_reset'
        )
        if not success:
            raise serializers.ValidationError({'otp_code': error})
        attrs['token'] = signing.dumps(user.id, salt=OTP_TOKEN_SALT)
        attrs['user'] = user
        return attrs


class SetNewPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            user_id = signing.loads(
                attrs['token'],
                salt=OTP_TOKEN_SALT,
                max_age=OTP_TOKEN_MAX_AGE,
            )
        except (signing.BadSignature, signing.SignatureExpired):
            raise serializers.ValidationError(
                {'token': 'Invalid or expired token.'}
            )
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'token': 'Invalid token.'})
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': 'Passwords do not match.'}
            )
        password_validation.validate_password(attrs['password'], user)
        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['password'])
        user.is_active = True
        user.save()
        EmailOTP.objects.filter(
            user=user, purpose='password_reset'
        ).delete()
        return user
