"""
Forms and ModelForms for user registration, OTP verification, and login.
"""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class StudentRegistrationForm(forms.ModelForm):
    """
    Two-Phase Student Registration Form.
    Validates email uniqueness and password strength before creating inactive account.
    """
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "Minimum 8 characters with digits & symbols",
            "autocomplete": "new-password",
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "Repeat password",
            "autocomplete": "new-password",
        })
    )

    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='student',
        widget=forms.HiddenInput(attrs={'id': 'id_role'}),
        required=False,
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
                "placeholder": "First name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
                "placeholder": "Last name",
            }),
            "username": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
                "placeholder": "Unique handle (e.g. alex_vance)",
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
                "placeholder": "engineering@domain.com",
            }),
        }

    def __init__(self, *args, **kwargs):
        # If an unverified user exists with this email, bind existing instance before super().__init__
        # so ModelForm uniqueness validation properly excludes this instance's pk.
        if 'instance' not in kwargs:
            data = kwargs.get('data')
            if data is None and len(args) > 0 and hasattr(args[0], 'get'):
                data = args[0]
            if data and 'email' in data:
                submitted_email = str(data.get('email', '')).strip().lower()
                if submitted_email:
                    unverified_user = User.objects.filter(email__iexact=submitted_email, is_active=False).first()
                    if unverified_user:
                        kwargs['instance'] = unverified_user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        """Validates username uniqueness, allowing unverified accounts to update their username."""
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise ValidationError("A unique handle is required.")

        query = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        """
        Validates email uniqueness:
        - If email exists and user is verified (is_active=True): rejects with 'already exists' message.
        - If email exists and user is unverified (is_active=False): allows continuing verification.
        """
        email = self.cleaned_data.get("email", "").lower().strip()
        if not email:
            raise ValidationError("A valid email address is required.")

        verified_user = User.objects.filter(email__iexact=email, is_active=True).first()
        if verified_user:
            raise ValidationError("An account with this email address already exists. Please sign in.")
        return email

    def clean(self):
        """Cross-field validation: Password match & minimum complexity."""
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")

        if p1 and p2 and p1 != p2:
            self.add_error("confirm_password", "Passwords do not match.")

        if p1 and len(p1) < 8:
            self.add_error("password", "Password must be at least 8 characters long.")

        role = cleaned_data.get('role')
        if not role or role not in ['student', 'instructor']:
            cleaned_data['role'] = 'student'

        return cleaned_data


class OTPVerificationForm(forms.Form):
    """
    Form for validating the 6-digit cryptographic verification code.
    """
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "class": "w-full text-center tracking-[0.5em] font-mono text-2xl font-bold py-3.5 px-4 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all",
            "placeholder": "••••••",
            "maxlength": "6",
            "pattern": "[0-9]{6}",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "autofocus": "autofocus",
        })
    )

    def clean_otp_code(self):
        code = self.cleaned_data.get("otp_code", "").strip()
        if not code.isdigit():
            raise ValidationError("The verification code must contain digits only.")
        return code


class UserLoginForm(AuthenticationForm):
    """
    Styled credentials login form with backend role validation.
    Enforces that selected role matches user's registered role in database.
    """
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='student',
        widget=forms.HiddenInput(attrs={'id': 'id_role'}),
        required=False,
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "Username or Email",
            "autocomplete": "username",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "Your password",
            "autocomplete": "current-password",
        })
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "Your account email has not been verified yet. Please check your email for the OTP or register again to request a fresh code.",
                code="inactive",
            )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                # Check if an inactive account exists with matching credentials
                inactive_user = (
                    User.objects.filter(username__iexact=username, is_active=False).first() or
                    User.objects.filter(email__iexact=username, is_active=False).first()
                )
                if inactive_user and inactive_user.check_password(password):
                    raise ValidationError(
                        "Your account email has not been verified yet. Please check your email for the OTP or register again to request a fresh code.",
                        code="inactive",
                    )
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        user = self.get_user()
        submitted_role = self.data.get('role')

        if user and submitted_role:
            submitted_role = submitted_role.lower().strip()
            profile = getattr(user, 'profile', None)
            actual_role = getattr(profile, 'role', 'student') if profile else 'student'

            # Allow superusers to access, but enforce strict matching for regular users
            if not user.is_superuser and submitted_role in ['student', 'instructor']:
                if actual_role != submitted_role:
                    role_display = "Instructor" if actual_role == 'instructor' else "Student"
                    raise ValidationError(
                        f"This account is registered as a {role_display}. "
                        f"Please switch the role toggle to '{role_display}' to sign in."
                    )

        return self.cleaned_data


class ForgotPasswordRequestForm(forms.Form):
    """
    Form to request a 6-digit password reset OTP by entering registered email.
    """
    email = forms.EmailField(
        label="Registered Email Address",
        widget=forms.EmailInput(attrs={
            "class": "w-full px-4 py-3.5 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "engineering@domain.com",
            "autocomplete": "email",
            "autofocus": "autofocus",
        })
    )

    def clean_email(self):
        return self.cleaned_data.get("email", "").strip().lower()


class SetNewPasswordForm(forms.Form):
    """
    Form for entering and confirming a new password during the reset flow.
    Enforces password match and Django password validation.
    """
    password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "Minimum 8 characters with digits & symbols",
            "autocomplete": "new-password",
            "autofocus": "autofocus",
        })
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-600 transition-all placeholder:text-slate-400",
            "placeholder": "Repeat new password",
            "autocomplete": "new-password",
        })
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")

        if p1 and p2 and p1 != p2:
            self.add_error("confirm_password", "Passwords do not match.")

        if p1 and len(p1) < 8:
            self.add_error("password", "Password must be at least 8 characters long.")

        if p1 and self.user:
            try:
                from django.contrib.auth import password_validation
                password_validation.validate_password(p1, self.user)
            except ValidationError as error:
                self.add_error("password", error)

        return cleaned_data
