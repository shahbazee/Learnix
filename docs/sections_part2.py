"""
Sections 6 to 11 for Learnix Technical Documentation:
6. URLs and Routing
7. Views and Business Logic
8. Authentication System (Two-Phase OTP)
9. Google Sign-In / Google OAuth
10. Centralized Email Subsystem
11. Stripe Integration — Complete A-to-Z
"""

from .doc_builder import (
    p, bullet, h1, h2, h3, spacer, hr, code_box, callout, viva_qa, create_table
)
from reportlab.platypus import PageBreak

def build_part2():
    story = []

    # =========================================================================
    # SECTION 6: URLS AND ROUTING
    # =========================================================================
    story.append(h1("6. URLs and Routing Architecture"))
    story.append(hr())
    story.append(p(
        "Routing in Django connects incoming HTTP request paths to callable views. "
        "Learnix employs a hierarchical routing design: the master router (<b>learnix_project/urls.py</b>) "
        "delegates subpaths to individual app routers using the <b>include()</b> function."
    ))

    story.append(h2("6.1 Master Route Delegation Table"))
    story.append(create_table([
        ["URL Pattern / Prefix", "Delegated App / Target View", "Namespace / Name", "Purpose & Role"],
        ["admin/", "django.contrib.admin.site.urls", "admin:index", "Django built-in administrative portal."],
        ["accounts/", "include('accounts.urls')", "accounts:*", "Registration, OTP verification, login, logout, profile."],
        ["courses/", "include('courses.urls')", "courses:*", "Catalog, masterclass detail, lessons, certificates, studio."],
        ["payments/", "include('payments.urls')", "payments:*", "Stripe Checkout, success, cancel, billing hub, invoices, webhooks."],
        ["dashboard/", "courses.views.StudentDashboardView", "courses:dashboard", "Direct top-level student learning hub."],
        ["", "include('core.urls')", "core:*", "Root landing page (home) and platform about page."]
    ], [110, 150, 110, 170]))

    story.append(h2("6.2 Complete URL-to-Response Pipeline for All App Routes"))
    story.append(p(
        "The table below shows the complete pipeline: <b>URL -> View -> Business Logic -> Database -> Response</b>:"
    ))
    story.append(create_table([
        ["Route Pattern", "View Name", "Business Logic & Database Action", "Response Returned"],
        ["/", "HomeView", "Queries published courses, computes metrics.", "200 HTML (core/home.html)"],
        ["about/", "AboutView", "Renders faculty directory & benchmarks.", "200 HTML (core/about.html)"],
        ["accounts/signup/", "SignUpView", "Validates input, creates inactive user, creates EmailOTP, sends email.", "302 Redirect (/accounts/verify-otp/)"],
        ["accounts/verify-otp/", "VerifyOTPView", "Checks expiry, throttles attempts, activates user, creates session.", "302 Redirect (/accounts/profile/)"],
        ["accounts/resend-otp/", "ResendOTPView", "Enforces 60s rate limit, creates fresh EmailOTP, sends email.", "302 Redirect (/accounts/verify-otp/)"],
        ["accounts/login/", "UserLoginView", "Authenticates credentials, starts authenticated session cookie.", "302 Redirect (next or /profile/)"],
        ["accounts/logout/", "UserLogoutView", "Flushes active session cookie.", "302 Redirect (/)"],
        ["accounts/profile/", "ProfileView", "Fetches UserProfile and active enrollment count.", "200 HTML (accounts/profile.html)"],
        ["courses/", "CourseListView", "Filters published courses by category, level, and search keywords.", "200 HTML (courses/course_list.html)"],
        ["courses/<slug>/", "CourseDetailView", "Fetches course, modules, lessons; checks enrollment status.", "200 HTML (courses/course_detail.html)"],
        ["courses/<slug>/learn/<id>/", "LessonView", "EnrolledCourseRequiredMixin checks access; renders lesson player.", "200 HTML (lesson_player.html)"],
        ["courses/lesson/<id>/complete/", "MarkCompleteView", "Toggles LessonProgress.is_completed; recalculates enrollment progress.", "200 JSON ({'success': true, 'progress': X})"],
        ["courses/api/search/", "course_search_api", "Queries Course by title/description for live search modal.", "200 JSON ({'results': [...]})"],
        ["courses/<slug>/preview/<id>/", "lesson_preview_api", "Checks lesson.is_preview; returns preview video URL.", "200 JSON ({'video_url': ...})"],
        ["courses/certificates/<id>/", "CertificateDetailView", "Verifies certificate hash publicly on ledger page.", "200 HTML (certificate_detail.html)"],
        ["courses/certificates/<id>/download/", "DownloadCertificatePDFView", "Generates landscape certificate PDF via xhtml2pdf.", "200 Binary PDF Stream"],
        ["payments/checkout/<slug>/", "CreateCheckoutSessionView", "Creates pending PaymentTransaction, calls Stripe Checkout API.", "302/303 Redirect to checkout.stripe.com"],
        ["payments/success/", "PaymentSuccessView", "Fulfills order (fallback); renders celebration page.", "200 HTML (payments/success.html)"],
        ["payments/cancel/", "PaymentCancelView", "Renders aborted checkout notice with retry link.", "200 HTML (payments/cancel.html)"],
        ["payments/billing/", "BillingHubView", "Queries user transactions and invoices for billing hub.", "200 HTML (payments/billing_hub.html)"],
        ["payments/invoice/<num>/download/", "DownloadInvoicePDFView", "Generates and streams formal PDF tax invoice.", "200 Binary PDF Stream"],
        ["payments/webhook/stripe/", "stripe_webhook", "Validates HMAC-SHA256 signature; fulfills enrollment atomically.", "200 HTTP OK"]
    ], [115, 105, 195, 125]))

    story.append(h2("6.3 URL Parameter Converters and Reverse Resolution"))
    story.append(bullet("<b>Path Converters:</b> &lt;slug:slug&gt; matches lowercase alphanumeric characters with hyphens; &lt;int:lesson_id&gt; converts numeric strings into Python integers; &lt;str:certificate_id&gt; matches non-empty strings."))
    story.append(bullet("<b>Reverse Resolution:</b> Eliminates hardcoded URLs. reverse('courses:course_detail', kwargs={'slug': 'ai-swarms'}) generates '/courses/ai-swarms/' dynamically. In templates: {% url 'courses:course_detail' course.slug %}."))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 7: VIEWS AND BUSINESS LOGIC
    # =========================================================================
    story.append(h1("7. Views & Business Logic"))
    story.append(hr())
    story.append(p(
        "Views represent the processing engine of Learnix. Learnix leverages Django's "
        "<b>Class-Based Views (CBVs)</b> for standard pages and clean <b>Function-Based Views (FBVs)</b> "
        "for specialized JSON endpoints and webhook listeners."
    ))

    story.append(h2("7.1 Class-Based View Hierarchy Used in Learnix"))
    story.append(create_table([
        ["Django Generic CBV", "Learnix Implementation Views", "Why this CBV was Chosen"],
        ["FormView", "SignUpView, VerifyOTPView", "Automates form validation, error re-rendering, and success redirection."],
        ["ListView", "CourseListView", "Built-in pagination, automatic query execution, and template context binding."],
        ["DetailView", "CourseDetailView, LessonView, CertificateDetailView", "Automatically fetches single model instance by pk or slug; handles 404 if missing."],
        ["TemplateView", "HomeView, AboutView, StudentDashboardView, BillingHubView, ProfileView", "Renders rich static/dynamic templates with custom get_context_data() dictionary."],
        ["LoginView / LogoutView", "UserLoginView, UserLogoutView", "Inherits Django's secure authentication and session management hooks."],
        ["View (Base CBV)", "CreateCheckoutSessionView, EnrollCourseView, MarkCompleteView, ResendOTPView, PDF Views", "Provides granular control over HTTP methods (get, post) without form/template boilerplate."]
    ], [110, 180, 250]))

    story.append(h2("7.2 Code Walkthrough: CreateCheckoutSessionView"))
    story.append(p(
        "The <b>CreateCheckoutSessionView</b> in <b>payments/views.py</b> coordinates the official Stripe Hosted Checkout flow:"
    ))
    story.append(code_box("""# payments/views.py
class CreateCheckoutSessionView(LoginRequiredMixin, View):
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_published=True)

        # 1. Prevent duplicate purchase if student already has active enrollment
        if request.user.enrollments.filter(course=course, is_active=True).exists():
            messages.info(request, f"You are already enrolled in {course.title}.")
            return redirect('courses:dashboard')

        # 2. Handle Free Courses (Tuition = $0.00)
        if course.is_free:
            with db_transaction.atomic():
                order_num = PaymentTransaction.generate_order_number()
                tx, _ = PaymentTransaction.objects.get_or_create(
                    user=request.user, course=course,
                    defaults={'order_number': order_num, 'amount': Decimal('0.00'), 'status': 'COMPLETED'}
                )
                Enrollment.objects.get_or_create(user=request.user, course=course, defaults={'is_active': True})
                inv, _ = Invoice.objects.get_or_create(transaction=tx, defaults={...})
            send_order_confirmation_email(request.user, course, tx, inv)
            return redirect(f"{reverse('payments:payment_success')}?order={tx.order_number}")

        # 3. Create or retrieve pending order
        tx, _ = PaymentTransaction.objects.get_or_create(
            user=request.user, course=course, status='PENDING',
            defaults={'order_number': PaymentTransaction.generate_order_number(), 'amount': course.price}
        )

        # 4. Initiate Stripe Official Hosted Checkout Session
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            checkout_session = stripe.checkout.Session.create(
                customer_email=request.user.email or None,
                payment_method_types=['card'], # Forces card only (disables Apple/Google Pay)
                line_items=[{
                    'price_data': {
                        'currency': settings.STRIPE_CURRENCY.lower(),
                        'product_data': {'name': course.title, 'description': course.short_description[:200]},
                        'unit_amount': int(course.price * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata={'user_id': str(request.user.id), 'course_id': str(course.id), 'order_number': str(tx.order_number)},
                success_url=request.build_absolute_uri(f"{reverse('payments:payment_success')}?session_id={{CHECKOUT_SESSION_ID}}&order={tx.order_number}"),
                cancel_url=request.build_absolute_uri(f"{reverse('payments:payment_cancel')}?order={tx.order_number}"),
            )
            tx.stripe_checkout_session_id = checkout_session.id
            tx.save(update_fields=['stripe_checkout_session_id'])
            return redirect(checkout_session.url)
        except stripe.error.AuthenticationError:
            messages.error(request, "Stripe configuration error: A valid secret key is required.")
            return redirect('courses:course_detail', slug=course.slug)""",
        "payments/views.py — CreateCheckoutSessionView Line-by-Line"))

    story.append(callout("Key Business Logic Decisions in CreateCheckoutSessionView",
        "• Idempotency: Checks active enrollment first to prevent duplicate charges.<br/>"
        "• Free Courses: Bypass payment gateway entirely and fulfill access immediately in an atomic transaction.<br/>"
        "• Card Only: payment_method_types=['card'] removes Apple Pay and Google Pay express buttons.<br/>"
        "• Graceful Degradation: If Stripe authentication fails, an informative message alerts the administrator.", "info"))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 8: AUTHENTICATION SYSTEM
    # =========================================================================
    story.append(h1("8. Authentication System (Two-Phase OTP)"))
    story.append(hr())
    story.append(p(
        "Learnix features a production-grade <b>Two-Phase Registration and Verification System</b>. "
        "Unlike basic Django apps that activate users immediately upon form submission, Learnix prevents "
        "fake accounts and spam by enforcing cryptographic email verification."
    ))

    story.append(h2("8.1 The Two-Phase Lifecycle Step-by-Step"))
    story.append(bullet("<b>Phase 1: Registration Form Submission (SignUpView):</b><br/>"
                        "1. Student fills out StudentRegistrationForm (first_name, last_name, username, email, password, confirm_password).<br/>"
                        "2. Form runs clean_email() (uniqueness) and clean() (password match, minimum 8 characters).<br/>"
                        "3. View creates user with <b>is_active=False</b> (inactive).<br/>"
                        "4. View calls EmailOTP.create_for_user(user): generates 6-digit code via secrets.choice('0123456789') with a 10-minute validity.<br/>"
                        "5. View stores request.session['otp_user_id'] and request.session['otp_last_sent'].<br/>"
                        "6. Dispatches transactional email with the code and redirects to /accounts/verify-otp/."))

    story.append(bullet("<b>Phase 2: Code Verification (VerifyOTPView):</b><br/>"
                        "1. Student submits 6-digit code in OTPVerificationForm.<br/>"
                        "2. Checks if pending user exists in session (guards against direct URL access).<br/>"
                        "3. Checks if OTP is expired (now > expires_at): rejects if > 10 minutes.<br/>"
                        "4. Checks brute-force ceiling (attempts_count >= 5): locks OTP if 5 failed tries occur.<br/>"
                        "5. Checks code equality: increments attempts_count if wrong; displays remaining tries.<br/>"
                        "6. If correct: marks otp_record.is_verified=True, sets <b>user.is_active=True</b>, logs user in via login(), cleans session keys, dispatches welcome email from shahbazbutt22ee@gmail.com, and redirects to profile."))

    story.append(bullet("<b>Rate-Limited Resend (ResendOTPView):</b><br/>"
                        "Enforces a strict 60-second cooldown rate limit using request.session['otp_last_sent']. If the user clicks Resend before 60 seconds, a warning shows the exact remaining cooldown seconds."))

    story.append(h2("8.2 Security Considerations in Authentication"))
    story.append(create_table([
        ["Security Vector", "Learnix Defense Implementation", "Underlying Technology"],
        ["Password Storage", "Passwords are never stored in plain text. Hashed using salt.", "PBKDF2 with SHA-256 algorithm (1,000,000 iterations)."],
        ["Session Hijacking", "Session cookie is marked HttpOnly, preventing JavaScript access.", "SESSION_COOKIE_HTTPONLY = True; signed sessionid cookie."],
        ["Brute-Force OTP", "Maximum 5 verification attempts allowed per generated OTP code.", "EmailOTP.MAX_ATTEMPTS = 5; attempts_count incremented on mismatch."],
        ["OTP Expiration", "Code expires strictly after 10 minutes from issuance.", "EmailOTP.EXPIRY_MINUTES = 10; compared against timezone.now()."],
        ["Email Flooding", "Resending OTP is throttled to once every 60 seconds per user session.", "ResendOTPView.RATE_LIMIT_SECONDS = 60 checked via session timestamp."],
        ["Account Spoofing", "Users cannot log in until their email is cryptographically verified.", "user.is_active = False set at signup; activated only in VerifyOTPView."]
    ], [110, 250, 180]))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 9: GOOGLE SIGN-IN / GOOGLE OAUTH
    # =========================================================================
    story.append(h1("9. Google Sign-In & OAuth 2.0 Architecture"))
    story.append(hr())
    story.append(p(
        "OAuth 2.0 (Open Authorization) is an industry-standard delegation protocol that allows users to grant "
        "third-party applications access to their identity on an identity provider (such as Google) "
        "without ever exposing their password to the application."
    ))

    story.append(h2("9.1 Actual Status in Learnix Codebase"))
    story.append(callout("Current Codebase Status: UI & Dependencies Ready (Backend Activation Planned)",
        "An inspection of the actual project files reveals:<br/>"
        "1. <b>requirements.txt</b> contains <b>django-allauth&gt;=65.0.0</b>.<br/>"
        "2. <b>templates/accounts/login.html</b> contains the branded Google OAuth button with SVG logo and label 'Continue with Google', currently pointing to <b>href='#'</b> as a UI placeholder.<br/>"
        "3. In <b>learnix_project/settings.py</b>, allauth is not yet added to INSTALLED_APPS, as authentication is currently fulfilled by the two-phase cryptographic Email OTP engine.<br/>"
        "This architectural design enables immediate drop-in activation of Google OAuth whenever production credentials are configured.", "warning"))

    story.append(h2("9.2 How Google OAuth Works (Evaluation Reference)"))
    story.append(p(
        "During an evaluation, an examiner may ask how Google OAuth works. The standard Authorization Code Flow operates as follows:"
    ))
    story.append(bullet("<b>1. Consent Request:</b> User clicks 'Continue with Google'. Browser redirects to Google Authorization Endpoint (https://accounts.google.com/o/oauth2/v2/auth) with client_id, redirect_uri, response_type='code', and scope='email profile'."))
    story.append(bullet("<b>2. User Consent:</b> Google authenticates the user and asks permission to share profile data with Learnix."))
    story.append(bullet("<b>3. Authorization Code Callback:</b> Google redirects browser back to Learnix's registered redirect URI (/accounts/google/login/callback/) with a temporary authorization code."))
    story.append(bullet("<b>4. Backend Token Exchange:</b> Learnix server securely contacts Google's token endpoint (https://oauth2.googleapis.com/token), sending authorization code + client_secret over TLS. Google returns an access_token."))
    story.append(bullet("<b>5. User Profile Retrieval & Session:</b> Learnix queries Google UserInfo API, retrieves verified email, creates or retrieves the Django User, and establishes a Django session."))

    story.append(h2("9.3 Step-by-Step Activation Guide for Learnix"))
    story.append(p("To enable Google OAuth in Learnix, the following additions are made to settings.py:"))
    story.append(code_box("""# learnix_project/settings.py (When activating Google OAuth)
INSTALLED_APPS += [
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]
SITE_ID = 1
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID'),
            'secret': config('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}""", "Google OAuth Configuration Template for django-allauth"))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 10: EMAIL SYSTEM
    # =========================================================================
    story.append(h1("10. Centralized Email Subsystem"))
    story.append(hr())
    story.append(p(
        "Learnix implements a centralized, production-grade email subsystem in <b>payments/services.py</b>. "
        "Every platform notification is sent strictly from the centralized administrator address: "
        "<b>shahbazbutt22ee@gmail.com</b>."
    ))

    story.append(h2("10.1 Email Configuration & Environment Decoupling"))
    story.append(create_table([
        ["Setting Variable", "Configured Value in Learnix", "Purpose & Explanation"],
        ["EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend", "Console backend in development; prints emails to terminal without requiring live SMTP."],
        ["EMAIL_HOST", "smtp.gmail.com", "Google SMTP mail exchange server address."],
        ["EMAIL_PORT", "587", "Standard TLS port for secure authenticated mail transmission."],
        ["EMAIL_USE_TLS", "True", "Enforces Transport Layer Security (TLS) encryption on the SMTP socket."],
        ["EMAIL_HOST_USER", "shahbazbutt22ee@gmail.com", "Centralized authenticating email account."],
        ["DEFAULT_FROM_EMAIL", "Learnix <shahbazbutt22ee@gmail.com>", "Sender header appearing on all outbound communications."]
    ], [130, 200, 210]))

    story.append(h2("10.2 The 4 Types of Learnix Platform Emails"))
    story.append(bullet("<b>1. Registration OTP Verification Email:</b> Dispatched by SignUpView and ResendOTPView. Contains the 6-digit cryptographic verification code and 10-minute expiry warning."))
    story.append(bullet("<b>2. Registration Welcome Email:</b> Dispatched by send_registration_welcome_email(user) upon successful account activation. Welcomes the student to Learnix."))
    story.append(bullet("<b>3. Password Reset OTP Email:</b> Dispatched by send_password_reset_otp_email(user, otp_code). Contains password recovery code."))
    story.append(bullet("<b>4. Order Confirmation & Tuition Receipt Email:</b> Dispatched by send_order_confirmation_email(user, course, transaction, invoice). Includes course name, order number, amount paid, and dashboard link."))

    story.append(h2("10.3 Dual-Mode HTML & Plaintext Fallback Pattern"))
    story.append(p(
        "Every email in Learnix utilizes dual-mode rendering: it compiles a rich HTML email template "
        "(templates/emails/) using render_to_string(), generates an automatic plain text version using "
        "strip_tags(), and gracefully falls back to plain text if the template engine encounters an error."
    ))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 11: STRIPE INTEGRATION COMPLETE A-TO-Z
    # =========================================================================
    story.append(h1("11. Stripe Integration — Complete A-to-Z"))
    story.append(hr())
    story.append(p(
        "The Learnix payment infrastructure is built on <b>Stripe Hosted Checkout</b> in Test/Sandbox Mode. "
        "The architecture completely avoids collecting sensitive card credentials on Learnix servers, "
        "achieving PCI-DSS Level 1 compliance by delegating payment details directly to Stripe's secure hosted domain."
    ))

    story.append(h2("11.1 The Exact End-to-End Payment Flow"))
    story.append(bullet("<b>Step 1: Student Clicks Buy / Enroll Button:</b> On the course detail page (course_detail.html), student clicks 'Enroll & Instant Access'. This submits a POST request to /payments/checkout/&lt;course_slug&gt;/."))
    story.append(bullet("<b>Step 2: CreateCheckoutSessionView Invocation:</b><br/>"
                        "• Checks if student already has an active Enrollment. If yes, redirects to dashboard.<br/>"
                        "• Checks if course is free (price = 0.00). If yes, grants immediate access and redirects to success.<br/>"
                        "• Creates or retrieves a pending PaymentTransaction record with status='PENDING'.<br/>"
                        "• Invokes stripe.checkout.Session.create() with: customer_email, payment_method_types=['card'], line_items (unit_amount in cents), mode='payment', metadata (user_id, course_id, order_number), success_url, and cancel_url.<br/>"
                        "• Saves checkout_session.id on the transaction.<br/>"
                        "• Returns a redirect to checkout_session.url (https://checkout.stripe.com/...)."))
    story.append(bullet("<b>Step 3: Hosted Stripe Checkout & Digital Wallet Suppression:</b> The student is redirected to checkout.stripe.com. Because payment_method_types=['card'] is strictly specified, digital wallet overlays (Apple Pay, Google Pay) are removed in favor of standard card entry. The student enters test card 4242 4242 4242 4242."))
    story.append(bullet("<b>Step 4: Asynchronous Webhook Fulfillment (stripe_webhook):</b><br/>"
                        "• Stripe asynchronously POSTs the event payload to /payments/webhook/stripe/.<br/>"
                        "• Webhook verifies cryptographic signature using HMAC-SHA256 with STRIPE_WEBHOOK_SECRET.<br/>"
                        "• Upon event 'checkout.session.completed', extracts metadata: user_id, course_id, order_number.<br/>"
                        "• Opens an atomic transaction (db_transaction.atomic()):<br/>"
                        "  1. Updates PaymentTransaction: status='COMPLETED', saves payment_intent_id.<br/>"
                        "  2. Creates or activates Enrollment: is_active=True, progress_percent=0.00.<br/>"
                        "  3. Creates formal Invoice: generates invoice_number, saves total amount.<br/>"
                        "• Dispatches order receipt email from shahbazbutt22ee@gmail.com.<br/>"
                        "• Returns HTTP 200 to Stripe."))
    story.append(bullet("<b>Step 5: Browser Success Redirection (PaymentSuccessView):</b> Stripe redirects the student's browser back to /payments/success/?session_id={CHECKOUT_SESSION_ID}&order={order_number}. The view displays the celebratory enrollment onboarding page with a direct 'Launch Course Classroom' CTA."))

    story.append(h2("11.2 Why the Backend Must Not Trust the Frontend Alone"))
    story.append(callout("Critical Architectural Principle for Viva Evaluation",
        "A malicious user could manipulate client-side JavaScript or manually craft a URL to /payments/success/?order=LRN-12345 "
        "without paying. Therefore, Learnix relies on the <b>asynchronous Stripe Webhook</b> as the authoritative source of truth. "
        "The webhook is cryptographically signed by Stripe with HMAC-SHA256 and sent server-to-server. "
        "The frontend success page only fulfills transactions if they are verified against Stripe or already completed by the webhook.", "security"))

    story.append(h2("11.3 Webhook Implementation Code"))
    story.append(code_box("""# payments/webhooks.py
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400) # Invalid signature rejected

    if event.type == "checkout.session.completed":
        session = event.data.object
        meta = session.metadata
        with db_transaction.atomic():
            tx = PaymentTransaction.objects.get(order_number=meta.order_number)
            tx.status = "COMPLETED"
            tx.stripe_payment_intent_id = session.payment_intent
            tx.save()

            Enrollment.objects.get_or_create(user_id=meta.user_id, course_id=meta.course_id, defaults={'is_active': True})
            inv = Invoice.objects.create(transaction=tx, invoice_number=Invoice.generate_invoice_number(), ...)
            send_order_confirmation_email(tx.user, tx.course, tx, inv)
    return HttpResponse(status=200)""", "payments/webhooks.py — Cryptographic Webhook Handler"))

    story.append(PageBreak())
    return story
