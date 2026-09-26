"""
Sections 23, 24, and 25 for Learnix Technical Documentation:
23. How to Explain This Project in an Evaluation / Viva (18 Domains)
24. Code Explanation Rules & Live Presentation Strategies
25. Final Quick Revision (7 Cheat Sheets + Top 50 Viva Questions & Model Answers)
"""

import html
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from .doc_builder import (
    p, bullet, h1, h2, h3, spacer, hr, code_box, callout, viva_qa, create_table,
    style_body, style_body_bold, style_callout_body, PRIMARY, PRIMARY_DARK, ACCENT_CYAN,
    DARK_SLATE, BORDER_LIGHT, BG_CODE
)

# ==============================================================================
# SECTION 23: HOW TO EXPLAIN THIS PROJECT IN AN EVALUATION / VIVA
# ==============================================================================

def build_section_23():
    story = []
    story.append(h1("23. How to Explain This Project in an Evaluation / Viva"))
    story.append(hr())
    story.append(p(
        "During a technical evaluation or viva voce, examiners assess not just whether your code works, "
        "but whether you fundamentally understand <b>why</b> architectural decisions were made, <b>how</b> "
        "Django handles operations under the hood, and <b>where</b> specific business logic lives in your codebase. "
        "Below are the <b>18 core technical domains</b> of the Learnix platform, structured with concise definitions, "
        "project rationale, internal mechanisms, exact code locations, and model answers for likely questions."
    ))
    story.append(spacer(6))

    domains = [
        # Domain 1
        {
            "num": 1,
            "title": "Django Architecture & the MTV Design Pattern",
            "what": "A architectural design pattern that separates concerns into Model (database layer & business rules), Template (presentation & HTML rendering), and View (request handler & orchestration logic), managed by Django's URL dispatcher.",
            "why": "Eliminates code tangling, enables modular maintenance across 4 distinct apps, and allows independent evolution of database schemas, UI templates, and business logic.",
            "how": "HTTP request enters WSGI handler -> URLconf matches regex/path -> View receives HttpRequest -> View queries Model via ORM -> ORM returns QuerySet -> View passes context dictionary to Template engine -> Engine renders HTML -> View returns HttpResponse.",
            "where": "Master router in config/urls.py; App views across accounts/views.py, courses/views.py, payments/views.py; Templates in templates/ directory.",
            "q": "Why is Django called MTV instead of MVC, and what is the Controller in Django?",
            "ans": "Django uses MTV (Model-Template-View). The Model is data, the Template is presentation (View in MVC), and the View is business logic. The Controller role is handled by the Django framework itself via the URL dispatcher and request handler which routes requests to the appropriate view."
        },
        # Domain 2
        {
            "num": 2,
            "title": "Models & Relational Schema Design",
            "what": "Python classes inheriting from django.db.models.Model that declare database tables, columns, constraints, relationships, and model-level business methods as single sources of truth.",
            "why": "Avoids raw SQL writing, ensures automated database portability (PostgreSQL/SQLite), enforces relational integrity (ForeignKeys, cascading rules), and provides an object-oriented API for records.",
            "how": "Metaclass ModelBase intercepts class definition, registers fields, and prepares table schema mappings. When instantiated, model objects represent individual rows in the corresponding SQL table.",
            "where": "accounts/models.py (UserProfile, EmailOTP), courses/models.py (Category, Course, Module, Lesson, Enrollment, LessonProgress, Review, Certificate), payments/models.py (PaymentTransaction, Invoice).",
            "q": "How does Learnix prevent duplicate enrollments or duplicate progress tracking in the database?",
            "ans": "Using unique_together constraints and UniqueConstraint in model Meta classes: Enrollment enforces unique_together = ('user', 'course'); LessonProgress enforces unique_together = ('user', 'lesson'); and EmailOTP enforces unique_together = ('user', 'code'). This guarantees database-level integrity against race conditions."
        },
        # Domain 3
        {
            "num": 3,
            "title": "Django ORM & Lazy Query Evaluation",
            "what": "An Object-Relational Mapper that maps relational database tables to Python objects and translates Python query syntax into optimized SQL statements.",
            "why": "Protects against SQL injection via parameterized queries, eliminates vendor-specific SQL lock-in, and offers high-level composition of complex queries with filter chaining.",
            "how": "QuerySets are lazy: creating a QuerySet does not touch the database. The database is queried only when the QuerySet is evaluated (iteration, slicing with step, len(), list(), or bool evaluation).",
            "where": "Throughout views: Course.objects.filter(is_published=True).select_related('instructor', 'category') in courses/views.py; Enrollment.objects.get_or_create() in payments/views.py.",
            "q": "What is the N+1 query problem and how did you resolve it in Learnix?",
            "ans": "The N+1 problem occurs when fetching a list of N records executes 1 initial query, and then accessing a related foreign key on each record triggers N additional queries. In Learnix, we solve this using .select_related('category', 'instructor') for ForeignKey joins (SQL INNER/LEFT JOIN) and .prefetch_related() for many-to-many relationships."
        },
        # Domain 4
        {
            "num": 4,
            "title": "Migrations & Schema Evolution",
            "what": "Django's mechanism for propagating changes made to Python models (adding fields, altering constraints) into the physical database schema in a version-controlled, reversible manner.",
            "why": "Allows database schemas to evolve safely across development, staging, and production environments without manual, error-prone ALTER TABLE scripts.",
            "how": "makemigrations inspects model state, compares it to migration history, and writes Python migration operations (CreateModel, AddField). migrate checks django_migrations table and executes unapplied migrations inside atomic transactions.",
            "where": "accounts/migrations/ (0001_initial to 0002_emailotp), courses/migrations/ (0001_initial to 0004_certificate), payments/migrations/ (0001_initial to 0002_invoice).",
            "q": "What happens if a migration fails halfway through execution?",
            "ans": "On databases supporting DDL transactions (like PostgreSQL), Django wraps migrations in an atomic transaction; if an error occurs, the entire schema change rolls back cleanly. On SQLite/MySQL (which do not support transactional DDL), manual schema cleanup is required."
        },
        # Domain 5
        {
            "num": 5,
            "title": "Views Architecture: CBVs vs FBVs & Mixins",
            "what": "Class-Based Views (CBVs) encapsulate HTTP method handling into object-oriented classes with reusable mixins; Function-Based Views (FBVs) are explicit Python functions taking a request and returning a response.",
            "why": "Learnix uses CBVs for standard CRUD flows (CourseListView, LessonView) to eliminate boilerplate, and FBVs for specialized AJAX endpoints (course_search_api, lesson_preview_api) for lightweight transparency.",
            "how": "CBV dispatch() inspects request.method (GET, POST) and delegates to corresponding class methods (get(), post()). Mixins inject reusable behaviors (e.g. LoginRequiredMixin, EnrolledCourseRequiredMixin) via Python multiple inheritance.",
            "where": "CBVs in courses/views.py (CourseListView, CourseDetailView, LessonView); FBVs in courses/views.py (course_search_api, lesson_preview_api) and payments/webhooks.py (stripe_webhook).",
            "q": "What is the method resolution order (MRO) in Python mixins, and why does EnrolledCourseRequiredMixin come first?",
            "ans": "Python resolves inheritance from left to right using the C3 linearization algorithm. EnrolledCourseRequiredMixin must be listed before DetailView so its dispatch() method executes first, checking enrollment permissions before the view attempts to load or render the lesson."
        },
        # Domain 6
        {
            "num": 6,
            "title": "URLs, Routing & Reverse Resolution",
            "what": "The routing engine that maps incoming HTTP request URL paths to corresponding view functions or CBVs using path() and re_path(), with named URL reversing via reverse() and {% url %}.",
            "why": "Decouples application URL structure from internal Python view names; if a URL path changes, templates and view redirects remain unaffected as long as the route name is preserved.",
            "how": "config/urls.py delegates route namespaces (accounts:, courses:, payments:) to app-level urls.py files. Path converters (<slug:slug>, <int:lesson_id>) parse path parameters and pass them as keyword arguments (kwargs) to the view.",
            "where": "config/urls.py, accounts/urls.py, courses/urls.py, payments/urls.py.",
            "q": "Why do you use reverse_lazy in Class-Based Views instead of reverse?",
            "ans": "reverse_lazy evaluates the URL route lazily when the view attribute is accessed at runtime, rather than when the module is imported. Using standard reverse at class definition time fails because the URLconf is not yet fully loaded when Python imports view classes."
        },
        # Domain 7
        {
            "num": 7,
            "title": "Forms, Input Cleaning & Security Validation",
            "what": "Django's Form and ModelForm classes that handle HTML form generation, server-side data extraction, CSRF protection, and two-tier data validation (field-level and cross-field cleaning).",
            "why": "Prevents malformed, malicious, or duplicate input from ever reaching the database or business logic layer. Provides unified error messaging back to user templates.",
            "how": "Calling form.is_valid() executes: 1. Field validation (type conversion, required checks, max_length); 2. clean_<fieldname>() methods for single-field logic; 3. clean() for cross-field verification. Cleaned data is stored in form.cleaned_data.",
            "where": "accounts/forms.py: StudentRegistrationForm (validates unique email & matching passwords), OTPVerificationForm (validates 6-digit regex), UserLoginForm.",
            "q": "How does clean_email() in StudentRegistrationForm prevent duplicate accounts?",
            "ans": "It normalizes the email to lowercase and executes User.objects.filter(email__iexact=email).exists(). If a record is found, it raises forms.ValidationError('A user with this email already exists.'), preventing the registration from proceeding."
        },
        # Domain 8
        {
            "num": 8,
            "title": "User Authentication & Session Lifecycle",
            "what": "Django's built-in session-based authentication subsystem that manages user identity, password hashing (PBKDF2), session cookies, and login/logout state.",
            "why": "Provides industry-standard, cryptographically secure credential management without reinventing authentication from scratch.",
            "how": "authenticate() verifies credentials against hashed passwords in auth_user. login() assigns session key, stores it in django_session table, and attaches a signed sessionid cookie in HTTP response headers. AuthenticationMiddleware inspects the cookie on every subsequent request and attaches the user instance to request.user.",
            "where": "accounts/views.py (LoginView, LogoutView), config/settings.py (AUTH_PASSWORD_VALIDATORS, SESSION_COOKIE_AGE).",
            "q": "How does Django store user passwords in the database?",
            "ans": "Django never stores plaintext passwords. It uses PBKDF2 with SHA-256 hash algorithm and 720,000 iterations (in Django 5.0), combined with a cryptographically unique per-user salt. The database column stores the format: algorithm$iterations$salt$hash."
        },
        # Domain 9
        {
            "num": 9,
            "title": "Two-Phase Email OTP Verification",
            "what": "A secondary authentication security layer where an unverified user account is created with is_active=False until a 6-digit one-time PIN sent to their registered email is validated.",
            "why": "Prevents spam signups, bot registrations, and identity spoofing by ensuring the user owns the email address before granting platform access.",
            "how": "1. User submits registration form -> User saved with is_active=False -> EmailOTP generated with secrets.choice() -> 6-digit code sent via SMTP -> user_id saved in request.session['pending_user_id']. 2. User submits OTP -> verify_otp() checks code match, attempts < 5, and age <= 10 minutes. If valid, user.is_active = True, user.save(), and session cleared.",
            "where": "accounts/models.py (EmailOTP), accounts/services.py (generate_and_send_otp, verify_user_otp), accounts/views.py (VerifyOTPView, ResendOTPView).",
            "q": "How do you protect the OTP verification system against brute-force attacks and replay attacks?",
            "ans": "EmailOTP tracks an attempts integer field. Every failed guess increments attempts; if it reaches 5, the OTP is instantly invalidated (is_used=True). Furthermore, the OTP expires automatically after 10 minutes, and once successfully verified, is_used is permanently flagged to True."
        },
        # Domain 10
        {
            "num": 10,
            "title": "Google OAuth 2.0 Integration & Roadmap",
            "what": "An open standard authorization protocol that delegates authentication to Google, enabling users to log in securely without entering a password on Learnix.",
            "why": "Increases signup conversion rates, reduces password fatigue, and offloads multi-factor security to Google's identity infrastructure.",
            "how": "Authorization Code Grant: User clicks 'Sign in with Google' -> Redirected to Google consent screen -> Google redirects back to /accounts/google/login/callback/ with auth code -> Backend exchanges auth code for access token via HTTPS POST -> Backend fetches Google user profile -> Django matches or creates user record -> Logs user in.",
            "where": "requirements.txt (django-allauth>=65.0.0 installed); templates/accounts/login.html (Google button placeholder href='#'); accounts/views.py (OAuth integration guide ready for INSTALLED_APPS activation).",
            "q": "What is the current implementation status of Google Sign-In in Learnix?",
            "ans": "The UI button and styling are fully implemented in login.html, and the django-allauth library is installed in requirements.txt. The backend settings (adding allauth to INSTALLED_APPS, configuring SOCIALACCOUNT_PROVIDERS, and setting Google Client ID/Secret in .env) are staged as the next architectural milestone."
        },
        # Domain 11
        {
            "num": 11,
            "title": "Stripe Hosted Checkout & Card-Only Flow",
            "what": "A payment integration where the user is redirected to Stripe's PCI-DSS Level 1 compliant hosted checkout page to complete transactions securely.",
            "why": "Zero sensitive card data touches Learnix servers, completely eliminating PCI compliance liability while providing an optimized, fraud-protected checkout UI.",
            "how": "User clicks 'Buy Now' -> CreateCheckoutSessionView calls stripe.checkout.Session.create() with payment_method_types=['card'], course metadata, success_url, cancel_url -> Pending PaymentTransaction record created -> View redirects user to session.url (hosted by Stripe).",
            "where": "payments/views.py (CreateCheckoutSessionView, PaymentSuccessView, PaymentCancelView), payments/services.py (create_stripe_checkout_session).",
            "q": "Why did you explicitly restrict payment_method_types to ['card']?",
            "ans": "To maintain a streamlined checkout experience for our target student demographic and avoid wallet popups (Apple Pay, Google Pay) during local sandbox testing, ensuring clear and consistent credit/debit card processing."
        },
        # Domain 12
        {
            "num": 12,
            "title": "Stripe Webhooks & Asynchronous Fulfillment",
            "what": "An event-driven HTTP POST callback sent directly from Stripe's servers to Learnix to notify the backend when a payment is successfully completed.",
            "why": "Guarantees reliable course enrollment and invoice generation even if the student closes their browser tab, loses internet connectivity, or experiences a crash immediately after entering payment details.",
            "how": "Stripe sends checkout.session.completed event -> payments/webhooks.py receives raw request body -> stripe.Webhook.construct_event() validates HMAC-SHA256 signature using STRIPE_WEBHOOK_SECRET -> fulfill_order() executes inside transaction.atomic() -> PaymentTransaction updated to COMPLETED -> Enrollment created -> Invoice issued -> Confirmation email sent.",
            "where": "payments/webhooks.py (stripe_webhook view), payments/services.py (fulfill_payment_order).",
            "q": "Why is the webhook endpoint decorated with @csrf_exempt?",
            "ans": "CSRF tokens are browser cookies submitted by web browsers to protect user sessions. Stripe's webhook is an external machine-to-machine HTTP POST call that cannot have a Django CSRF cookie. Instead of CSRF, authenticity is cryptographically verified using Stripe's HMAC-SHA256 webhook signature header (Stripe-Signature)."
        },
        # Domain 13
        {
            "num": 13,
            "title": "Course & Enrollment Management Subsystem",
            "what": "The core e-learning business logic models representing courses, hierarchical modules, sequential lessons, and student enrollment records.",
            "why": "Provides a clean structured hierarchy for educational content delivery, enforces paid course access restrictions, and tracks student participation.",
            "how": "Course has many Modules (ForeignKey, ordering by order); Module has many Lessons (ForeignKey, ordering by order). Enrollment links User and Course. Views inspect Enrollment records before granting access to lesson streaming.",
            "where": "courses/models.py (Course, Module, Lesson, Enrollment), courses/decorators.py (@enrolled_required), accounts/mixins.py (EnrolledCourseRequiredMixin).",
            "q": "How does the platform restrict free preview lessons versus paid lessons?",
            "ans": "Lesson has an is_preview boolean field. If a user is not enrolled, LessonDetailView and the lesson_preview_api endpoint check if lesson.is_preview is True. If True, content is served; if False, the user is redirected to the course landing page with a 403 Forbidden alert."
        },
        # Domain 14
        {
            "num": 14,
            "title": "Progress Tracking & Dynamic Certificate Issuance",
            "what": "An automated tracking engine that records lesson completion per student, calculates overall course completion percentage, and automatically issues a unique, verifiable PDF/hash certificate upon 100% completion.",
            "why": "Motivates learners, provides visual progress indicators (progress bar), and delivers tangible credentials upon mastering course content.",
            "how": "When student clicks 'Mark Complete', MarkCompleteView creates/updates LessonProgress(is_completed=True). enrollment.calculate_progress() counts completed lessons / total lessons * 100. When progress reaches 100%, Certificate.objects.get_or_create() generates a unique certificate ID (LRN-UUID-X) and SHA-256 verification hash.",
            "where": "courses/models.py (LessonProgress, Certificate), courses/views.py (MarkCompleteView, CertificateView).",
            "q": "How do you ensure a student cannot claim a certificate without finishing all lessons?",
            "ans": "Certificate generation is strictly guarded in Certificate.generate_for_enrollment() and CertificateView. The method re-evaluates enrollment.calculate_progress() from the database; if completed lessons < total lessons, it raises PermissionDenied('Course not yet 100% completed.'), preventing unauthorized certificate generation."
        },
        # Domain 15
        {
            "num": 15,
            "title": "RESTful Endpoints & Client-Side AJAX Architecture",
            "what": "Asynchronous HTTP endpoints that accept JSON/URL-encoded requests from browser JavaScript and return structured JSON responses without triggering a full page reload.",
            "why": "Delivers a modern, fast, responsive Single Page Application (SPA)-like experience for live course search, modal previews, and instantaneous lesson completion.",
            "how": "Browser fetch() or XMLHttpRequest sends GET/POST -> Django view processes query -> View instantiates JsonResponse({'status': 'success', ...}) -> JavaScript receives response and dynamically updates the DOM.",
            "where": "courses/views.py: course_search_api (live search autocomplete), MarkCompleteView (instant lesson completion toggle), lesson_preview_api (modal video/text preview).",
            "q": "Why did you choose native JsonResponse instead of Django REST Framework (DRF)?",
            "ans": "For Learnix's current scope, native Django JsonResponse provides lightweight, zero-dependency, ultra-fast asynchronous JSON handling without the overhead of installing, configuring, and maintaining heavy DRF serializers, viewsets, and permissions classes. DRF can easily be added later if full public API exposure is needed."
        },
        # Domain 16
        {
            "num": 16,
            "title": "Security Architecture & Vulnerability Mitigation",
            "what": "A comprehensive security defense layer protecting against the OWASP Top 10 vulnerabilities including CSRF, XSS, SQL Injection, Session Hijacking, and Clickjacking.",
            "why": "Protects student personal data, financial transactions, and server integrity from malicious exploitation.",
            "how": "CsrfViewMiddleware requires cryptographic tokens on POST; Django ORM parameterizes all SQL queries to eliminate SQL injection; Django template engine auto-escapes HTML to prevent XSS; XFrameOptionsMiddleware sets DENY to block clickjacking; Session cookies use HttpOnly and SameSite=Lax.",
            "where": "config/settings.py (MIDDLEWARE list, SECURE_* directives, PASSWORD_HASHERS), core/middleware.py.",
            "q": "How does Django protect against Cross-Site Request Forgery (CSRF)?",
            "ans": "Django generates a cryptographically random, secret token stored in a user cookie. In every POST form, {% csrf_token %} renders a hidden input. When submitted, CsrfViewMiddleware compares the form token against the cookie token. If they do not match or the token is missing, the request is rejected with 403 Forbidden."
        },
        # Domain 17
        {
            "num": 17,
            "title": "Database ACID Transactions & Concurrency",
            "what": "Atomic, Consistent, Isolated, and Durable database operations executed within a single transactional boundary using Django's transaction.atomic() context manager.",
            "why": "Prevents orphaned data or corrupt states when an operation requires writing to multiple database tables simultaneously (e.g. updating payment status, creating enrollment, and creating an invoice).",
            "how": "with transaction.atomic(): opens an SQL BEGIN TRANSACTION block. If all Python code within the block succeeds, COMMIT is issued. If an unhandled exception occurs, an automatic ROLLBACK restores the database to its pristine state before the block began.",
            "where": "payments/views.py (PaymentSuccessView), payments/webhooks.py (fulfill_payment_order in background).",
            "q": "What happens if creating the Invoice fails after PaymentTransaction is marked COMPLETED?",
            "ans": "Because both operations are enclosed inside with transaction.atomic(), the unhandled exception triggers an immediate ROLLBACK. The PaymentTransaction change is undone, no partial enrollment is saved, and the database remains 100% consistent."
        },
        # Domain 18
        {
            "num": 18,
            "title": "Centralized Transactional Email Subsystem",
            "what": "A unified email notification architecture utilizing Django's django.core.mail module configured with SMTP credentials to dispatch HTML and fallback plaintext transactional emails.",
            "why": "Keeps users informed across critical lifecycle events (OTP verification, purchase receipt, certificate issuance, password reset) with consistent branding and reliable delivery.",
            "how": "Services call EmailMultiAlternatives, attach HTML rendered via render_to_string(), provide plain-text fallback, and send via configured SMTP host (smtp.gmail.com on port 587 with TLS).",
            "where": "config/settings.py (EMAIL_BACKEND, EMAIL_HOST_USER = 'shahbazbutt22ee@gmail.com'), core/services/email.py (send_otp_email, send_payment_receipt_email, send_certificate_email).",
            "q": "How does Learnix prevent an email delivery failure from crashing a critical user request?",
            "ans": "The send_mail call uses fail_silently=False wrapped in a try...except SMTPException block, with error logging. In the OTP workflow, failure raises a user-friendly custom EmailDeliveryError prompting a resend rather than showing an unhandled 500 error."
        }
    ]

    for item in domains:
        d_table = Table([
            [Paragraph(f"<b>DOMAIN {item['num']}: {item['title']}</b>", ParagraphStyle('DTitle', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=PRIMARY_DARK))],
            [Paragraph(f"<b>What it is:</b> {item['what']}", style_body)],
            [Paragraph(f"<b>Why in Learnix:</b> {item['why']}", style_body)],
            [Paragraph(f"<b>Internal Mechanism (How):</b> {item['how']}", style_body)],
            [Paragraph(f"<b>Code Location:</b> <font color='#4F46E5'>{item['where']}</font>", style_body)],
        ], colWidths=[540])
        d_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#CBD5E1')),
            ('LINELEFT', (0,0), (0,-1), 3.5, PRIMARY),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(KeepTogether([
            d_table,
            spacer(3),
            viva_qa(item['num'], item['title'], item['q'], item['ans'], item['where']),
            spacer(6)
        ]))

    return story


