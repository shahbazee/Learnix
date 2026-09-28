"""
Django settings for Learnix E-Learning Platform.

Configured strictly for PostgreSQL 15+ and decoupled environment variables.
"""

import os
import sys
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = config('SECRET_KEY', default='django-insecure-learnix-dev-key-change-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Platform Identity
SITE_NAME = 'Learnix'

# Application definition
INSTALLED_APPS = [
    # Django Built-in
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Learnix Core Apps
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'courses.apps.CoursesConfig',
    'payments.apps.PaymentsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'learnix_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'learnix_project.wsgi.application'
ASGI_APPLICATION = 'learnix_project.asgi.application'

# Database Configuration: PostgreSQL 15+ ONLY
# SQLite is strictly prohibited per architectural requirements
def _resolve_database_config():
    raw_url = os.environ.get('DATABASE_URL') or config('DATABASE_URL', default=None)
    if not raw_url:
        return None

    # Strip any leading/trailing whitespace, backslashes, and accidental quotes (common when pasting into Render/PaaS dashboards)
    cleaned_url = str(raw_url).strip().strip("'\"\\ \t\n\r")
    if not cleaned_url:
        return None

    # Auto-repair URL missing protocol scheme
    if cleaned_url.startswith('://'):
        cleaned_url = f'postgres{cleaned_url}'
    elif cleaned_url.startswith('//'):
        cleaned_url = f'postgres:{cleaned_url}'
    elif '://' not in cleaned_url and '@' in cleaned_url:
        cleaned_url = f'postgres://{cleaned_url}'

    import dj_database_url
    try:
        return dj_database_url.parse(
            cleaned_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    except Exception as exc:
        raise ValueError(
            f"Invalid DATABASE_URL provided ('{raw_url}'). "
            "Please ensure your DATABASE_URL in the Render dashboard starts with "
            "'postgres://' or 'postgresql://' and has no surrounding quotes. "
            f"Details: {exc}"
        ) from exc


_db_config = _resolve_database_config()
if _db_config:
    DATABASES = {
        'default': _db_config
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='learnix_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

# Media files (User uploads, avatars, PDF invoices)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Accelerated password hasher for automated tests
if 'test' in sys.argv:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600  # 2 weeks
CSRF_COOKIE_HTTPONLY = False  # Allows JS to read for AJAX CSRF headers

# Email Subsystem (SMTP Backend Configuration)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST") or config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT") or config("EMAIL_PORT", default=587, cast=int))
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER") or config("EMAIL_HOST_USER", default="shahbazbutt22ee@gmail.com")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD") or config("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT") or config("EMAIL_TIMEOUT", default=10, cast=int))

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    config("DEFAULT_FROM_EMAIL", default="shahbazbutt22ee@gmail.com")
)

# Stripe Configuration (Test/Sandbox Mode Only per requirements)
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default=config('STRIPE_PUBLIC_KEY', default='pk_test_placeholder'))
STRIPE_PUBLIC_KEY = STRIPE_PUBLISHABLE_KEY
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='whsec_placeholder')
STRIPE_CURRENCY = config('STRIPE_CURRENCY', default='usd')

# Google OAuth 2.0 Configuration
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

# Render & Production Hostname / CSRF Configuration (Phase 11)
RENDER_EXTERNAL_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default=None)
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
custom_csrf = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
for origin in custom_csrf:
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# Production Deployment Security Hardening (Phase 11)
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
