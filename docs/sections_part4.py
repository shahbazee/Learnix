"""
Sections 18 to 22 for Learnix Technical Documentation:
18. Important Python Concepts Used in Learnix
19. Third-Party Libraries Reference Table
20. Environment and Configuration
21. Git and Project Workflow
22. Deployment & Production Architecture
"""

from .doc_builder import (
    p, bullet, h1, h2, h3, spacer, hr, code_box, callout, viva_qa, create_table
)
from reportlab.platypus import PageBreak

def build_part4():
    story = []

    # =========================================================================
    # SECTION 18: IMPORTANT PYTHON CONCEPTS USED IN MY PROJECT
    # =========================================================================
    story.append(h1("18. Important Python Concepts in Learnix"))
    story.append(hr())
    story.append(p(
        "A strong command of foundational and advanced Python language constructs is critical for technical interviews. "
        "Every concept below is mapped directly to actual lines of code in Learnix:"
    ))

    py_concepts = [
        ("Python Decorators (@wraps, @receiver, @csrf_exempt)",
         "Functions that take another function as an argument, extend or modify its behavior, and return a new function without altering the original source code.",
         "@receiver(post_save, sender=User) in accounts/signals.py; @enrolled_required in courses/decorators.py; @csrf_exempt in payments/webhooks.py.",
         "# courses/decorators.py\ndef enrolled_required(view_func):\n    @wraps(view_func)\n    def _wrapped_view(request, slug, *args, **kwargs):\n        if not request.user.is_authenticated:\n            return redirect('/accounts/login/')\n        # ... enrollment verification\n        return view_func(request, slug, *args, **kwargs)\n    return _wrapped_view"),

        ("Object-Oriented Programming (OOP) & Multiple Inheritance (Mixins)",
         "Creating reusable classes that encapsulate state and behavior. Mixins allow composable, multiple inheritance in Class-Based Views.",
         "EnrolledCourseRequiredMixin in accounts/mixins.py inheriting from AccessMixin; SignUpView inheriting from FormView.",
         "# courses/views.py\nclass LessonView(EnrolledCourseRequiredMixin, DetailView):\n    model = Lesson\n    template_name = 'courses/lesson_player.html'"),

        ("Context Managers & the 'with' Statement",
         "A Python protocol (__enter__ and __exit__) that guarantees setup and teardown actions (such as committing or rolling back a transaction).",
         "with db_transaction.atomic(): used in payments/views.py and payments/webhooks.py to wrap multi-table writes.",
         "# payments/views.py\nwith db_transaction.atomic():\n    tx.status = 'COMPLETED'\n    tx.save()\n    Enrollment.objects.get_or_create(user=user, course=course)\n    Invoice.objects.create(...)"),

        ("Cryptographic Randomness (secrets vs. random)",
         "The standard random module is pseudo-random and vulnerable to predictability attacks. Python's secrets module accesses the OS cryptographically secure entropy source.",
         "EmailOTP.create_for_user() in accounts/models.py uses secrets.choice() to generate tamper-proof 6-digit OTP codes.",
         "# accounts/models.py\nimport secrets\ndigits = '0123456789'\ncode = ''.join(secrets.choice(digits) for _ in range(6))"),

        ("Type Hinting (PEP 484)",
         "Explicitly annotating variable types and function return signatures to enhance code readability, IDE auto-completion, and static analysis.",
         "Used on model properties and helper methods across courses/models.py and courses/services.py.",
         "# courses/models.py\ndef calculate_progress(self) -> float:\n    # ...\n    return float(self.progress_percent)\n\ndef generate_certificate_id(cls) -> str:\n    return f'LRN-{suffix}-X'"),

        ("List, Set & Dictionary Comprehensions",
         "Concise, idiomatic syntax for transforming iterables into lists, sets, or dictionaries in a single readable line.",
         "Used in courses/models.py to calculate total duration and gather completed lesson IDs for sequential discovery.",
         "# courses/models.py\ncompleted_ids = set(\n    LessonProgress.objects.filter(\n        user=self.user, lesson__module__course=self.course, is_completed=True\n    ).values_list('lesson_id', flat=True)\n)"),

        ("String Manipulation & Slugs (django.utils.text.slugify)",
         "Converting human-readable strings into URL-safe ASCII tokens by stripping non-alphanumeric characters and replacing spaces with hyphens.",
         "CourseCategory.save() and Course.save() auto-generate slugs if not provided.",
         "# courses/models.py\nfrom django.utils.text import slugify\ndef save(self, *args, **kwargs):\n    if not self.slug:\n        self.slug = slugify(self.title)\n    super().save(*args, **kwargs)")
    ]

    for title, definition, where, code_sample in py_concepts:
        story.append(h2(f"18.{py_concepts.index((title, definition, where, code_sample)) + 1} {title}"))
        story.append(p(f"<b>Definition & Viva Concept:</b> {definition}"))
        story.append(p(f"<b>Where Used in Learnix:</b> {where}"))
        story.append(code_box(code_sample, f"Python Implementation in Learnix — {title}"))
        story.append(spacer(4))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 19: THIRD-PARTY LIBRARIES REFERENCE TABLE
    # =========================================================================
    story.append(h1("19. Third-Party Libraries Reference"))
    story.append(hr())
    story.append(p(
        "Learnix maintains a lean, highly vetted set of third-party dependencies specified in <b>requirements.txt</b>. "
        "The table below details every installed package, its rationale, and its actual usage in the project:"
    ))

    packages = [
        ["Package Name", "Version Range", "Why Installed & What Problem It Solves", "Key Modules / Classes Used in Code"],
        ["Django", ">=5.0, <6.1", "The primary high-level Python web framework providing ORM, MVT, auth, forms, and admin.", "django.db.models, django.views.generic, django.contrib.auth, django.forms"],
        ["psycopg", ">=3.2.0", "Next-generation PostgreSQL database driver for Python, supporting async I/O and connection pooling.", "django.db.backends.postgresql"],
        ["psycopg2-binary", ">=2.9.10", "Production-tested C-based PostgreSQL adapter for maximum query execution speed.", "Low-level TCP socket communication with PostgreSQL 15+."],
        ["python-decouple", ">=3.8", "Decouples settings parameters from operating system environment variables or .env files.", "from decouple import config, Csv in settings.py."],
        ["whitenoise", ">=6.8.0", "Allows Django to serve its own static files with Gzip/Brotli compression and cache headers.", "whitenoise.middleware.WhiteNoiseMiddleware, CompressedManifestStaticFilesStorage"],
        ["Pillow", ">=10.4.0", "Python Imaging Library enabling image processing, validation, and resizing for ImageFields.", "models.ImageField (UserProfile.avatar, Course.thumbnail)"],
        ["django-allauth", ">=65.0.0", "Comprehensive authentication suite for local accounts and social OAuth providers.", "Installed in requirements.txt; Google OAuth UI prepared in login.html."],
        ["stripe", ">=10.0.0", "Official Stripe Python SDK for managing hosted checkout sessions, charges, and webhooks.", "stripe.checkout.Session.create(), stripe.Webhook.construct_event"],
        ["xhtml2pdf", ">=0.2.16", "HTML/CSS to PDF converter engine using ReportLab, compiling styled templates to PDF.", "from xhtml2pdf import pisa in payments/services.py and courses/services.py"],
        ["reportlab", ">=4.2.0", "Low-level programmatic PDF generation library supporting flowables, canvases, and shapes.", "Used by xhtml2pdf and custom document generation scripts."],
        ["gunicorn", ">=23.0.0", "Production-grade WSGI HTTP Server for UNIX, managing worker pools behind reverse proxies.", "learnix_project.wsgi:application in production deployment."],
        ["requests", ">=2.32.0", "Elegant HTTP client library for sending synchronous REST requests to external web APIs.", "Used for HTTP communication and external service health checks."],
        ["dj-database-url", ">=2.1.0", "Parses DATABASE_URL environment strings (e.g. postgres://user:pass@host/db) into DATABASES dict.", "DATABASES['default'] = dj_database_url.config(...) in settings.py"]
    ]

    story.append(create_table(packages, [80, 70, 240, 150]))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 20: ENVIRONMENT AND CONFIGURATION
    # =========================================================================
    story.append(h1("20. Environment and Configuration"))
    story.append(hr())
    story.append(p(
        "Learnix adheres strictly to <b>The Twelve-Factor App</b> methodology: configuration is completely "
        "isolated from code and injected via environment variables through <b>python-decouple</b>."
    ))

    story.append(h2("20.1 Structure of the .env Configuration File"))
    story.append(code_box("""# Learnix Environment Configuration Template (.env)

# Core Django Secrets
SECRET_KEY=<cryptographically-random-50-character-secret>
DEBUG=True                                       # False in production
ALLOWED_HOSTS=localhost,127.0.0.1,testserver

# PostgreSQL Database (PostgreSQL 15+ ONLY)
DB_NAME=learnix_db
DB_USER=postgres
DB_PASSWORD=<secure-database-password>
DB_HOST=localhost
DB_PORT=5432
# DATABASE_URL=postgres://user:password@host:5432/learnix_db   # (Optional PaaS URL)

# Stripe Payment Gateway (Sandbox / Test Mode)
STRIPE_PUBLIC_KEY=pk_test_<your-stripe-publishable-key>
STRIPE_SECRET_KEY=sk_test_<your-stripe-secret-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-stripe-webhook-secret>
STRIPE_CURRENCY=usd

# Centralized Email Subsystem (shahbazbutt22ee@gmail.com)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend   # smtp backend in prod
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=shahbazbutt22ee@gmail.com
EMAIL_HOST_PASSWORD=<google-app-password>
DEFAULT_FROM_EMAIL=Learnix <shahbazbutt22ee@gmail.com>""",
        "Structure of .env File (Sensitive Credentials Masked)"))

    story.append(callout("Security Rule: Never Commit .env to Version Control",
        "The .env file contains database passwords, Stripe secret keys, and email credentials. "
        "It is strictly listed in <b>.gitignore</b> so that it is never checked into Git or pushed to GitHub. "
        "In production environments (Render, Heroku, AWS), these variables are injected through the hosting platform's secure dashboard.", "security"))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 21: GIT AND PROJECT WORKFLOW
    # =========================================================================
    story.append(h1("21. Git & Project Workflow"))
    story.append(hr())
    story.append(p(
        "Learnix is managed using Git version control, isolated virtual environments, and standardized requirements freezing."
    ))

    story.append(h2("21.1 Essential Git Workflow Commands"))
    story.append(bullet("<b>git status:</b> Inspects working directory changes and staged modifications."))
    story.append(bullet("<b>git add &lt;file&gt; / git add .:</b> Stages modified files for commit."))
    story.append(bullet("<b>git commit -m 'Descriptive message':</b> Records a snapshot of staged changes to the local repository."))
    story.append(bullet("<b>git push origin &lt;branch&gt;:</b> Transmits local commits to the remote GitHub repository."))
    story.append(bullet("<b>git pull origin &lt;branch&gt;:</b> Fetches and merges updates from the remote repository."))
    story.append(bullet("<b>git branch / git checkout -b &lt;name&gt;:</b> Manages isolated feature branches."))

    story.append(h2("21.2 The .gitignore Guardrails"))
    story.append(p("The following files and patterns are strictly ignored by Git to protect secrets and avoid bloat:"))
    story.append(bullet("<b>.env:</b> Contains secret keys and credentials."))
    story.append(bullet("<b>.venv/ / venv/:</b> Local virtual environment containing thousands of vendor package files."))
    story.append(bullet("<b>__pycache__/ / *.pyc:</b> Compiled Python bytecode files."))
    story.append(bullet("<b>staticfiles/:</b> Collected production static files generated by collectstatic."))
    story.append(bullet("<b>media/:</b> User-uploaded avatars and dynamic course thumbnails."))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 22: DEPLOYMENT & PRODUCTION ARCHITECTURE
    # =========================================================================
    story.append(h1("22. Deployment & Production Architecture"))
    story.append(hr())
    story.append(p(
        "Learnix is engineered for zero-downtime deployment on modern cloud platforms (Render, Heroku, AWS, or DigitalOcean). "
        "The production stack comprises:"
    ))

    story.append(bullet("<b>WSGI Application Server:</b> <b>Gunicorn</b> (Green Unicorn) running multi-worker concurrent Python processes."))
    story.append(bullet("<b>Static Asset Pipeline:</b> <b>WhiteNoise</b> with CompressedManifestStaticFilesStorage, generating unique MD5 hash suffixes for immutable cache busting."))
    story.append(bullet("<b>Managed Database:</b> Cloud PostgreSQL 15+ instance connected via DATABASE_URL and dj-database-url with persistent connection pooling (conn_max_age=600)."))
    story.append(bullet("<b>Reverse Proxy & SSL:</b> Cloudflare or platform reverse proxy terminating SSL/TLS certificates and forwarding HTTPS headers."))

    story.append(h2("22.1 Production Release Phase Commands"))
    story.append(p("During continuous deployment (e.g. Render build pipeline), the build script executes:"))
    story.append(code_box("""# Production Build & Release Script
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
gunicorn learnix_project.wsgi:application --bind 0.0.0.0:$PORT --workers 4""",
        "Standard Cloud Deployment Pipeline Commands"))

    story.append(PageBreak())
    return story
