from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

User = get_user_model()

INPUT_CLASSES = (
    "w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 "
    "text-sm text-slate-900 focus:outline-none focus:ring-2 "
    "focus:ring-purple-500/40 focus:border-purple-600 transition-all "
    "placeholder:text-slate-400"
)

EMAIL_CLASSES = (
    "w-full px-4 py-3.5 rounded-xl bg-slate-50 border border-slate-200 "
    "text-sm text-slate-900 focus:outline-none focus:ring-2 "
    "focus:ring-purple-500/40 focus:border-purple-600 transition-all "
    "placeholder:text-slate-400"
)

OTP_CLASSES = (
    "w-full text-center tracking-[0.5em] font-mono text-2xl font-bold "
    "py-3.5 px-4 rounded-xl bg-slate-50 border border-slate-200 "
    "focus:outline-none focus:ring-2 focus:ring-purple-500/40 "
    "focus:border-purple-600 transition-all"
)


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Minimum 8 characters with digits & symbols",
            "autocomplete": "new-password",
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
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
                "class": INPUT_CLASSES,
                "placeholder": "First name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Last name",
            }),
            "username": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Unique handle (e.g. alex_vance)",
            }),
            "email": forms.EmailInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "engineering@domain.com",
            }),
        }

    def __init__(self, *args, **kwargs):
        if 'instance' not in kwargs:
            data = kwargs.get('data')
            if data is None and len(args) > 0 and hasattr(args[0], 'get'):
                data = args[0]
            if data and 'email' in data:
                submitted_email = str(
                    data.get('email', '')
                ).strip().lower()
                if submitted_email:
                    unverified_user = User.objects.filter(
                        email__iexact=submitted_email, is_active=False
                    ).first()
                    if unverified_user:
                        kwargs['instance'] = unverified_user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise ValidationError("A unique handle is required.")

        query = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise ValidationError(
                "This username is already taken. Please choose another."
            )
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        if not email:
            raise ValidationError("A valid email address is required.")

        verified_user = User.objects.filter(
            email__iexact=email, is_active=True
        ).first()
        if verified_user:
            raise ValidationError(
                "An account with this email address already exists. "
                "Please sign in."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")

        if p1 and p2 and p1 != p2:
            self.add_error("confirm_password", "Passwords do not match.")

        if p1 and len(p1) < 8:
            self.add_error(
                "password",
                "Password must be at least 8 characters long."
            )

        role = cleaned_data.get('role')
        if not role or role not in ['student', 'instructor']:
            cleaned_data['role'] = 'student'

        return cleaned_data


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "class": OTP_CLASSES,
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
            raise ValidationError(
                "The verification code must contain digits only."
            )
        return code


class UserLoginForm(AuthenticationForm):
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
            "class": INPUT_CLASSES,
            "placeholder": "Username or Email",
            "autocomplete": "username",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Your password",
            "autocomplete": "current-password",
        })
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "Your account email has not been verified yet. "
                "Please check your email for the OTP or register again "
                "to request a fresh code.",
                code="inactive",
            )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            clean_input = str(username).strip()

            self.user_cache = authenticate(
                self.request, username=clean_input, password=password
            )

            if self.user_cache is None and '@' in clean_input:
                user_by_email = User.objects.filter(
                    email__iexact=clean_input
                ).first()
                if user_by_email:
                    self.user_cache = authenticate(
                        self.request,
                        username=user_by_email.get_username(),
                        password=password
                    )

            if self.user_cache is None:
                inactive_user = (
                    User.objects.filter(
                        username__iexact=clean_input, is_active=False
                    ).first() or
                    User.objects.filter(
                        email__iexact=clean_input, is_active=False
                    ).first()
                )
                if inactive_user and inactive_user.check_password(password):
                    raise ValidationError(
                        "Your account email has not been verified yet. "
                        "Please check your email for the OTP or register "
                        "again to request a fresh code.",
                        code="inactive",
                    )
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

        user = getattr(self, 'user_cache', None)
        submitted_role = self.cleaned_data.get('role')
        if user and submitted_role:
            submitted_role = submitted_role.lower().strip()
            profile = getattr(user, 'profile', None)
            actual_role = (
                getattr(profile, 'role', 'student')
                if profile else 'student'
            )

            if (
                not user.is_superuser and
                submitted_role in ['student', 'instructor']
            ):
                if actual_role != submitted_role:
                    role_display = (
                        "Instructor"
                        if actual_role == 'instructor'
                        else "Student"
                    )
                    raise ValidationError(
                        f"This account is registered as a {role_display}. "
                        f"Please switch the role toggle to "
                        f"'{role_display}' to sign in."
                    )

        return self.cleaned_data


class ForgotPasswordRequestForm(forms.Form):
    email = forms.EmailField(
        label="Registered Email Address",
        widget=forms.EmailInput(attrs={
            "class": EMAIL_CLASSES,
            "placeholder": "engineering@domain.com",
            "autocomplete": "email",
            "autofocus": "autofocus",
        })
    )

    def clean_email(self):
        return self.cleaned_data.get("email", "").strip().lower()


class SetNewPasswordForm(forms.Form):
    password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Minimum 8 characters with digits & symbols",
            "autocomplete": "new-password",
            "autofocus": "autofocus",
        })
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
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
            self.add_error(
                "password",
                "Password must be at least 8 characters long."
            )

        if p1 and self.user:
            try:
                from django.contrib.auth import password_validation
                password_validation.validate_password(p1, self.user)
            except ValidationError as error:
                self.add_error("password", error)

        return cleaned_data
