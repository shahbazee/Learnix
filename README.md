# Learnix — Modern E-Learning & Engineering Education Platform

[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Stripe](https://img.shields.io/badge/Stripe-Payments-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

**Learnix** is a full-featured, enterprise-grade e-learning web platform built with Django. It provides an intuitive, high-performance learning environment for modern software engineering masterclasses, featuring interactive course players, verified credentials, instructor authoring tools, Stripe checkout, automated tax invoicing, and dual-phase OTP security.

---

## 🌟 Key Features

### 🎓 Student Experience & Learning Management
* **Curriculum Catalog**: Browse courses categorized by topic, difficulty level, and rating with live quick-search (⌘K).
* **Interactive Lesson Player**: Stream structured video lessons, track timestamps, and read accompanying technical lecture notes.
* **Granular Progress Telemetry**: Automatic completion tracking across lessons and modules with aggregate course progress percentages.
* **Verified Certificates**: Cryptographically verifiable certificates issued upon 100% course completion, featuring unique certificate IDs and public validation pages.
* **Student Dashboard**: Overview of all enrolled courses, active learning tracks, and billing history.

### 💳 Stripe Checkout & Automated Invoicing
* **Official Stripe Hosted Checkout**: Seamless checkout flow for premium courses using Stripe Checkout sessions.
* **Stripe Webhook Pipeline**: Listens for `checkout.session.completed` and `payment_intent.payment_failed` with signature verification and idempotency locks.
* **Instant Automated Tax Invoices**:
  - Automatically generates itemized PDF tax invoices using `xhtml2pdf`.
  - Dispatches immediate purchase confirmation and formal tax invoice emails (with attached PDF) to both the student's registered email and their Stripe billing email.
* **Student Billing Hub**: View order numbers, payment dates, amounts, and download PDF tax receipts directly from the dashboard.

### 🔐 Authentication & Security
* **Role-Based Access Control**: Strict separation between Student and Instructor permissions with anti-spoofing validation.
* **Two-Phase Email OTP**: Cryptographically secure 6-digit one-time passcodes with 10-minute expiry and 5-attempt brute-force protection.
* **Google OAuth 2.0**: Native Google Single Sign-On (SSO) with automated account creation, state validation, and profile synchronization.
* **Account Settings**: Manage user profiles, avatars, credentials, and notification preferences.

### 🛠️ Instructor Studio
* **Course Authoring**: Create, edit, and publish masterclasses with rich descriptions, pricing, and thumbnails.
* **Curriculum Builder**: Organize courses into sequential modules and rich video lessons.
* **Student Roster**: Track enrolled students, individual lesson completion rates, and enrollment dates.

---

## 🏗️ Architecture & Tech Stack

* **Framework**: Django 5.x (MVT architecture)
* **Language**: Python 3.12+
* **Database**: PostgreSQL 15+ (production) / SQLite (development)
* **Styling**: Tailwind CSS with custom glassmorphic UI design tokens
* **PDF Rendering**: `xhtml2pdf` / ReportLab for server-side invoice generation
* **Payments**: Stripe API & Stripe Webhooks
* **Email Engine**: Django SMTP backend with HTML and plain-text multipart email templates
* **Smooth Scrolling**: Lenis Smooth Scroll

---

## 📁 Project Structure

```text
Learnix/
├── accounts/               # Authentication, Profiles, OTP verification & Google OAuth
│   ├── forms.py            # User registration, login, and profile forms
│   ├── mixins.py           # Role-based access control mixins
│   ├── models.py           # UserProfile & EmailOTP models
│   ├── signals.py          # Automatic profile creation signals
│   └── views.py            # Login, Signup, OTP, Profile & OAuth views
├── courses/                # Curriculum catalog, lesson player & Instructor Studio
│   ├── models.py           # Category, Course, Module, Lesson, Enrollment, Certificate
│   ├── services.py         # Business logic for course progress & certificate issuance
│   └── views.py            # Course catalog, detail, lesson streaming & studio views
├── payments/               # Stripe checkout, webhooks & PDF invoicing
│   ├── models.py           # PaymentTransaction & Invoice models
│   ├── services.py         # Order fulfillment, PDF generation & email orchestration
│   ├── views.py            # Checkout creation, success/cancel views & Billing Hub
│   └── webhooks.py         # Stripe signature verification and webhook handlers
├── core/                   # Marketing views, error handlers & centralized email service
│   ├── emails.py           # Centralized email notification dispatchers (8 platform events)
│   └── views.py            # Landing page, about page, custom 403/404/500 handlers
├── learnix_project/        # Project settings, WSGI/ASGI configuration & root URLs
├── static/                 # Static CSS, JS libraries (Lenis), and UI assets
├── templates/              # Semantic Django templates
│   ├── accounts/           # Auth and profile templates
│   ├── courses/            # Catalog, dashboard, studio, and lesson player templates
│   ├── emails/             # Responsive HTML email templates
│   ├── payments/           # Billing hub, success, cancel & PDF invoice templates
│   └── base.html           # Base layout with navbar, footer, and search modal
├── manage.py               # Django management CLI
└── requirements.txt        # Production Python dependencies
```

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.12+
* PostgreSQL 15+ (or SQLite for local evaluation)
* Git
* [Stripe CLI](https://stripe.com/docs/stripe-cli) (optional, for local webhook testing)

### 2. Clone the Repository
```bash
git clone https://github.com/shahbazee/Learnix.git
cd Learnix
```

### 3. Create & Activate Virtual Environment
```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```

Key variables in `.env`:
```ini
DEBUG=True
SECRET_KEY=your-secure-django-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=learnix_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email / SMTP Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_email_app_password
DEFAULT_FROM_EMAIL=Learnix <your_email@gmail.com>
```

### 6. Apply Migrations & Seed Sample Data
```bash
python manage.py migrate
python manage.py seed_courses
```

### 7. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Testing

Learnix includes an automated test suite covering authentication, permissions, checkout workflows, webhook idempotency, PDF invoice generation, and email dispatchers.

Run all tests:
```bash
python manage.py test
```

Run tests with verbosity:
```bash
python manage.py test -v 2
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author
Developed by [Shahbaz Butt](https://github.com/shahbazee) — [shahbazbutt22ee@gmail.com](mailto:shahbazbutt22ee@gmail.com)
