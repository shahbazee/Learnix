"""
Sections 12 to 17 for Learnix Technical Documentation:
12. Course and Enrollment System
13. REST API / Django REST Framework
14. Forms and Validation
15. Security Architecture
16. Error Handling & System Resilience
17. Complete Request Lifecycle Traces
"""

from .doc_builder import (
    p, bullet, h1, h2, h3, spacer, hr, code_box, callout, viva_qa, create_table
)
from reportlab.platypus import PageBreak

def build_part3():
    story = []

    # =========================================================================
    # SECTION 12: COURSE AND ENROLLMENT SYSTEM
    # =========================================================================
    story.append(h1("12. Course and Enrollment System"))
    story.append(hr())
    story.append(p(
        "The curriculum architecture in Learnix is modeled hierarchically to simulate rigorous, "
        "university-caliber technical tracks. The data hierarchy consists of: "
        "<b>CourseCategory -> Course -> CourseModule -> Lesson</b>, with student interactions tracked via "
        "<b>Enrollment</b>, <b>LessonProgress</b>, and <b>Certificate</b>."
    ))

    story.append(h2("12.1 Curriculum Entity Hierarchy"))
    story.append(bullet("<b>CourseCategory:</b> High-level subject matter domains (AI & LLMs, System Design, Zero-Trust Security)."))
    story.append(bullet("<b>Course:</b> Masterclass entity containing tuition pricing, level (BEGINNER, INTERMEDIATE, ADVANCED), instructor foreign key, description, thumbnail, rating, and publication status."))
    story.append(bullet("<b>CourseModule:</b> Sequential chapters or units organizing the syllabus (e.g. 'Module 1: Foundations')."))
    story.append(bullet("<b>Lesson:</b> Discrete learning units containing video streaming URLs, duration in seconds, markdown notes, and an <b>is_preview</b> boolean gating free guest access."))

    story.append(h2("12.2 Progress Calculation & Certificate Issuance"))
    story.append(p(
        "Student progress is tracked dynamically through the <b>calculate_progress()</b> method on the <b>Enrollment</b> model:"
    ))
    story.append(code_box("""# courses/models.py — calculate_progress() and automated Certificate issuance
def calculate_progress(self) -> float:
    total_lessons = Lesson.objects.filter(module__course=self.course).count()
    if total_lessons == 0:
        self.progress_percent = 0.00
    else:
        completed_count = LessonProgress.objects.filter(
            user=self.user,
            lesson__module__course=self.course,
            is_completed=True
        ).count()
        self.progress_percent = round((completed_count / total_lessons) * 100, 2)
        if self.progress_percent > 100.0:
            self.progress_percent = 100.00
    self.save(update_fields=["progress_percent"])

    # Automatically issue Certificate upon reaching 100% completion
    if self.progress_percent >= 100.00:
        Certificate.issue_for_enrollment(self)

    return float(self.progress_percent)""", "courses/models.py — Automated Progress & Certificate Trigger"))

    story.append(h2("12.3 Cryptographic Certificate Verification Ledger"))
    story.append(p(
        "When an enrollment reaches 100%, Learnix generates a <b>Certificate</b> with a cryptographic SHA-256 ledger hash: "
        "<b>0x + sha256('LEARNIX_CERT:{user_id}:{course_slug}:{timestamp}:SHA256_AUTH')[:38]</b>. "
        "Anyone can verify the legitimacy of a graduate's certificate publicly at <b>/courses/certificates/&lt;certificate_id&gt;/</b>, "
        "which renders the verifiable blockchain-styled credentials page."
    ))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 13: REST API / DJANGO REST FRAMEWORK
    # =========================================================================
    story.append(h1("13. REST API & Serialization Architecture"))
    story.append(hr())
    story.append(callout("Current Codebase Status: Native JsonResponse Endpoints Active (DRF Not Installed)",
        "An inspection of <b>requirements.txt</b> and <b>learnix_project/settings.py</b> shows that "
        "<b>Django REST Framework (djangorestframework)</b> is not installed. Instead, Learnix implements "
        "clean, ultra-fast, native JSON endpoints using Django's built-in <b>JsonResponse</b>.<br/>"
        "This is an important distinction to explain during your evaluation: Learnix delivers API functionality "
        "without adding heavy third-party framework overhead.", "info"))

    story.append(h2("13.1 Actual JSON Endpoints Implemented in Learnix"))
    story.append(create_table([
        ["Endpoint Route", "HTTP Method", "View / Callable", "Input Parameters", "JSON Output Format"],
        ["/courses/api/search/", "GET", "course_search_api", "?q=search_term", "{'results': [{'title': '...', 'slug': '...', 'price': '89.00', 'level': '...', 'url': '...'}]}"],
        ["/courses/lesson/<id>/complete/", "POST", "MarkCompleteView", "lesson_id in URL", "{'success': True, 'is_completed': True, 'progress_percent': 75.0, 'completed_count': 3, 'total_count': 4}"],
        ["/courses/<slug>/preview/<id>/", "GET", "lesson_preview_api", "slug, lesson_id", "{'success': True, 'title': '...', 'video_url': '...', 'content': '...', 'duration': '14:20'}"],
        ["/payments/webhook/stripe/", "POST", "stripe_webhook", "Stripe JSON payload", "HTTP 200 with empty body upon successful verification"]
    ], [130, 60, 105, 100, 145]))

    story.append(h2("13.2 DRF Concepts for Technical Evaluation (Viva Reference)"))
    story.append(p(
        "If asked by an evaluator how Django REST Framework (DRF) works and how it compares to Learnix's native endpoints:"
    ))
    story.append(bullet("<b>What DRF is:</b> A powerful third-party toolkit for building Web APIs in Django, providing serializers, viewsets, browsable APIs, and authentication classes."))
    story.append(bullet("<b>Serializers (serializers.ModelSerializer):</b> Converts complex model instances and querysets into native Python datatypes that can easily be rendered into JSON or XML. Also provides deserialization and validation (is_valid(), save())."))
    story.append(bullet("<b>APIView vs. Standard View:</b> APIView subclasses Django's View, wraps requests in DRF's Request class (which parses request.data automatically), and returns Response objects with proper content negotiation."))
    story.append(bullet("<b>Comparison:</b> Learnix currently uses JsonResponse for lightweight AJAX calls (search, lesson progress). If Learnix were to expose a public mobile app API or third-party developer API, DRF would be introduced to handle token authentication, pagination, and OpenAPI schema generation."))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 14: FORMS AND VALIDATION
    # =========================================================================
    story.append(h1("14. Forms & Input Validation"))
    story.append(hr())
    story.append(p(
        "Forms in Django protect the database by validating, sanitizing, and casting raw HTTP POST data. "
        "Learnix defines forms in <b>accounts/forms.py</b>:"
    ))

    story.append(h2("14.1 StudentRegistrationForm (ModelForm)"))
    story.append(bullet("<b>Model Binding:</b> Subclasses forms.ModelForm bound to auth.User (fields: first_name, last_name, username, email)."))
    story.append(bullet("<b>Custom Password Fields:</b> Defines password and confirm_password with PasswordInput widgets and Tailwind CSS classes."))
    story.append(bullet("<b>Field Validation (clean_email):</b> Normalizes email to lowercase, strips trailing whitespace, and verifies that no existing User already holds the address."))
    story.append(bullet("<b>Cross-Field Validation (clean):</b> Compares password and confirm_password to ensure equality, and checks that password length is at least 8 characters."))

    story.append(code_box("""# accounts/forms.py — clean_email() and clean()
def clean_email(self):
    email = self.cleaned_data.get("email", "").lower().strip()
    if not email:
        raise ValidationError("A valid email address is required.")
    if User.objects.filter(email=email).exists():
        raise ValidationError("An account with this email address already exists.")
    return email

def clean(self):
    cleaned_data = super().clean()
    p1 = cleaned_data.get("password")
    p2 = cleaned_data.get("confirm_password")
    if p1 and p2 and p1 != p2:
        self.add_error("confirm_password", "Passwords do not match.")
    if p1 and len(p1) < 8:
        self.add_error("password", "Password must be at least 8 characters long.")
    return cleaned_data""", "accounts/forms.py — Registration Form Validation"))

    story.append(h2("14.2 OTPVerificationForm & UserLoginForm"))
    story.append(bullet("<b>OTPVerificationForm:</b> Standard forms.Form with a single 6-digit field (otp_code). clean_otp_code() enforces exactly 6 numeric digits using code.isdigit()."))
    story.append(bullet("<b>UserLoginForm:</b> Subclasses Django's AuthenticationForm, adding modern glassmorphic Tailwind styling to username and password inputs."))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 15: SECURITY ARCHITECTURE
    # =========================================================================
    story.append(h1("15. Security Architecture"))
    story.append(hr())
    story.append(p(
        "Learnix is engineered with multi-layered defense-in-depth security principles across authentication, "
        "data persistence, session handling, and external gateway communication."
    ))

    story.append(h2("15.1 Implemented Defenses in Learnix"))
    story.append(create_table([
        ["Threat Vector", "Defense Mechanism", "Implementation in Learnix"],
        ["Cross-Site Request Forgery (CSRF)", "Cryptographic token verification on all POST actions.", "CsrfViewMiddleware enabled; {% csrf_token %} on all forms; X-CSRFToken headers on AJAX."],
        ["SQL Injection (SQLi)", "Parameterized database queries via ORM.", "100% of queries use Django ORM (filter, get, create). Zero raw SQL string concatenation."],
        ["Cross-Site Scripting (XSS)", "Automatic HTML entity escaping.", "Django Template Engine auto-escapes all variables ({{ var }}). mark_safe() restricted to sanitized badges."],
        ["Clickjacking", "Frame embedding prevention.", "XFrameOptionsMiddleware sends 'X-Frame-Options: SAMEORIGIN' header, preventing iframe overlays."],
        ["Credential Sniffing & Hijacking", "Session cookie protection.", "SESSION_COOKIE_HTTPONLY=True prevents client-side JS theft; SESSION_COOKIE_AGE=1209600 (2 weeks)."],
        ["Brute-Force OTP Guessing", "Maximum attempt ceiling and rate limiting.", "EmailOTP locks after 5 attempts; ResendOTPView enforces 60-second cooldown."],
        ["Webhook Forgery", "Cryptographic signature validation.", "stripe_webhook verifies HMAC-SHA256 signature using stripe.Webhook.construct_event."],
        ["Secret Key Exposure", "Decoupled environment configuration.", "All keys (SECRET_KEY, STRIPE_SECRET_KEY, DB passwords) stored in .env and loaded via decouple."]
    ], [110, 160, 270]))

    story.append(h2("15.2 Production Hardening Recommendations (Future Roadmap)"))
    story.append(p(
        "When deploying Learnix to a live production domain with an SSL/TLS certificate, the following settings "
        "are configured (already structured in learnix_project/settings.py under if not DEBUG):"
    ))
    story.append(bullet("<b>SECURE_SSL_REDIRECT = True:</b> Automatically redirects all plain HTTP requests to HTTPS."))
    story.append(bullet("<b>SESSION_COOKIE_SECURE = True:</b> Guarantees session cookies are only transmitted over encrypted HTTPS."))
    story.append(bullet("<b>CSRF_COOKIE_SECURE = True:</b> Ensures CSRF tokens are strictly transmitted over HTTPS."))
    story.append(bullet("<b>SECURE_HSTS_SECONDS = 31536000:</b> Instructs browsers to only connect via HTTPS for 1 year (HTTP Strict Transport Security)."))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 16: ERROR HANDLING & SYSTEM RESILIENCE
    # =========================================================================
    story.append(h1("16. Error Handling & System Resilience"))
    story.append(hr())
    story.append(p(
        "Learnix enforces structured exception handling, custom domain error hierarchies, and branded user-facing "
        "error templates to prevent server crashes and sensitive stack trace leaks."
    ))

    story.append(h2("16.1 Custom Domain Exception Hierarchy (core/exceptions.py)"))
    story.append(code_box("""# core/exceptions.py
class LearnixBaseException(Exception):
    def __init__(self, message="An internal business logic error occurred.", code="INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class PaymentVerificationFailedException(LearnixBaseException):
    def __init__(self, message="The payment verification check failed."):
        super().__init__(message=message, code="PAYMENT_VERIFICATION_FAILED")

class CourseAccessDeniedException(LearnixBaseException):
    def __init__(self, message="Enrollment required to access course content."):
        super().__init__(message=message, code="ACCESS_DENIED")

class OTPExpiredException(LearnixBaseException):
    def __init__(self, message="This OTP has expired. Please request a new verification code."):
        super().__init__(message=message, code="OTP_EXPIRED")""",
        "core/exceptions.py — Custom Domain Exception Hierarchy"))

    story.append(h2("16.2 Custom HTTP Status Handlers"))
    story.append(create_table([
        ["HTTP Status Code", "Handler Function", "Template Rendered", "Trigger Condition & User Experience"],
        ["404 Not Found", "core.views.custom_page_not_found_view", "templates/404.html", "Triggered when slug or pk does not exist. Renders whimsical deep-space graphic with return CTA."],
        ["500 Server Error", "core.views.custom_server_error_view", "templates/500.html", "Triggered upon unhandled Python runtime exception. Renders reactor alert page without exposing traceback."],
        ["403 Forbidden", "core.views.custom_permission_denied_view", "templates/403.html", "Triggered upon PermissionDenied (e.g. downloading another user's invoice). Renders security intercept page."]
    ], [80, 150, 110, 200]))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 17: COMPLETE REQUEST LIFECYCLE TRACES
    # =========================================================================
    story.append(h1("17. Complete Request Lifecycle Traces"))
    story.append(hr())
    story.append(p(
        "To synthesize how all components interconnect, this section traces five complete real-world requests "
        "from the initial browser action to database writes and final HTTP responses."
    ))

    traces = [
        ("Lifecycle 1: Two-Phase Student Registration & OTP Verification",
         "1. Browser POST /accounts/signup/ with form data (alex_vance, alex@learnix.com, password).\n"
         "2. CsrfViewMiddleware validates CSRF token; URL router directs to SignUpView.post().\n"
         "3. StudentRegistrationForm.is_valid() runs clean_email() and clean().\n"
         "4. User created in PostgreSQL with is_active=False and password hashed via PBKDF2.\n"
         "5. EmailOTP.create_for_user() generates 6-digit code (e.g. '849201') with 10-minute expiry.\n"
         "6. send_mail() dispatches code to alex@learnix.com from shahbazbutt22ee@gmail.com.\n"
         "7. View stores session['otp_user_id'] = user.id and redirects (302) to /accounts/verify-otp/.\n"
         "8. Student enters '849201'; VerifyOTPView checks expiry (<10m) and attempts (<5).\n"
         "9. User activated (is_active=True); login() creates session; welcome email sent; redirected to /accounts/profile/."),

        ("Lifecycle 2: Credentials Login & Session Creation",
         "1. Browser POST /accounts/login/ with username='alex_vance' and password.\n"
         "2. UserLoginView invokes UserLoginForm; calls authenticate(username, password).\n"
         "3. Django queries auth_user, hashes submitted password, and compares against stored hash.\n"
         "4. If valid, login(request, user) is invoked: generates unique 32-character session_key.\n"
         "5. Session data stored in django_session PostgreSQL table; Set-Cookie: sessionid=... header attached.\n"
         "6. View redirects to next parameter URL or /accounts/profile/ with success flash message."),

        ("Lifecycle 3: Paid Course Purchase via Stripe Hosted Checkout & Webhook",
         "1. Student clicks 'Enroll & Instant Access' (POST /payments/checkout/ai-swarms/).\n"
         "2. CreateCheckoutSessionView checks enrollment (none); creates pending PaymentTransaction (#LRN-84920).\n"
         "3. stripe.checkout.Session.create() called with unit_amount=8900 ($89), payment_method_types=['card'], and metadata.\n"
         "4. View redirects (302/303) to Stripe's hosted URL (https://checkout.stripe.com/c/pay/cs_test_...).\n"
         "5. Student enters test card details on Stripe; Stripe executes authorization.\n"
         "6. Stripe server POSTs 'checkout.session.completed' event to /payments/webhook/stripe/.\n"
         "7. stripe_webhook verifies HMAC-SHA256 signature; extracts order_number from metadata.\n"
         "8. Inside db_transaction.atomic(): marks PaymentTransaction COMPLETED, creates active Enrollment, generates formal Invoice.\n"
         "9. send_order_confirmation_email() dispatches PDF receipt email from shahbazbutt22ee@gmail.com.\n"
         "10. Browser redirected to /payments/success/?order=LRN-84920; celebratory onboarding page rendered."),

        ("Lifecycle 4: Live AJAX Course Search Modal",
         "1. Student types 'Django' into the search input in the global navigation bar.\n"
         "2. JavaScript debounce triggers fetch('/courses/api/search/?q=Django').\n"
         "3. course_search_api view receives request; executes Course.objects.filter(is_published=True).\n"
         "4. Applies Q(title__icontains='Django') | Q(short_description__icontains='Django').\n"
         "5. Serializes matching records into a list of dictionaries.\n"
         "6. Returns JsonResponse({'results': [...]}) with HTTP 200.\n"
         "7. Client JavaScript parses JSON and renders course preview cards in the dropdown dynamically."),

        ("Lifecycle 5: Async Lesson Completion & Automated Certificate Trigger",
         "1. Enrolled student clicks 'Mark Complete' on lesson player page.\n"
         "2. JavaScript executes fetch('/courses/lesson/12/complete/', {method: 'POST', headers: {'X-CSRFToken': token}}).\n"
         "3. MarkCompleteView verifies authentication and enrollment.\n"
         "4. LessonProgress.objects.get_or_create(user=user, lesson=lesson) updates is_completed=True.\n"
         "5. enrollment.calculate_progress() recalculates percentage: 10/10 lessons completed = 100.00%.\n"
         "6. calculate_progress() triggers Certificate.issue_for_enrollment(): generates SHA-256 ledger hash.\n"
         "7. View returns JsonResponse({'success': True, 'progress_percent': 100.0, 'completed_count': 10}).\n"
         "8. Frontend updates progress bar to 100% and displays 'Certificate Unlocked' banner without full page reload.")
    ]

    for title, trace_text in traces:
        story.append(h2(f"17.{traces.index((title, trace_text)) + 1} {title}"))
        story.append(code_box(trace_text, f"Step-by-Step Execution Trace — {title}"))
        story.append(spacer(4))

    story.append(PageBreak())
    return story
