"""
Sections 1 to 5 for Learnix Technical Documentation:
1. Project Overview
2. Django Fundamentals Used in Learnix
3. Deep Dive into Django Apps
4. Models and Database Architecture
5. Migrations from A to Z
"""

from .doc_builder import (
    p, bullet, h1, h2, h3, spacer, hr, code_box, callout, viva_qa, create_table
)
from reportlab.platypus import PageBreak

def build_part1():
    story = []

    # =========================================================================
    # SECTION 1: PROJECT OVERVIEW
    # =========================================================================
    story.append(h1("1. Project Overview & System Architecture"))
    story.append(hr())
    story.append(p(
        "<b>Learnix</b> is an enterprise-grade, full-stack educational masterclass platform built with "
        "Python 3.14 and <b>Django 5.0</b> on top of a <b>PostgreSQL 15+</b> relational database. "
        "The platform delivers intensive architectural curriculums across cutting-edge technical domains, "
        "including AI & Multi-Agent Swarms, Machine Learning & LLMs, Cloud DevOps, System Design, Zero-Trust Security, "
        "and Distributed Data Systems."
    ))
    story.append(p(
        "The backend is architected following the clean Model-View-Template (MVT) pattern, strictly adhering to "
        "decoupled twelve-factor application methodologies, robust security standards, atomic transactions, "
        "and centralized asynchronous services."
    ))

    story.append(h2("1.1 Core High-Level Architecture"))
    story.append(p(
        "The Learnix architecture is composed of five distinct layers that communicate synchronously and asynchronously:"
    ))
    story.append(bullet("<b>Client Presentation Layer:</b> Server-rendered HTML5 templates styled with Tailwind CSS, glassmorphic UI components, and client-side interactivity powered by vanilla JavaScript and Lenis smooth scrolling."))
    story.append(bullet("<b>Application Server Layer:</b> Django 5.0 WSGI application hosted via Gunicorn (in production) or runserver (development), running asynchronous and synchronous class-based view logic."))
    story.append(bullet("<b>Persistence & Relational Database Layer:</b> PostgreSQL 15+ holding 11 relational models with strict constraints, foreign keys, compound indexes, and atomic transaction handling."))
    story.append(bullet("<b>Payment & External Gateway Layer:</b> Stripe Hosted Checkout integration utilizing direct external browser redirection (checkout.stripe.com) and asynchronous HMAC-SHA256 verified webhooks."))
    story.append(bullet("<b>Document & Email Generation Pipeline:</b> Headless PDF generation via ReportLab / xhtml2pdf (academic invoices, financial receipts, cryptographically signed certificates) and centralized SMTP transactional email dispatch."))

    story.append(h2("1.2 Django Project vs. Django Apps Architecture"))
    story.append(p(
        "A foundational concept in Django is the clear separation between a <b>Django Project</b> and <b>Django Apps</b>:"
    ))
    story.append(create_table([
        ["Architectural Unit", "Directory in Learnix", "Primary Role & Responsibility"],
        ["Django Project", "learnix_project/", "The master container. Contains global settings (settings.py), master URL dispatcher (urls.py), WSGI/ASGI entrypoints, and cross-cutting configuration."],
        ["Django App: core", "core/", "Informational marketing showcase, dynamic bento home page, about page, global brand context processors, and custom 404/500/403 security intercept views."],
        ["Django App: accounts", "accounts/", "User lifecycle, two-phase cryptographic 6-digit email OTP verification, rate-limited resend, profile management, and session authentication."],
        ["Django App: courses", "courses/", "Curriculum taxonomy, categories, courses, modules, video lesson player, student progress calculation, and verifiable completion certificates."],
        ["Django App: payments", "payments/", "Stripe Hosted Checkout session creation, payment transactions, PDF tax invoice generation, webhook listener, and receipt dispatch."]
    ], [110, 110, 320]))

    story.append(h2("1.3 Request-Response Lifecycle"))
    story.append(p(
        "Every incoming HTTP request in Learnix traverses a strict, secure pipeline before generating a response:"
    ))
    story.append(bullet("<b>1. Web Server Ingress:</b> The client sends an HTTP request. Gunicorn or Django runserver receives the TCP packet and invokes the WSGI handler (learnix_project/wsgi.py)."))
    story.append(bullet("<b>2. Middleware Processing:</b> The request passes downwards through 8 sequential middleware layers (SecurityMiddleware -> WhiteNoiseMiddleware -> SessionMiddleware -> CommonMiddleware -> CsrfViewMiddleware -> AuthenticationMiddleware -> MessageMiddleware -> XFrameOptionsMiddleware)."))
    story.append(bullet("<b>3. URL Dispatcher:</b> Django consults ROOT_URLCONF ('learnix_project.urls'). It traverses URL patterns using regex/path converters and delegates the request to the matching app-level route."))
    story.append(bullet("<b>4. View Execution & Access Control:</b> The target View executes. Mixins (e.g. LoginRequiredMixin, EnrolledCourseRequiredMixin) verify authorization before business logic runs."))
    story.append(bullet("<b>5. ORM & Database Query:</b> The view queries PostgreSQL through Django's ORM. Transactions (transaction.atomic) ensure integrity."))
    story.append(bullet("<b>6. Template Rendering or JSON Output:</b> For web pages, the Django Template Engine renders HTML with context variables. For live APIs (search, progress toggle), JsonResponse serializes data."))
    story.append(bullet("<b>7. Egress Middleware & HTTP Response:</b> The response passes back up through the middleware (attaching session cookies and CSRF headers) and returns to the browser."))

    story.append(h2("1.4 Complete Backend Directory Tree & Component Responsibilities"))
    story.append(code_box("""Learnix/
├── .env                              # Decoupled environment variables (secrets, DB credentials, API keys)
├── manage.py                         # Django administrative command-line utility
├── requirements.txt                  # Locked Python dependencies (Django 5, psycopg, Stripe, etc.)
├── runtime.txt                       # Runtime Python version specification (python-3.14)
├── learnix_project/                  # Master Project Configuration Directory
│   ├── settings.py                   # Central settings: PostgreSQL, apps, middleware, email, Stripe
│   ├── urls.py                       # Top-level URL routing table delegating to apps
│   ├── wsgi.py                       # WSGI entry point for Gunicorn web server deployment
│   └── asgi.py                       # ASGI entry point for asynchronous capabilities
├── accounts/                         # User Authentication & Profile App
│   ├── models.py                     # UserProfile (OneToOne) and EmailOTP (Two-phase verification)
│   ├── views.py                      # SignUpView, VerifyOTPView, ResendOTPView, Login/Logout, Profile
│   ├── forms.py                      # StudentRegistrationForm, OTPVerificationForm, UserLoginForm
│   ├── mixins.py                     # EnrolledCourseRequiredMixin access control
│   ├── signals.py                    # post_save signal auto-provisioning UserProfile on user creation
│   ├── apps.py                       # AppConfig with ready() hook connecting signals
│   └── urls.py                       # /accounts/ routes
├── core/                             # Core Informational & Platform App
│   ├── views.py                      # HomeView, AboutView, custom 404, 500, 403 error handlers
│   ├── context_processors.py         # site_context exposing SITE_NAME and DEBUG globally
│   ├── exceptions.py                 # Learnix custom exception hierarchy
│   └── urls.py                       # / and /about/ routes
├── courses/                          # Curriculum, Progress & Certification App
│   ├── models.py                     # CourseCategory, Course, CourseModule, Lesson, Enrollment, LessonProgress, Certificate
│   ├── views.py                      # CourseListView, CourseDetailView, StudentDashboardView, LessonView, APIs
│   ├── decorators.py                 # @enrolled_required view decorator
│   ├── services.py                   # generate_certificate_pdf() via xhtml2pdf
│   ├── templatetags/course_extras.py # Custom filters: format_duration, calculate_progress_badge, times
│   ├── management/commands/          # Custom CLI: seed_courses.py for masterclass seeding
│   └── urls.py                       # /courses/ routes and endpoints
├── payments/                         # Stripe Gateway, Invoicing & Billing App
│   ├── models.py                     # PaymentTransaction and Invoice models
│   ├── views.py                      # CreateCheckoutSessionView, PaymentSuccessView, BillingHubView, PDF downloads
│   ├── webhooks.py                   # stripe_webhook with HMAC-SHA256 cryptographic verification
│   ├── services.py                   # Centralized email dispatcher (shahbazbutt22ee@gmail.com) and invoice PDFs
│   └── urls.py                       # /payments/ routes
├── templates/                        # DTL Templates hierarchy (base.html, accounts/, courses/, payments/)
└── static/                           # Static assets (learnix.css, learnix.js, images, loader-icon.png)""",
        "Actual Learnix Project File Hierarchy"))

    story.append(callout("Project Architecture Principle",
        "Every file in Learnix follows the Single Responsibility Principle (SRP). Models declare data contracts; "
        "Views process business logic and authorization; Forms sanitize user inputs; Services handle external APIs and emails; "
        "and Templates handle UI presentation.", "info"))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 2: DJANGO FUNDAMENTALS USED IN MY PROJECT
    # =========================================================================
    story.append(h1("2. Django Fundamentals Used in Learnix"))
    story.append(hr())
    story.append(p(
        "This section deconstructs every foundational Django concept utilized across Learnix. "
        "For each concept, we explain: <b>(1) What it is</b>, <b>(2) Why it is used</b>, <b>(3) Where it exists in Learnix</b>, "
        "<b>(4) How it works under the hood</b>, and <b>(5) Actual project code</b>."
    ))

    fundamentals = [
        ("Django Project (learnix_project/)",
         "The top-level container and administrative configuration package representing the entire website instance.",
         "Provides global coordination, root URL routing, WSGI server connection, and centralized settings.",
         "Directory: learnix_project/ (settings.py, urls.py, wsgi.py, asgi.py).",
         "When python manage.py runserver executes, it loads manage.py, sets DJANGO_SETTINGS_MODULE='learnix_project.settings', and initializes the registry.",
         "# learnix_project/urls.py\nfrom django.urls import path, include\nurlpatterns = [\n    path('admin/', admin.site.urls),\n    path('courses/', include('courses.urls')),\n]"),

        ("Django Apps (accounts, core, courses, payments)",
         "Modular, self-contained Python packages that handle a dedicated domain of business functionality.",
         "Promotes code reusability, decoupled logic, independent testing, and clean maintenance.",
         "Directories: accounts/, core/, courses/, payments/ registered in INSTALLED_APPS in settings.py.",
         "Each app defines its own models, views, URLs, forms, and tests. Django's AppRegistry loads each app during startup.",
         "# learnix_project/settings.py\nINSTALLED_APPS = [\n    'core.apps.CoreConfig',\n    'accounts.apps.AccountsConfig',\n    'courses.apps.CoursesConfig',\n    'payments.apps.PaymentsConfig',\n]"),

        ("settings.py (Configuration Engine)",
         "The central nervous system of the Django project containing all runtime parameters, credentials, and module registrations.",
         "Enables environmental separation between development and production without altering application source code.",
         "File: learnix_project/settings.py.",
         "Uses python-decouple (config()) to read environment variables from .env and cast them to Python types.",
         "# learnix_project/settings.py\nfrom decouple import config, Csv\nDEBUG = config('DEBUG', default=True, cast=bool)\nDATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.postgresql',\n        'NAME': config('DB_NAME', default='learnix_db'),\n    }\n}"),

        ("urls.py & URL Routing",
         "The HTTP request routing table that maps incoming URL paths and regex patterns to specific View callables.",
         "Translates user-facing web paths (e.g. /courses/python-django/) into executed Python functions or class instances.",
         "Root: learnix_project/urls.py; App-level: accounts/urls.py, courses/urls.py, payments/urls.py, core/urls.py.",
         "Django tests request.path against each pattern in order until a match is found, extracting parameters (<slug:slug>).",
         "# courses/urls.py\nurlpatterns = [\n    path('<slug:slug>/', views.CourseDetailView.as_view(), name='course_detail'),\n    path('<slug:slug>/learn/<int:lesson_id>/', views.LessonView.as_view(), name='lesson_view'),\n]"),

        ("views.py & Class-Based Views (CBVs)",
         "The business logic handlers that receive an HttpRequest object and return an HttpResponse object.",
         "Encapsulates domain logic: input validation, database querying, authorization, external Stripe calls, and template rendering.",
         "Files: accounts/views.py, core/views.py, courses/views.py, payments/views.py.",
         "Learnix utilizes CBVs (ListView, DetailView, FormView, TemplateView) which organize HTTP methods into distinct class methods (get, post, form_valid).",
         "# courses/views.py\nclass CourseListView(ListView):\n    model = Course\n    template_name = 'courses/course_list.html'\n    context_object_name = 'courses'\n    def get_queryset(self):\n        return Course.objects.filter(is_published=True).select_related('instructor', 'category')"),

        ("models.py & Database ORM",
         "Python classes that define the structure, constraints, relationships, and behavior of tables in PostgreSQL.",
         "Eliminates raw SQL vulnerabilities, provides database portability, automates schema migrations, and exposes Pythonic queries.",
         "Files: accounts/models.py, courses/models.py, payments/models.py.",
         "Subclasses models.Model. Django maps class attributes to PostgreSQL columns and provides the .objects manager.",
         "# courses/models.py\nclass Course(models.Model):\n    title = models.CharField(max_length=200, db_index=True)\n    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)\n    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)"),

        ("forms.py & ModelForms",
         "Python classes responsible for HTML form generation, data extraction, type conversion, and security validation.",
         "Prevents corrupted or malicious data from reaching the database; standardizes user validation error messages.",
         "File: accounts/forms.py.",
         "Receives request.POST. When form.is_valid() is called, runs clean_<field>() and cross-field clean() methods, populating cleaned_data.",
         "# accounts/forms.py\nclass StudentRegistrationForm(forms.ModelForm):\n    def clean_email(self):\n        email = self.cleaned_data.get('email', '').lower().strip()\n        if User.objects.filter(email=email).exists():\n            raise ValidationError('Account with this email already exists.')\n        return email"),

        ("Templates & DTL (Django Template Language)",
         "HTML documents with embedded DTL syntax ({% if %}, {% for %}, {{ variable }}) rendered on the server.",
         "Separates user interface presentation from backend data operations; enables clean template inheritance.",
         "Directory: templates/ (base.html, accounts/, courses/, payments/, includes/).",
         "Django's template engine parses the document into nodes, evaluates variables against the view's context dictionary, escapes HTML, and outputs raw HTML.",
         "{% extends 'base.html' %}\n{% block content %}\n  <h1>{{ course.title }}</h1>\n  <p>Tuition: ${{ course.price }}</p>\n{% endblock %}"),

        ("Static Files & WhiteNoise",
         "CSS stylesheets, JavaScript files, SVGs, and PNG assets required to style and operate the frontend.",
         "Enables modular asset organization in development and high-performance gzip/brotli caching in production.",
         "Directory: static/ (css/learnix.css, js/learnix.js, images/loader-icon.png); WhiteNoise middleware.",
         "WhiteNoise intercepts static URL requests directly at the WSGI layer, serving pre-compressed files with cache headers.",
         "# learnix_project/settings.py\nSTATIC_URL = '/static/'\nSTATICFILES_DIRS = [BASE_DIR / 'static']\nSTATIC_ROOT = BASE_DIR / 'staticfiles'\nSTATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'"),

        ("manage.py & Administrative CLI",
         "The executable command-line wrapper for managing the Django platform.",
         "Provides commands for running the server, executing migrations, running automated tests, and executing custom commands.",
         "File: manage.py (project root).",
         "Sets DJANGO_SETTINGS_MODULE and invokes django.core.management.execute_from_command_line(sys.argv).",
         "# Terminal execution\npython manage.py runserver 127.0.0.1:8000\npython manage.py test\npython manage.py seed_courses"),

        ("admin.py & Django Admin Portal",
         "The built-in, production-ready administrative back-office interface for inspecting and modifying database records.",
         "Enables faculty, support staff, and administrators to manage courses, verify transactions, and audit certificates.",
         "Files: accounts/admin.py, courses/admin.py, payments/admin.py.",
         "ModelAdmin classes register models with admin.site.register(), configuring search_fields, list_filter, and list_display.",
         "# courses/admin.py\n@admin.register(Course)\nclass CourseAdmin(admin.ModelAdmin):\n    list_display = ('title', 'instructor', 'price', 'level', 'is_published')\n    list_filter = ('level', 'is_published', 'category')\n    search_fields = ('title', 'short_description')"),

        ("apps.py & AppConfig Lifecycle",
         "The configuration class for a Django app that defines metadata and application startup hooks.",
         "Allows connecting model signals, initializing background workers, and registering system checks when Django boots.",
         "Files: accounts/apps.py, core/apps.py, courses/apps.py, payments/apps.py.",
         "Django instantiates AppConfig and executes ready() after all models are loaded.",
         "# accounts/apps.py\nclass AccountsConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'accounts'\n    def ready(self):\n        import accounts.signals"),

        ("Migrations Subsystem",
         "Django's version-control system for the database schema, propagating changes made in models.py to PostgreSQL.",
         "Eliminates manual SQL DDL scripts, prevents human error, and synchronizes team databases safely.",
         "Directories: accounts/migrations/, courses/migrations/, payments/migrations/.",
         "makemigrations inspects model diffs and writes a Python migration file; migrate executes SQL inside a database transaction.",
         "# Terminal commands\npython manage.py makemigrations\npython manage.py migrate"),

        ("PostgreSQL Database Configuration",
         "The robust ACID-compliant relational database engine powering Learnix.",
         "Guarantees relational integrity, foreign key cascading, transactional safety, and high-performance indexing.",
         "Configured in learnix_project/settings.py via DATABASES dictionary.",
         "Django utilizes psycopg (PostgreSQL 3 driver) to execute parameterized SQL and pool connections.",
         "# Database configuration\nDATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.postgresql',\n        'NAME': config('DB_NAME', default='learnix_db'),\n        'USER': config('DB_USER', default='postgres'),\n    }\n}"),

        ("Middleware Pipeline",
         "A framework of hooks into Django's request/response processing, executing globally before and after views.",
         "Applies cross-cutting concerns: security headers, session retrieval, CSRF validation, user authentication, and clickjacking defense.",
         "Configured in MIDDLEWARE list in learnix_project/settings.py.",
         "Each middleware wraps the next layer. During request, it runs process_request(); during response, it runs process_response().",
         "# learnix_project/settings.py\nMIDDLEWARE = [\n    'django.middleware.security.SecurityMiddleware',\n    'django.contrib.sessions.middleware.SessionMiddleware',\n    'django.middleware.csrf.CsrfViewMiddleware',\n    'django.contrib.auth.middleware.AuthenticationMiddleware',\n]"),

        ("Authentication & User Management",
         "Django's cryptographic user identity subsystem.",
         "Handles password hashing (PBKDF2 SHA-256), session verification, permissions, and user state.",
         "Module: django.contrib.auth, used in accounts/views.py and courses/models.py.",
         "Uses authenticate() to verify credentials and login() to attach the user ID to the session store.",
         "# accounts/views.py\nfrom django.contrib.auth import login\nlogin(self.request, user, backend='django.contrib.auth.backends.ModelBackend')"),

        ("Session Management",
         "The mechanism allowing HTTP (a stateless protocol) to remember a user across multiple page requests.",
         "Maintains active logins, pending registration states, and flash notification messages.",
         "django.contrib.sessions, storing signed session data in the django_session PostgreSQL table.",
         "SessionMiddleware reads the 'sessionid' cookie, loads the database session dictionary into request.session, and saves modifications on response.",
         "# accounts/views.py\nself.request.session['otp_user_id'] = user.id\nself.request.session['otp_last_sent'] = timezone.now().timestamp()"),

        ("CSRF (Cross-Site Request Forgery) Defense",
         "A security mechanism that protects authenticated users from malicious websites executing unauthorized POST actions.",
         "Guarantees that state-changing requests (buying a course, marking lesson complete) originate strictly from Learnix.",
         "CsrfViewMiddleware, {% csrf_token %} template tag, and CSRF request headers in fetch() calls.",
         "Generates a cryptographic secret token in a cookie ('csrftoken') and verifies that every POST request submits a matching token in the form or header.",
         "# HTML Form submission\n<form method=\"post\" action=\"{% url 'accounts:signup' %}\">\n  {% csrf_token %}\n  <button type=\"submit\">Sign Up</button>\n</form>"),

        ("Environment Variables & Decoupling",
         "Separating sensitive configuration credentials (passwords, Stripe secret keys, SECRET_KEY) from application code.",
         "Protects keys from being leaked in source control repositories; enables continuous deployment.",
         "File: .env in project root; accessed via python-decouple.",
         "The .env file contains KEY=VALUE pairs ignored by Git (.gitignore). decouple.config('KEY') reads them at runtime.",
         "# learnix_project/settings.py\nSTRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_placeholder')\nEMAIL_HOST_USER = config('EMAIL_HOST_USER', default='shahbazbutt22ee@gmail.com')")
    ]

    for title, what, why, where, how, code in fundamentals:
        story.append(h2(f"2.{fundamentals.index((title, what, why, where, how, code)) + 1} {title}"))
        story.append(p(f"<b>1. What it is:</b> {what}"))
        story.append(p(f"<b>2. Why it is used:</b> {why}"))
        story.append(p(f"<b>3. Where it exists in Learnix:</b> {where}"))
        story.append(p(f"<b>4. How it works under the hood:</b> {how}"))
        story.append(code_box(code, f"Learnix Code Implementation — {title}"))
        story.append(spacer(4))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: DJANGO APPS
    # =========================================================================
    story.append(h1("3. Deep Dive into Learnix Django Apps"))
    story.append(hr())
    story.append(p(
        "Learnix is partitioned into four decoupled applications: <b>accounts</b>, <b>core</b>, <b>courses</b>, and <b>payments</b>. "
        "Each application maintains a single, distinct business responsibility with clean interface contracts."
    ))

    apps_data = [
        ("accounts",
         "Identity, Two-Phase Cryptographic OTP Authentication, and Student Profile Portfolio",
         "The accounts app owns the complete user lifecycle: initial registration, issuing time-bounded 6-digit cryptographic OTPs via email, enforcing brute-force attempt limits, credentials authentication, session cookies, profile management, and access mixins.",
         [
             ("models.py", "Defines UserProfile (avatar, bio, headline, currency) and EmailOTP (6-digit code, 10-minute validity, attempt ceiling)."),
             ("forms.py", "Defines StudentRegistrationForm (email uniqueness, password rules), OTPVerificationForm, and UserLoginForm."),
             ("views.py", "Houses SignUpView, VerifyOTPView, ResendOTPView (60s rate limit), UserLoginView, UserLogoutView, ProfileView."),
             ("mixins.py", "EnrolledCourseRequiredMixin for enforcing course enrollment authorization on class-based views."),
             ("signals.py", "Auto-provisions a UserProfile instance whenever a new User record is created.")
         ],
         [
             ("/accounts/signup/", "SignUpView", "Validates student input, creates inactive user, generates cryptographic OTP, sends email."),
             ("/accounts/verify-otp/", "VerifyOTPView", "Validates 6-digit OTP, checks expiry/attempts, activates user, creates authenticated session."),
             ("/accounts/resend-otp/", "ResendOTPView", "Issues fresh OTP subject to strict 60-second cooldown rate limit."),
             ("/accounts/login/", "UserLoginView", "Authenticates credentials and establishes session cookie."),
             ("/accounts/logout/", "UserLogoutView", "Flushes active session and redirects to home page."),
             ("/accounts/profile/", "ProfileView", "Renders student profile portfolio with active enrollment counts.")
         ],
         "courses (checks user enrollments), payments (dispatches welcome email)."),

        ("core",
         "Platform Showcase, Global Marketing, and Security Exception Interceptors",
         "The core app manages the platform's public storefront, marketing pages, global brand context processors, and custom HTTP error handlers.",
         [
             ("views.py", "HomeView (bento grid, stats), AboutView, custom_page_not_found_view (404), custom_server_error_view (500), custom_permission_denied_view (403)."),
             ("context_processors.py", "site_context exposing SITE_NAME and DEBUG globally to all templates."),
             ("exceptions.py", "Defines LearnixBaseException hierarchy (PaymentVerificationFailedException, CourseAccessDeniedException, OTPExpiredException).")
         ],
         [
             ("/", "HomeView", "Renders interactive Bento grid, platform metrics, featured tracks, and CTA buttons."),
             ("/about/", "AboutView", "Renders curriculum philosophy, faculty credentials, and institutional benchmarks.")
         ],
         "courses (queries published courses for bento showcase)."),

        ("courses",
         "Curriculum Taxonomy, Video Lesson Streaming, Progress Telemetry & Certifications",
         "The courses app is the academic core of Learnix. It orchestrates categories, courses, curriculum modules, lessons, student enrollment records, granular lesson completion tracking, and cryptographically signed PDF certificates.",
         [
             ("models.py", "CourseCategory, Course, CourseModule, Lesson, Enrollment, LessonProgress, Certificate."),
             ("views.py", "CourseListView, CourseDetailView, StudentDashboardView, LessonView, MarkCompleteView, CertificateDetailView, APIs."),
             ("decorators.py", "@enrolled_required view decorator checking active enrollment before lesson streaming."),
             ("services.py", "generate_certificate_pdf() compiling landscape certificates with SHA-256 ledger hashes via xhtml2pdf."),
             ("templatetags/course_extras.py", "Template filters: format_duration, calculate_progress_badge, times, two_digits, preview_count.")
         ],
         [
             ("/courses/", "CourseListView", "Interactive course catalog with category, level, and search filters."),
             ("/courses/<slug>/", "CourseDetailView", "Masterclass detail, interactive syllabus, instructor pill, enroll CTA."),
             ("/courses/<slug>/learn/<lesson_id>/", "LessonView", "Interactive streaming lesson player with sequential module navigation."),
             ("/courses/lesson/<lesson_id>/complete/", "MarkCompleteView", "AJAX API toggling lesson completion and recalculating progress."),
             ("/courses/api/search/", "course_search_api", "JSON endpoint powering live header search modal."),
             ("/courses/<slug>/preview/<lesson_id>/", "lesson_preview_api", "JSON endpoint for free streaming preview modal."),
             ("/courses/certificates/<cert_id>/", "CertificateDetailView", "Public verification portal for verifiable certificates."),
             ("/courses/certificates/<cert_id>/download/", "DownloadCertificatePDFView", "High-resolution PDF certificate stream."),
             ("/courses/instructor/studio/", "InstructorStudioView", "Faculty metrics studio, student counts, and revenue tracking."),
             ("/dashboard/", "StudentDashboardView", "Student learning hub showing progress cards and velocity metrics.")
         ],
         "accounts (User model, EnrolledCourseRequiredMixin), payments (Invoice & transaction links)."),

        ("payments",
         "Stripe Hosted Checkout Integration, Invoicing, Webhooks & Email Dispatcher",
         "The payments app handles tuition processing through Stripe's official hosted Checkout page, manages financial transaction records, generates formal PDF tax invoices and receipts, and receives asynchronous Stripe webhook events.",
         [
             ("models.py", "PaymentTransaction (status, order_number, checkout_session_id) and Invoice (tax invoice, invoice_number)."),
             ("views.py", "CreateCheckoutSessionView (Stripe session creation), PaymentSuccessView, PaymentCancelView, BillingHubView, PDF downloads."),
             ("webhooks.py", "stripe_webhook verifying HMAC-SHA256 signatures and fulfilling enrollments atomically."),
             ("services.py", "send_order_confirmation_email, send_registration_welcome_email, generate_invoice_pdf, generate_receipt_pdf.")
         ],
         [
             ("/payments/checkout/<slug>/", "CreateCheckoutSessionView", "Initiates Stripe Hosted Checkout session and redirects to checkout.stripe.com."),
             ("/payments/success/", "PaymentSuccessView", "Renders celebratory enrollment onboarding page with launch CTA."),
             ("/payments/cancel/", "PaymentCancelView", "Renders aborted checkout notice with retry options."),
             ("/payments/billing/", "BillingHubView", "Student financial hub: invoices, payment history, 1-click receipts."),
             ("/payments/invoice/<inv_num>/download/", "DownloadInvoicePDFView", "Streams formal PDF tax invoice."),
             ("/payments/receipt/<order_num>/download/", "DownloadReceiptPDFView", "Streams formal PDF Stripe payment receipt."),
             ("/payments/billing/export-all/", "ExportAllInvoicesZipView", "Compiles all invoices into a .ZIP archive."),
             ("/payments/webhook/stripe/", "stripe_webhook", "Receives asynchronous Stripe events (checkout.session.completed).")
         ],
         "courses (Course, Enrollment models), accounts (User model).")
    ]

    for app_name, summary, resp, files, routes, deps in apps_data:
        story.append(h2(f"3.{apps_data.index((app_name, summary, resp, files, routes, deps)) + 1} App: {app_name}"))
        story.append(p(f"<b>Responsibility:</b> {summary}"))
        story.append(p(resp))
        story.append(h3("Key Files in this App:"))
        for fname, fdesc in files:
            story.append(bullet(f"<b>{fname}:</b> {fdesc}"))
        story.append(h3("URL Routes & Handlers:"))
        table_rows = [["URL Path", "View Handler", "Description"]]
        for path_u, view_u, desc_u in routes:
            table_rows.append([path_u, view_u, desc_u])
        story.append(create_table(table_rows, [140, 120, 280]))
        story.append(p(f"<b>Dependencies on other apps:</b> {deps}"))
        story.append(spacer(6))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 4: MODELS AND DATABASE
    # =========================================================================
    story.append(h1("4. Models & Database Architecture"))
    story.append(hr())
    story.append(p(
        "Learnix enforces relational database design with 11 models mapped to PostgreSQL 15+. "
        "Every table defines explicit primary keys, data constraints, foreign key referential integrity, "
        "and optimized indexes for lightning-fast queries."
    ))

    story.append(h2("4.1 Relational Entity-Relationship (ER) Overview"))
    story.append(create_table([
        ["Parent Model", "Relationship", "Child Model", "on_delete Rule", "related_name"],
        ["auth.User", "1-to-1", "accounts.UserProfile", "CASCADE", "profile"],
        ["auth.User", "1-to-Many", "accounts.EmailOTP", "CASCADE", "email_otps"],
        ["auth.User", "1-to-Many", "courses.Course (instructor)", "CASCADE", "authored_courses"],
        ["courses.CourseCategory", "1-to-Many", "courses.Course", "SET_NULL", "courses"],
        ["courses.Course", "1-to-Many", "courses.CourseModule", "CASCADE", "modules"],
        ["courses.CourseModule", "1-to-Many", "courses.Lesson", "CASCADE", "lessons"],
        ["auth.User", "1-to-Many", "courses.Enrollment", "CASCADE", "enrollments"],
        ["courses.Course", "1-to-Many", "courses.Enrollment", "CASCADE", "enrollments"],
        ["courses.Enrollment", "1-to-1", "courses.Certificate", "CASCADE", "certificate"],
        ["auth.User & Lesson", "1-to-Many", "courses.LessonProgress", "CASCADE", "progresses / lesson_progresses"],
        ["auth.User & Course", "1-to-Many", "payments.PaymentTransaction", "CASCADE", "payments"],
        ["payments.PaymentTransaction", "1-to-1", "payments.Invoice", "CASCADE", "invoice"]
    ], [110, 60, 140, 90, 140]))

    story.append(h2("4.2 Exhaustive Model Definitions"))

    models_list = [
        ("UserProfile (accounts/models.py)",
         "Extends Django's User model with portfolio metadata, headline, and bio.",
         [
             ("user", "OneToOneField(settings.AUTH_USER_MODEL)", "CASCADE", "Primary relationship to auth_user table. related_name='profile'."),
             ("avatar", "ImageField(upload_to='avatars/')", "null=True, blank=True", "Student avatar image stored in MEDIA_ROOT/avatars/."),
             ("bio", "TextField()", "blank=True, default=''", "Biographical statement displayed on profile."),
             ("headline", "CharField(max_length=255)", "blank=True, default=''", "Professional title e.g. 'Staff Architect · AI Fellow'."),
             ("phone_number", "CharField(max_length=30)", "blank=True, default=''", "Optional contact number."),
             ("preferred_currency", "CharField(max_length=10)", "default='USD'", "Currency preference for billing display."),
             ("created_at / updated_at", "DateTimeField", "auto_now_add=True / auto_now=True", "Audit timestamps.")
         ],
         "__str__: Returns f\"{self.user.username}'s Profile\""),

        ("EmailOTP (accounts/models.py)",
         "Cryptographic 6-digit OTP for two-phase email verification with rate-limiting.",
         [
             ("user", "ForeignKey(settings.AUTH_USER_MODEL)", "CASCADE", "Target student awaiting account verification."),
             ("otp_code", "CharField(max_length=6, db_index=True)", "Indexed", "Cryptographically generated 6-digit numeric string."),
             ("created_at", "DateTimeField(auto_now_add=True)", "Default now", "Creation timestamp."),
             ("expires_at", "DateTimeField()", "db_index=True", "Timestamp at which OTP expires (created_at + 10 minutes)."),
             ("is_verified", "BooleanField()", "default=False", "Set to True upon successful verification."),
             ("attempts_count", "PositiveSmallIntegerField()", "default=0", "Failed attempts counter; throttles at MAX_ATTEMPTS=5.")
         ],
         "Methods: create_for_user(user) generates secure 6-digit code via secrets.choice; is_expired property; is_locked property."),

        ("CourseCategory (courses/models.py)",
         "Categorizes technical domains (e.g. AI Swarms, Cloud DevOps, System Design).",
         [
             ("name", "CharField(max_length=100)", "unique=True", "Human-readable category name."),
             ("slug", "SlugField(max_length=120)", "unique=True", "URL slug auto-generated via slugify()."),
             ("icon", "CharField(max_length=50)", "default='school'", "Google Material Symbols icon identifier."),
             ("description", "TextField()", "blank=True, default=''", "Curriculum domain description.")
         ],
         "Meta: ordering=['name'], verbose_name_plural='Course Categories'."),

        ("Course (courses/models.py)",
         "Core curriculum entity defining masterclass architecture tracks.",
         [
             ("title", "CharField(max_length=200)", "db_index=True", "Full masterclass title."),
             ("slug", "SlugField(max_length=220)", "unique=True, db_index=True", "URL identifier used across routes."),
             ("instructor", "ForeignKey(AUTH_USER_MODEL)", "CASCADE", "Faculty instructor. related_name='authored_courses'."),
             ("category", "ForeignKey(CourseCategory)", "SET_NULL, null=True, blank=True", "Taxonomy link. related_name='courses'."),
             ("short_description", "TextField()", "Required", "1-2 sentence overview for catalog cards."),
             ("full_description", "TextField()", "blank=True, default=''", "Comprehensive syllabus and learning outcomes."),
             ("price", "DecimalField(max_digits=8, decimal_places=2)", "default=0.00", "Tuition cost. If 0.00, course is free."),
             ("level", "CharField(max_length=15)", "choices=(BEGINNER, INTERMEDIATE, ADVANCED)", "Skill level."),
             ("thumbnail / thumbnail_url", "ImageField / URLField", "Optional", "Primary image and CDN demo fallback."),
             ("rating / reviews_count", "DecimalField / PositiveIntegerField", "default=4.90 / 120", "Social proof telemetry."),
             ("is_published", "BooleanField()", "default=False", "Publication flag gating student access.")
         ],
         "Properties: total_lessons_count, is_free, total_duration_seconds, total_duration_hours_display, get_thumbnail_url."),

        ("CourseModule (courses/models.py)",
         "Curriculum unit or chapter organizing lessons sequentially.",
         [
             ("course", "ForeignKey(Course)", "CASCADE", "Parent course. related_name='modules'."),
             ("title", "CharField(max_length=200)", "Required", "Chapter title e.g. 'Foundations of Agentic Systems'."),
             ("order_number", "PositiveIntegerField()", "default=1", "Sequential ordering position in syllabus.")
         ],
         "Meta: ordering=['order_number']. Property: total_duration_seconds."),

        ("Lesson (courses/models.py)",
         "Individual learning unit containing interactive video player streams and rich text.",
         [
             ("module", "ForeignKey(CourseModule)", "CASCADE", "Parent chapter. related_name='lessons'."),
             ("title", "CharField(max_length=200)", "Required", "Lesson title."),
             ("video_url", "CharField(max_length=500)", "blank=True, default=''", "Direct stream MP4 or embed link."),
             ("content", "TextField()", "blank=True, default=''", "Markdown notes and architecture blueprints."),
             ("duration_seconds", "PositiveIntegerField()", "default=600", "Duration in seconds (e.g. 860 for 14m 20s)."),
             ("order_number", "PositiveIntegerField()", "default=1", "Sequential order within the module."),
             ("is_preview", "BooleanField()", "default=False", "If True, unenrolled guests can stream for free.")
         ],
         "Property: formatted_duration (returns mm:ss format e.g. '14:20')."),

        ("Enrollment (courses/models.py)",
         "Active student enrollment record tracking completion progress.",
         [
             ("user", "ForeignKey(AUTH_USER_MODEL)", "CASCADE", "Enrolled student. related_name='enrollments'."),
             ("course", "ForeignKey(Course)", "CASCADE", "Target course. related_name='enrollments'."),
             ("enrolled_at", "DateTimeField(auto_now_add=True)", "Timestamp", "Enrollment initiation timestamp."),
             ("is_active", "BooleanField()", "default=True, db_index=True", "Access permission toggle."),
             ("progress_percent", "DecimalField(max_digits=5, decimal_places=2)", "default=0.00", "0.00% to 100.00% completion rate.")
         ],
         "Methods: calculate_progress() (queries LessonProgress, calculates %, triggers Certificate at 100%); next_uncompleted_lesson."),

        ("LessonProgress (courses/models.py)",
         "Granular completion and telemetry tracking per lesson per student.",
         [
             ("user", "ForeignKey(AUTH_USER_MODEL)", "CASCADE", "Student executing the lesson."),
             ("lesson", "ForeignKey(Lesson)", "CASCADE", "Target lesson."),
             ("is_completed", "BooleanField()", "default=False", "Marked complete flag."),
             ("completed_at", "DateTimeField()", "null=True, blank=True", "Timestamp when finished."),
             ("last_accessed_at", "DateTimeField(auto_now=True)", "Timestamp", "Last playback interaction timestamp.")
         ],
         "Meta: unique_together=('user', 'lesson')."),

        ("Certificate (courses/models.py)",
         "Cryptographically verifiable completion certificate with SHA-256 ledger hash.",
         [
             ("user", "ForeignKey(AUTH_USER_MODEL)", "CASCADE", "Awardee student."),
             ("course", "ForeignKey(Course)", "CASCADE", "Completed masterclass."),
             ("enrollment", "OneToOneField(Enrollment)", "CASCADE", "Originating 100% completed enrollment record."),
             ("certificate_id", "CharField(max_length=64)", "unique=True, db_index=True", "Human-readable code e.g. LRN-98214-X."),
             ("verification_hash", "CharField(max_length=64)", "Required", "SHA-256 cryptographic verification ledger hash."),
             ("ceus", "DecimalField(max_digits=4, decimal_places=1)", "default=4.5", "Continuing Education Units awarded."),
             ("issued_at", "DateTimeField(auto_now_add=True)", "Timestamp", "Issuance date."),
             ("pdf_file", "FileField(upload_to='certificates/')", "null=True, blank=True", "Pre-generated PDF file.")
         ],
         "Methods: generate_certificate_id(); compute_verification_hash(user_id, course_slug, timestamp); issue_for_enrollment()."),

        ("PaymentTransaction (payments/models.py)",
         "Records financial tuition checkout transactions via Stripe.",
         [
             ("user", "ForeignKey(AUTH_USER_MODEL)", "CASCADE", "Purchasing student."),
             ("course", "ForeignKey('courses.Course')", "CASCADE", "Target masterclass."),
             ("order_number", "CharField(max_length=50)", "unique=True, db_index=True", "Order reference e.g. LRN-84920."),
             ("stripe_checkout_session_id", "CharField(max_length=255)", "unique=True, null=True, blank=True", "Stripe session cs_test_..."),
             ("stripe_payment_intent_id", "CharField(max_length=255)", "null=True, blank=True", "Stripe payment intent pi_..."),
             ("amount", "DecimalField(max_digits=8, decimal_places=2)", "Required", "Tuition charge amount."),
             ("currency", "CharField(max_length=10)", "default='USD'", "Currency code."),
             ("status", "CharField(max_length=20)", "choices=(PENDING, COMPLETED, FAILED, REFUNDED)", "Current order status."),
             ("created_at", "DateTimeField(auto_now_add=True)", "Timestamp", "Initiation timestamp.")
         ],
         "Method: generate_order_number() (returns e.g. LRN-A4B8C1)."),

        ("Invoice (payments/models.py)",
         "Formal academic tax invoice generated for completed tuition payments.",
         [
             ("transaction", "OneToOneField(PaymentTransaction)", "CASCADE", "Associated financial transaction. related_name='invoice'."),
             ("invoice_number", "CharField(max_length=50)", "unique=True, db_index=True", "Tax invoice number e.g. INV-2026-00481."),
             ("billing_name", "CharField(max_length=200)", "Required", "Legal billing entity or student name."),
             ("billing_email", "EmailField()", "Required", "Billing notification email address."),
             ("subtotal / tax_amount / total_amount", "DecimalField(max_digits=8, decimal_places=2)", "Required", "Itemized pricing."),
             ("issued_at", "DateTimeField(auto_now_add=True)", "Timestamp", "Issuance date."),
             ("pdf_file", "FileField(upload_to='invoices/')", "null=True, blank=True", "Pre-generated PDF file.")
         ],
         "Method: generate_invoice_number() (returns e.g. INV-2026-XXXXX).")
    ]

    for m_title, m_desc, fields, extra in models_list:
        story.append(h2(f"4.{models_list.index((m_title, m_desc, fields, extra)) + 2} Model: {m_title}"))
        story.append(p(m_desc))
        f_rows = [["Field Name", "Field Type", "Constraints / Defaults", "Description & Role"]]
        for f_name, f_type, f_con, f_desc in fields:
            f_rows.append([f_name, f_type, f_con, f_desc])
        story.append(create_table(f_rows, [110, 130, 130, 170]))
        story.append(p(f"<b>Model Methods & Logic:</b> {extra}"))
        story.append(spacer(4))

    story.append(h2("4.13 ORM Methods & QuerySet Evaluation Used in Learnix"))
    story.append(p(
        "Learnix interacts with PostgreSQL exclusively through Django's Object-Relational Mapping (ORM). "
        "The following QuerySet methods are actively used:"
    ))
    story.append(bullet("<b>filter(**kwargs):</b> Returns a new QuerySet containing objects matching parameters. Lazy; doesn't hit DB immediately. Example: Course.objects.filter(is_published=True)."))
    story.append(bullet("<b>get(**kwargs):</b> Returns exactly one matching object. Raises DoesNotExist if not found, or MultipleObjectsReturned if more than 1 found. Example: User.objects.get(id=user_id)."))
    story.append(bullet("<b>create(**kwargs):</b> Instantiates and executes an INSERT into PostgreSQL in one step. Example: PaymentTransaction.objects.create(...)."))
    story.append(bullet("<b>get_or_create(defaults, **kwargs):</b> Atomic lookup; if not found, creates the object with defaults. Used extensively to prevent race conditions during enrollments."))
    story.append(bullet("<b>exists():</b> Executes an optimized 'SELECT (1) AS a FROM table LIMIT 1' in SQL, returning True or False without loading record data into Python memory."))
    story.append(bullet("<b>count():</b> Executes 'SELECT COUNT(*) FROM table' in PostgreSQL, computing the count inside the database engine."))
    story.append(bullet("<b>select_related(*fields):</b> Performs an SQL INNER JOIN for ForeignKey and OneToOneField relationships, avoiding the classic 'N+1 query problem'."))
    story.append(bullet("<b>prefetch_related(*fields):</b> Executes a separate optimized SQL lookup and joins in Python memory for Many-to-Many and reverse ForeignKey relationships (e.g. course.modules.prefetch_related('lessons'))."))
    story.append(bullet("<b>transaction.atomic():</b> Context manager opening a database transaction block (BEGIN...COMMIT/ROLLBACK). If an exception occurs, all DB writes inside the block are cleanly rolled back."))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 5: MIGRATIONS
    # =========================================================================
    story.append(h1("5. Migrations from A to Z"))
    story.append(hr())
    story.append(p(
        "Migrations are Django's way of propagating changes made to Python models into the PostgreSQL database schema. "
        "Instead of writing raw, error-prone SQL DDL scripts by hand, Django automatically tracks model evolution, "
        "computes schema differences, and executes migrations inside atomic transactions."
    ))

    story.append(h2("5.1 How the Migration Engine Works"))
    story.append(p("The migration lifecycle operates in three clear phases:"))
    story.append(bullet("<b>1. Model Inspection (makemigrations):</b> Django compares the current state of models.py against the recorded state of the latest migration file in the app's migrations/ folder. It writes a new Python file detailing operations (CreateModel, AddField, AlterField, AddIndex)."))
    story.append(bullet("<b>2. Schema Execution (migrate):</b> Django inspects the special <b>django_migrations</b> table in PostgreSQL to find unapplied migrations. For each pending migration, it translates Python operations into PostgreSQL DDL (CREATE TABLE, ALTER TABLE, CREATE INDEX) and executes them in an atomic transaction."))
    story.append(bullet("<b>3. State Recording:</b> Upon successful execution, a new row is inserted into <b>django_migrations</b> (app, name, applied_timestamp). If an error occurs, PostgreSQL rolls back the entire transaction."))

    story.append(h2("5.2 Actual Migrations in Learnix"))
    story.append(create_table([
        ["App", "Migration File", "Dependencies", "Key Operations & Schema Alterations"],
        ["accounts", "0001_initial.py", "auth.User", "CreateModel: UserProfile (OneToOne to User); CreateModel: EmailOTP with composite indexes on (user, otp_code) and (expires_at)."],
        ["courses", "0001_initial.py", "auth.User", "CreateModel: CourseCategory, Course, CourseModule, Lesson. AddIndex on course slug, price, and level."],
        ["courses", "0002_alter_course_thumbnail_url.py", "0001_initial", "AlterField: Expanded Course.thumbnail_url max_length to 500 characters."],
        ["courses", "0003_enrollment_lessonprogress.py", "0002_alter...", "CreateModel: Enrollment (unique_together user/course); CreateModel: LessonProgress (unique_together user/lesson)."],
        ["courses", "0004_certificate.py", "0003_enrollment...", "CreateModel: Certificate with OneToOneField to Enrollment, SHA-256 verification hash, and indexes."],
        ["payments", "0001_initial.py", "courses.0003_enrollment...", "CreateModel: PaymentTransaction (order_number index); CreateModel: Invoice (OneToOne to transaction)."]
    ], [65, 115, 100, 260]))

    story.append(h2("5.3 Deconstructing a Real Learnix Migration File"))
    story.append(p(
        "Below is an excerpt from <b>courses/migrations/0003_enrollment_lessonprogress.py</b> showing how Django structures operations:"
    ))
    story.append(code_box("""# courses/migrations/0003_enrollment_lessonprogress.py
class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0002_alter_course_thumbnail_url'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('progress_percent', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('course', models.ForeignKey(on_delete=models.CASCADE, related_name='enrollments', to='courses.course')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='enrollments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-enrolled_at'],
                'unique_together': {('user', 'course')},
            },
        ),
    ]""", "Actual Migration Operation: CreateModel for Enrollment"))

    story.append(callout("Viva Question: What happens when you run 'python manage.py migrate'?",
        "Django connects to PostgreSQL, acquires an exclusive advisory lock on the database, inspects the "
        "'django_migrations' table, calculates the dependency graph of all unapplied migrations across all installed apps, "
        "and runs the SQL DDL inside an atomic transaction. If any step fails, the entire transaction is rolled back, "
        "leaving the database in a consistent state.", "viva"))

    story.append(PageBreak())
    return story