# ==============================================================================
# SECTION 24: CODE EXPLANATION RULES & LIVE PRESENTATION STRATEGIES
# ==============================================================================

def build_section_24():
    story = []
    story.append(PageBreak())
    story.append(h1("24. Code Explanation Rules and Live Demonstration Strategies"))
    story.append(hr())
    story.append(p(
        "A common pitfall in technical evaluations is reading code line-by-line like a narrative novel. "
        "Examiners want to hear <b>engineering reasoning</b>: what problem does this component solve, what data enters it, "
        "how does it transform state, and how does it handle failure? "
        "Follow these battle-tested strategies when presenting Learnix code live:"
    ))
    story.append(spacer(6))

    rules = [
        ("Rule 1: The 30-Second High-Level Summary First",
         "Never start explaining from line 1 of a file. Begin with the macro-purpose: 'This class handles Stripe checkout session creation. It receives the course ID, creates a pending transaction record, calls Stripe's API to generate a session URL, and redirects the student to Stripe's hosted checkout page.'"),
        ("Rule 2: The Input-Output First Principle",
         "Clearly articulate the inputs and outputs before discussing internal loops: 'The input is an HTTP POST request containing a CSRF token and course_id. The output is an HTTP 302 redirect header pointing to checkout.stripe.com.'"),
        ("Rule 3: Structural Traversal Order",
         "Explain components in this standardized logical sequence: 1. Mixins / Inherited base class; 2. Decorators; 3. Method dispatch; 4. Database query / ORM lookup; 5. Business logic & state mutations; 6. Transaction handling; 7. Return response."),
        ("Rule 4: Explain 'Why' Over 'What'",
         "Instead of saying 'Here I use transaction.atomic()', explain 'I wrap the enrollment and invoice creation inside transaction.atomic() to ensure database ACID compliance—if the invoice generation fails, the payment status rolls back so no inconsistent state is saved.'"),
        ("Rule 5: Highlight Defense and Edge-Case Handling",
         "Examiners love edge cases. Explicitly point out: 'Notice on line 42, we check if the user is already enrolled using Enrollment.objects.filter().exists() to prevent duplicate charges or double enrollments.'"),
        ("Rule 6: How to Handle Unfamiliar or Difficult Questions",
         "If asked about an unfamiliar concept: 1. Stay calm; 2. Acknowledge the core topic ('That relates to database indexing strategies'); 3. Explain how Learnix currently handles it ('In our current design, we rely on Django's automatic primary key indexing and unique constraints'); 4. State how you would implement it next ('To scale this for millions of rows, I would add db_index=True or composite indexes in the model Meta class')."),
        ("Rule 7: Live Code Presentation Checklist",
         "Keep your IDE organized: 1. Have config/settings.py, models.py, and views.py open in split tabs; 2. Have the terminal ready with python manage.py runserver running; 3. Know the exact line numbers of key features (e.g. EmailOTP creation in accounts/models.py, checkout in payments/views.py); 4. Keep your browser logged in with both a superuser and a normal student account.")
    ]

    for title, desc in rules:
        r_table = Table([
            [Paragraph(f"<b>{title}</b>", ParagraphStyle('RTitle', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=PRIMARY_DARK))],
            [Paragraph(desc, style_body)]
        ], colWidths=[540])
        r_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
            ('LINELEFT', (0,0), (0,-1), 3.5, ACCENT_CYAN),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(r_table)
        story.append(spacer(4))

    story.append(spacer(4))
    story.append(callout(
        "Live Demonstration Golden Rule",
        "When asked to demonstrate a feature: 1. Walk through the UI as a student; 2. Show the resulting database change in the Django Admin or database shell; 3. Open the corresponding View in VS Code and explain the exact lines that executed that transition.",
        "viva"
    ))
    return story


# ==============================================================================
# SECTION 25: FINAL QUICK REVISION & VIVA CHEAT SHEETS
# ==============================================================================

def build_section_25():
    story = []
    story.append(PageBreak())
    story.append(h1("25. Final Quick Revision: 7 High-Yield Cheat Sheets & Top 50 Viva Q&As"))
    story.append(hr())
    story.append(p(
        "This final section serves as your rapid-fire revision cockpit. It condenses the entire Learnix backend "
        "into <b>7 one-page architectural cheat sheets</b>, followed by the <b>Top 50 Most Likely Technical Viva Questions "
        "and Model Answers</b> designed to guarantee maximum confidence and competence during evaluation."
    ))
    story.append(spacer(6))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 1: ARCHITECTURAL BLUEPRINT
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 1: Architectural Blueprint & Request-Response Pipeline"))
    sheet1_data = [
        ["Pipeline Stage", "Component Executed", "Key Responsibility in Learnix", "Code Reference"],
        ["1. Web Gateway", "WSGI Handler (wsgi.py)", "Bridges HTTP server to Django application instance", "config/wsgi.py"],
        ["2. Security & Session", "Security & Session Middleware", "SSL redirect, HSTS, sessionid cookie lookup", "config/settings.py:MIDDLEWARE"],
        ["3. Authentication", "AuthenticationMiddleware", "Associates request.user with authenticated User", "django.contrib.auth"],
        ["4. CSRF Defense", "CsrfViewMiddleware", "Validates CSRF token on POST requests", "django.middleware.csrf"],
        ["5. URL Dispatcher", "Root URLconf (config/urls.py)", "Matches regex/path and extracts URL kwargs", "config/urls.py"],
        ["6. View Execution", "CBV / FBV (views.py)", "Executes business logic, queries ORM, handles forms", "courses/views.py"],
        ["7. Database Engine", "Django ORM / PostgreSQL", "Compiles lazy QuerySets into parameterized SQL", "courses/models.py"],
        ["8. Presentation", "Template Engine / JsonResponse", "Renders HTML templates or returns JSON payload", "templates/, JsonResponse"],
        ["9. Client Delivery", "HttpResponse (Status 200/302)", "Sends HTTP headers, cookies, and rendered content", "HTTP Response"]
    ]
    story.append(create_table(sheet1_data, [85, 125, 220, 110]))
    story.append(spacer(8))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 2: DATABASE & 11 MODELS MATRIX
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 2: Relational Schema & 11 Models ERD Matrix"))
    sheet2_data = [
        ["Model Name", "App", "Primary Foreign Keys & Relations", "Unique Constraints / Key Fields", "Core Purpose"],
        ["UserProfile", "accounts", "OneToOneField -> User", "bio, avatar, phone, role", "Extends auth_user with profile info"],
        ["EmailOTP", "accounts", "ForeignKey -> User", "unique_together=('user','code'), attempts", "Two-phase registration security"],
        ["Category", "courses", "None (Self-contained)", "name, slug (unique=True)", "Course subject classification"],
        ["Course", "courses", "FK -> User, FK -> Category", "slug (unique=True), price, is_published", "Master e-learning catalog entity"],
        ["Module", "courses", "FK -> Course (on_delete=CASCADE)", "order (PositiveIntegerField)", "Hierarchical course chapter structure"],
        ["Lesson", "courses", "FK -> Module (on_delete=CASCADE)", "order, is_preview, video_url", "Individual educational learning unit"],
        ["Enrollment", "courses", "FK -> User, FK -> Course", "unique_together=('user','course')", "Grants and verifies student course access"],
        ["LessonProgress", "courses", "FK -> User, FK -> Lesson", "unique_together=('user','lesson')", "Tracks individual lesson completion"],
        ["Review", "courses", "FK -> User, FK -> Course", "unique_together=('user','course'), rating", "Student course ratings (1-5) and feedback"],
        ["Certificate", "courses", "FK -> User, FK -> Course", "certificate_id (unique=True), sha256_hash", "Automated course credential generation"],
        ["PaymentTransaction", "payments", "FK -> User, FK -> Course", "stripe_session_id, amount, status", "Tracks financial transaction state"],
        ["Invoice", "payments", "FK -> PaymentTransaction", "invoice_number (unique=True)", "Official billing and tax documentation"]
    ]
    story.append(create_table(sheet2_data, [75, 45, 130, 140, 150]))
    story.append(spacer(8))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 3: AUTHENTICATION & TWO-PHASE OTP LIFECYCLE
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 3: Authentication & Two-Phase OTP Lifecycle"))
    sheet3_data = [
        ["Phase", "Trigger Action", "Internal Logic Executed", "State / Database Result"],
        ["Phase 1: Form Submit", "POST /accounts/signup/", "StudentRegistrationForm.is_valid() passes", "User saved with is_active=False"],
        ["Phase 2: Code Creation", "generate_and_send_otp()", "secrets.choice(digits) creates 6-digit code", "EmailOTP created; user_id stored in session"],
        ["Phase 3: SMTP Dispatch", "send_otp_email()", "SMTP TLS email sent to registered address", "User sees OTP verification form"],
        ["Phase 4: Input Validation", "POST /accounts/verify-otp/", "OTPVerificationForm checks 6-digit regex", "Form validated against database record"],
        ["Phase 5: Verification Check", "verify_user_otp()", "Checks code match, age <= 10m, attempts < 5", "If valid: user.is_active=True, OTP used"],
        ["Phase 6: Session Cleanup", "VerifyOTPView.post()", "del request.session['pending_user_id']", "Redirect to /accounts/login/ with success"]
    ]
    story.append(create_table(sheet3_data, [90, 110, 200, 140]))
    story.append(spacer(8))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 4: GOOGLE OAUTH 2.0 STATUS & ROADMAP
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 4: Google OAuth 2.0 Architectural Blueprint & Status"))
    sheet4_data = [
        ["Layer / Component", "Current Implementation Status", "Code Location", "Viva Talking Point"],
        ["Frontend UI", "Fully Implemented (Google Sign-In Button)", "templates/accounts/login.html", "Branded button rendered with Google SVG icon"],
        ["Package Dependency", "Installed (django-allauth>=65.0.0)", "requirements.txt", "Library in virtual environment ready for activation"],
        ["Button Link", "Placeholder (href='#')", "templates/accounts/login.html", "Prevents broken links while backend is configured"],
        ["Backend Activation", "Roadmap Milestone (Ready for config)", "accounts/views.py (documented)", "Add allauth to INSTALLED_APPS, configure client secrets"],
        ["Auth Flow Standard", "OAuth 2.0 Authorization Code Grant", "Theory & Implementation guide", "Google exchanges auth code for JWT user identity token"]
    ]
    story.append(create_table(sheet4_data, [95, 145, 140, 160]))
    story.append(spacer(8))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 5: STRIPE HOSTED CHECKOUT & WEBHOOK SETTLEMENT
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 5: Stripe Hosted Checkout & Webhook Settlement Matrix"))
    sheet5_data = [
        ["Step", "Endpoint / Handler", "Parameters / Payload", "Business / Financial Logic"],
        ["1. Initiate Checkout", "POST /payments/checkout/<course_id>/", "payment_method_types=['card']", "Creates pending PaymentTransaction, redirects to Stripe"],
        ["2. Hosted Payment", "https://checkout.stripe.com/", "Card Number, Expiry, CVC", "Stripe PCI Level 1 hosted page processes payment"],
        ["3. User Redirect", "GET /payments/success/", "?session_id={CHECKOUT_SESSION_ID}", "Verifies session status with Stripe API, enrolls user"],
        ["4. Webhook Callback", "POST /payments/webhook/", "Event: checkout.session.completed", "Cryptographically verifies Stripe-Signature header"],
        ["5. Order Fulfillment", "fulfill_payment_order()", "session.metadata['course_id']", "transaction.atomic(): marks tx COMPLETED, issues invoice"],
        ["6. Confirmation Email", "send_payment_receipt_email()", "User, Course, Invoice Number", "Dispatches HTML invoice receipt via SMTP"]
    ]
    story.append(create_table(sheet5_data, [85, 135, 140, 180]))
    story.append(spacer(8))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 6: ASYNCHRONOUS AJAX ENDPOINTS
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 6: Asynchronous AJAX Endpoints & Client-Side Contract"))
    sheet6_data = [
        ["Endpoint URL", "Method", "Request Parameters", "Response Format (JSON)", "UI Interaction"],
        ["/courses/api/search/", "GET", "?q=<query_str>", "{'results': [{'title', 'slug', 'price'}]}", "Live search dropdown autocomplete"],
        ["/courses/lesson/<id>/complete/", "POST", "X-CSRFToken header", "{'status': 'success', 'progress': 75.0}", "Instant progress bar update & checkmark"],
        ["/courses/api/lesson/<id>/preview/", "GET", "None (Public for preview)", "{'title': '...', 'video_url': '...'}", "Opens video preview in Stitch modal"]
    ]
    story.append(create_table(sheet6_data, [130, 45, 120, 135, 110]))
    story.append(spacer(8))

    # --------------------------------------------------------------------------
    # CHEAT SHEET 7: MASTER DJANGO CLI REFERENCE
    # --------------------------------------------------------------------------
    story.append(h2("Cheat Sheet 7: Master Django Management Commands & CLI Reference"))
    sheet7_data = [
        ["Management Command", "Core Action", "Safety / Production Consideration"],
        ["python manage.py runserver", "Starts local lightweight WSGI development server", "Never use in production; use Gunicorn / Uwsgi"],
        ["python manage.py makemigrations", "Scans models.py and creates Python migration files", "Review generated migrations before applying"],
        ["python manage.py migrate", "Executes unapplied migrations on database", "Runs within transactional DDL on PostgreSQL"],
        ["python manage.py createsuperuser", "Creates administrative user with is_superuser=True", "Requires strong password meeting validators"],
        ["python manage.py collectstatic", "Copies all static assets into STATIC_ROOT", "Essential build step before production deployment"],
        ["python manage.py check --deploy", "Runs security health checks on settings.py", "Verifies SSL, cookies, debug mode before release"],
        ["python manage.py shell", "Launches interactive Python shell with Django loaded", "Excellent for testing ORM queries and service functions"]
    ]
    story.append(create_table(sheet7_data, [140, 190, 210]))
    story.append(spacer(12))

    # --------------------------------------------------------------------------
    # TOP 50 VIVA QUESTIONS AND MODEL ANSWERS
    # --------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(h1("Top 50 Most Likely Technical Evaluation Questions & Concise Model Answers"))
    story.append(hr())
    story.append(p(
        "These 50 questions have been carefully curated from real-world software engineering interviews and university "
        "viva examinations. Every question is answered with concise, technically accurate model answers directly grounded "
        "in the Learnix codebase."
    ))
    story.append(spacer(6))

    top_50_qas = [
        # Django Architecture & Core (1-8)
        (1, "Core", "What is Django and what does it mean that it is a 'batteries-included' framework?",
         "Django is a high-level Python web framework that encourages rapid development. 'Batteries-included' means it ships out-of-the-box with common web features like an ORM, authentication, CSRF protection, admin panel, and form validation without requiring third-party plugins.", "config/settings.py"),
        (2, "Core", "Explain the difference between a Django Project and a Django App.",
         "A Project is the entire website configuration containing global settings, database credentials, and root URL routing (e.g. Learnix). An App is a self-contained, modular Python package that handles a single functional responsibility (e.g. accounts, courses, payments).", "config/ vs accounts/"),
        (3, "Core", "What is wsgi.py and what is its role?",
         "WSGI stands for Web Server Gateway Interface. It is the standardized Python specification that enables web servers like Gunicorn or Nginx to communicate with Django application code.", "config/wsgi.py"),
        (4, "Core", "What is the purpose of manage.py?",
         "It is a command-line utility that wraps django.core.management, setting the DJANGO_SETTINGS_MODULE environment variable and providing CLI commands like runserver, migrate, and collectstatic.", "manage.py"),
        (5, "Core", "How does Django locate and render HTML templates?",
         "Django's TEMPLATES setting defines backend engines. The APP_DIRS: True setting instructs Django to look inside a 'templates/' folder in every installed app, while DIRS specifies project-wide template roots.", "config/settings.py:TEMPLATES"),
        (6, "Core", "What are Context Processors in Django?",
         "Functions that run automatically on every template render, injecting global dictionary variables (like request, user, or cart count) into every template without manually passing them in each view.", "courses/context_processors.py"),
        (7, "Core", "What is the role of Custom Template Filters?",
         "Functions decorated with @register.filter that modify or format variable display inside templates (e.g. formatting course duration or currency).", "courses/templatetags/course_tags.py"),
        (8, "Core", "Why should DEBUG=True never be used in production?",
         "When DEBUG=True, any unhandled exception outputs a detailed traceback revealing database passwords, file paths, settings, and internal variables to the public internet, creating an extreme security risk.", "config/settings.py:DEBUG"),

        # Models & ORM (9-15)
        (9, "ORM", "What is an ORM and what are its primary advantages?",
         "An Object-Relational Mapper translates Python classes to database tables and Python queries to SQL. It prevents SQL injection, accelerates development, and eliminates database vendor lock-in.", "courses/models.py"),
        (10, "ORM", "What is a QuerySet and why is it considered 'lazy'?",
         "A QuerySet is a collection of database queries. It is lazy because it does not execute SQL against the database until the data is actually needed (e.g. when iterated over or evaluated).", "courses/views.py"),
        (11, "ORM", "Explain the difference between select_related and prefetch_related.",
         "select_related performs a SQL JOIN in a single query and is used for single-valued relationships (ForeignKey, OneToOneField). prefetch_related executes a separate query and joins objects in Python memory, used for multi-valued relationships (ManyToMany, reverse ForeignKey).", "courses/views.py"),
        (12, "ORM", "What is the difference between on_delete=models.CASCADE and models.SET_NULL?",
         "CASCADE deletes child records when the referenced parent record is deleted (e.g. deleting a Course deletes all its Modules). SET_NULL sets the foreign key to NULL (requires null=True), preserving child records.", "courses/models.py:Module"),
        (13, "ORM", "What is the purpose of unique_together in model Meta?",
         "It creates a composite unique database constraint across multiple columns, guaranteeing that no two rows can have duplicate combinations of those values (e.g. a user cannot enroll twice in the same course).", "courses/models.py:Enrollment"),
        (14, "ORM", "What is the difference between null=True and blank=True?",
         "null=True determines database schema (whether the database column allows NULL values). blank=True determines form validation (whether a field can be left empty in forms and admin).", "accounts/models.py:UserProfile"),
        (15, "ORM", "How does get_or_create() work in Django?",
         "It queries the database for an object matching kwargs. If found, it returns (object, False). If not found, it creates and saves a new object and returns (object, True).", "payments/views.py"),

        # Migrations (16-19)
        (16, "Migrations", "What is the difference between makemigrations and migrate?",
         "makemigrations inspects models.py and creates Python migration files recording schema changes. migrate executes those migration files on the actual database to update table schemas.", "courses/migrations/"),
        (17, "Migrations", "Where does Django keep track of which migrations have been applied?",
         "In a dedicated internal database table named django_migrations, which stores the app name, migration name, and the timestamp it was applied.", "django_migrations table"),
        (18, "Migrations", "What is a fake migration and when would you use it?",
         "python manage.py migrate --fake marks migrations as applied in django_migrations without actually running the SQL DDL statements. Used when syncing existing database tables to new migration files.", "CLI Command"),
        (19, "Migrations", "What should you do if two developers create conflicting migrations?",
         "Run python manage.py makemigrations --merge. Django will generate a merge migration that unifies the conflicting branch points into a single timeline.", "CLI Command"),

        # Views & URLs (20-25)
        (20, "Views", "What are Class-Based Views (CBVs) and why use them?",
         "CBVs represent views as Python classes. They allow code reuse through object-oriented inheritance and mixins, and provide generic views (ListView, DetailView) that eliminate repetitive CRUD code.", "courses/views.py:CourseListView"),
        (21, "Views", "How does a CBV route different HTTP methods like GET and POST?",
         "The as_view() classmethod returns a view function. Inside, dispatch() inspects request.method and calls the matching class method (get(), post(), put()).", "courses/views.py:LessonView"),
        (22, "Views", "What is the purpose of LoginRequiredMixin?",
         "An access-control mixin that intercepts incoming requests; if the user is unauthenticated, it redirects them to settings.LOGIN_URL with a ?next= parameter pointing to the requested page.", "accounts/mixins.py"),
        (23, "Views", "How does URL path conversion work (e.g. <slug:slug>, <int:pk>)?",
         "Path converters capture substrings from the URL, convert them to Python types (str for slug, int for pk), and pass them as keyword arguments into the view function.", "courses/urls.py"),
        (24, "Views", "What does reverse() do in Django?",
         "It looks up the URL pattern string by its named identifier (e.g. reverse('courses:course_detail', kwargs={'slug': 'python'})) preventing hardcoded URL strings.", "payments/views.py"),
        (25, "Views", "What is the difference between render() and redirect()?",
         "render() combines a template with a context dictionary and returns an HTTP 200 OK response with HTML content. redirect() returns an HTTP 302 Found response instructing the browser to navigate to a different URL.", "accounts/views.py"),

        # Forms & Validation (26-28)
        (26, "Forms", "What is a ModelForm in Django?",
         "A helper class that automatically builds form fields, validation logic, and save methods based on a specified Django Model's field definitions.", "accounts/forms.py"),
        (27, "Forms", "How does Django's form cleaning cycle work?",
         "When form.is_valid() is called, Django runs default field validation, then calls clean_<fieldname>() for field-specific logic, and finally calls clean() for multi-field cross-validation.", "accounts/forms.py:StudentRegistrationForm"),
        (28, "Forms", "Where are cleaned and validated form values stored?",
         "In the form.cleaned_data dictionary, with values already converted into appropriate Python data types (e.g. str, int, datetime).", "accounts/forms.py"),

        # Authentication & OTP (29-33)
        (29, "Auth", "Why does Learnix create new users with is_active=False?",
         "To enforce two-phase email verification. Unverified accounts cannot authenticate or access platform resources until their 6-digit email OTP is confirmed.", "accounts/views.py:SignUpView"),
        (30, "Auth", "Why use Python's secrets module instead of random for generating OTPs?",
         "random generates pseudo-random numbers that can be predicted by attackers if the internal seed is observed. secrets generates cryptographically secure entropy from the operating system.", "accounts/models.py:EmailOTP"),
        (31, "Auth", "How is OTP expiration calculated in Learnix?",
         "EmailOTP checks timezone.now() - self.created_at <= timedelta(minutes=10). If the duration exceeds 10 minutes, the OTP is considered expired.", "accounts/models.py:EmailOTP.is_valid()"),
        (32, "Auth", "What prevents brute-force guessing of the 6-digit OTP?",
         "The attempts counter increments on every incorrect guess. When attempts reach 5, the OTP record is permanently invalidated (is_used=True).", "accounts/services.py:verify_user_otp"),
        (33, "Auth", "How does Django track logged-in users across requests?",
         "Through session-based authentication: Django stores session state in the database (django_session table) and sends a signed sessionid cookie to the client browser.", "django.contrib.sessions"),

        # Google OAuth (34-36)
        (34, "OAuth", "What is OAuth 2.0 and why use it?",
         "OAuth 2.0 is an authorization protocol that allows third-party services like Google to verify user identities without exposing user passwords to the application.", "OAuth 2.0 Standard"),
        (35, "OAuth", "What is the difference between an Authorization Code and an Access Token?",
         "An Authorization Code is a short-lived, single-use token sent to the browser that the backend exchanges for an Access Token via a secure back-channel HTTP POST call.", "OAuth 2.0 Protocol"),
        (36, "OAuth", "What is the current status of Google Sign-In in Learnix?",
         "The UI button is fully designed with Google branding, django-allauth is installed in requirements.txt, and the backend activation steps are documented and staged for final key configuration.", "templates/accounts/login.html"),

        # Stripe Payments & Webhooks (37-42)
        (37, "Stripe", "Why use Stripe Hosted Checkout instead of collecting card numbers directly?",
         "Hosted Checkout offloads PCI compliance entirely to Stripe. Learnix servers never touch, process, or store credit card numbers, eliminating security and legal liability.", "payments/views.py"),
        (38, "Stripe", "How does Learnix disable Apple Pay and Google Pay in Stripe Checkout?",
         "By passing payment_method_types=['card'] when creating the Stripe Checkout session, restricting payment options strictly to credit/debit cards.", "payments/views.py:CreateCheckoutSessionView"),
        (39, "Stripe", "What is a Stripe Webhook and why is it necessary?",
         "A webhook is an HTTP callback from Stripe to our server. It is essential because if a user closes their browser immediately after paying, the success_url redirect never runs, but the webhook guarantees order fulfillment.", "payments/webhooks.py"),
        (40, "Stripe", "How does Learnix verify that a webhook really came from Stripe?",
         "Using stripe.Webhook.construct_event(), which checks the Stripe-Signature HTTP header against our STRIPE_WEBHOOK_SECRET using HMAC-SHA256 cryptography.", "payments/webhooks.py"),
        (41, "Stripe", "What is Idempotency in payment processing and how do you achieve it?",
         "Idempotency means an operation can be called multiple times without changing the result beyond the initial application. In Learnix, we check if PaymentTransaction.status == 'COMPLETED' before executing fulfillment to prevent duplicate enrollments.", "payments/services.py:fulfill_payment_order"),
        (42, "Stripe", "What does with transaction.atomic() do during payment fulfillment?",
         "It ensures that updating the transaction, creating the enrollment, and generating the invoice all succeed together or fail together, preventing partial database updates.", "payments/services.py"),

        # Courses, Enrollment & Certificates (43-46)
        (43, "Courses", "How is course progress percentage calculated?",
         "Total completed lessons for that student divided by total published lessons in that course multiplied by 100, formatted as a percentage float.", "courses/models.py:Enrollment.calculate_progress"),
        (44, "Courses", "What triggers automatic certificate generation?",
         "When a student marks a lesson complete and calculate_progress() reaches 100.0%, Certificate.objects.get_or_create() creates a verifiable certificate record.", "courses/models.py:Certificate"),
        (45, "Courses", "What makes Learnix certificates tamper-proof and verifiable?",
         "Each certificate receives a unique ID (LRN-UUID-X) and an SHA-256 cryptographic hash calculated from the student's ID, course ID, and issue timestamp.", "courses/models.py:Certificate"),
        (46, "Courses", "How does lesson preview work for unenrolled visitors?",
         "Lessons have an is_preview boolean field. If is_preview=True, unauthenticated or unenrolled users can watch the preview; if False, access is blocked with 403 Forbidden.", "courses/views.py:LessonView"),

        # Security & Production Deployment (47-50)
        (47, "Security", "How does Django protect against Cross-Site Scripting (XSS)?",
         "The template engine automatically HTML-escapes all variable output by default, converting dangerous characters like <, >, and & into safe HTML entities (&lt;, &gt;, &amp;).", "Django Template Engine"),
        (48, "Security", "How does Django protect against SQL Injection?",
         "The Django ORM uses parameterized queries (prepared statements), where user input is treated strictly as data rather than executable SQL commands.", "Django ORM"),
        (49, "Deployment", "What is WhiteNoise and why is it used in production?",
         "WhiteNoise is a Python middleware that enables Django to serve its own static files (CSS, JS, images) directly with high performance, gzip compression, and caching headers without configuring Nginx.", "config/settings.py:WhiteNoise"),
        (50, "Deployment", "What are the essential steps to prepare a Django project for production?",
         "1. Set DEBUG=False; 2. Set strong SECRET_KEY via environment variable; 3. Configure PostgreSQL database; 4. Run collectstatic; 5. Use Gunicorn as WSGI server; 6. Enable SECURE_SSL_REDIRECT and SECURE_HSTS_SECONDS; 7. Run python manage.py check --deploy.", "config/settings.py")
    ]

    for q_num, topic, question, answer, code_ref in top_50_qas:
        story.append(viva_qa(q_num, topic, question, answer, code_ref))
        story.append(spacer(4))

    return story


# ==============================================================================
# MAIN EXPORT FUNCTION FOR PART 5
# ==============================================================================

def build_part5():
    """
    Builds and returns all flowables for Sections 23, 24, and 25.
    """
    story = []
    story.extend(build_section_23())
    story.extend(build_section_24())
    story.extend(build_section_25())
    return story
