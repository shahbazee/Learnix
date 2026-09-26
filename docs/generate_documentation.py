"""
Learnix E-Learning Platform - Master Backend Technical Documentation Generator
Compiles all 25 sections into a publication-grade PDF manual with running headers,
two-pass page numbering ("Page X of Y"), and complete syntax styling.
"""

import os
import sys
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle

from docs.doc_builder import (
    NumberedCanvas, p, bullet, h1, h2, h3, spacer, hr, code_box, callout,
    create_table, PRIMARY, PRIMARY_DARK, ACCENT_CYAN, DARK_SLATE, BORDER_LIGHT,
    BG_CODE, style_title, style_subtitle, style_meta, style_body, style_body_bold
)

from docs.sections_part1 import build_part1
from docs.sections_part2 import build_part2
from docs.sections_part3 import build_part3
from docs.sections_part4 import build_part4
from docs.sections_part5 import build_part5


def build_cover_page():
    """
    Renders an elegant, publication-quality cover page for the technical manual.
    """
    cover = []
    cover.append(Spacer(1, 40))

    # Badge pill
    badge_style = ParagraphStyle(
        'CoverBadge',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=PRIMARY,
        alignment=1
    )
    badge_table = Table([[Paragraph("★ OFFICIAL BACKEND ARCHITECTURE & VIVA PREPARATION MANUAL ★", badge_style)]], colWidths=[540])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EEF2FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#C7D2FE')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    cover.append(badge_table)
    cover.append(Spacer(1, 35))

    # Title & Subtitle
    cover.append(style_title and Paragraph("LEARNIX E-LEARNING PLATFORM", style_title))
    cover.append(Spacer(1, 10))
    cover.append(Paragraph("Complete Backend Technical Documentation & Evaluation Reference Manual", style_subtitle))
    cover.append(Spacer(1, 15))

    # Accent divider
    cover.append(HRFlowable(width="60%", thickness=2, color=PRIMARY, spaceBefore=8, spaceAfter=25, hAlign='CENTER'))

    # Description summary box
    desc_style = ParagraphStyle(
        'CoverDesc',
        fontName='Helvetica',
        fontSize=9.5,
        leading=14.5,
        textColor=DARK_SLATE,
        alignment=1
    )
    desc_text = (
        "An exhaustive, beginner-friendly technical guide constructed from direct source code inspection of the "
        "Learnix repository. Covers the Model-Template-View (MTV) pattern, 11 database models, ACID transaction boundaries, "
        "two-phase email OTP verification, Stripe hosted checkout with asynchronous webhooks, course progress algorithms, "
        "centralized SMTP notifications, OWASP security architecture, and a comprehensive 50-question viva masterclass."
    )
    cover.append(Paragraph(desc_text, desc_style))
    cover.append(Spacer(1, 45))

    # Technical Specifications Matrix
    spec_data = [
        [Paragraph("<b>Framework:</b>", style_body_bold), Paragraph("Django 5.0 (LTS Architecture)", style_body),
         Paragraph("<b>Runtime:</b>", style_body_bold), Paragraph("Python 3.14 (PEP 484 Type Hints)", style_body)],
        [Paragraph("<b>Database:</b>", style_body_bold), Paragraph("PostgreSQL 15+ (Production) / SQLite3 (Dev)", style_body),
         Paragraph("<b>Payment Gateway:</b>", style_body_bold), Paragraph("Stripe Hosted Checkout & Webhooks", style_body)],
        [Paragraph("<b>Authentication:</b>", style_body_bold), Paragraph("Two-Phase Email OTP (secrets module)", style_body),
         Paragraph("<b>Email Subsystem:</b>", style_body_bold), Paragraph("Centralized SMTP (Gmail TLS / port 587)", style_body)],
        [Paragraph("<b>Frontend Bridge:</b>", style_body_bold), Paragraph("Native JsonResponse AJAX & Stitch UI", style_body),
         Paragraph("<b>Verification Hash:</b>", style_body_bold), Paragraph("SHA-256 Tamper-Proof Certificates", style_body)],
    ]
    spec_table = Table(spec_data, colWidths=[95, 175, 105, 165])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.75, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    cover.append(spec_table)
    cover.append(Spacer(1, 55))

    # Publication Metadata Footer
    meta_table = Table([
        [Paragraph("<b>Document Edition:</b> Production Master Viva Reference", style_meta),
         Paragraph("<b>Inspected Scope:</b> 4 Apps, 11 Models, 22 Routes", style_meta),
         Paragraph(f"<b>Publication Date:</b> September 2026", style_meta)]
    ], colWidths=[180, 180, 180])
    meta_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.75, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    cover.append(meta_table)

    cover.append(PageBreak())
    return cover


def build_table_of_contents():
    """
    Renders an organized, easy-to-navigate Table of Contents spanning all 25 sections.
    """
    toc = []
    toc.append(h1("Table of Contents"))
    toc.append(hr())
    toc.append(p(
        "This master manual is organized into 25 structured technical sections designed for progressive learning "
        "and rapid examination review. Every section reflects actual code and configuration verified in the Learnix repository:"
    ))
    toc.append(spacer(6))

    toc_items = [
        ("Part I: System Overview & Django Fundamentals", [
            ("Section 1", "Project Overview & Five-Layer Architecture", "Mission, design philosophy, directory tree, request lifecycle"),
            ("Section 2", "Django Fundamentals Deep Dive (19 Core Concepts)", "What, Why, Where, How, and real code for 19 fundamental concepts"),
            ("Section 3", "Deep Dive into Django Apps (accounts, core, courses, payments)", "Responsibilities, directory structure, route tables, dependencies"),
            ("Section 4", "Models and Database Architecture (All 11 Models)", "Detailed tables, fields, constraints, methods, and ORM operations"),
            ("Section 5", "Migrations from A to Z", "Schema evolution from 0001 to 0004, CreateModel, django_migrations"),
        ]),
        ("Part II: Routing, Business Logic, Auth & Payments", [
            ("Section 6", "URLs and Routing Architecture", "Master router delegation, 22-route execution table, path converters"),
            ("Section 7", "Views and Business Logic", "CBV hierarchy, mixins, generic views, line-by-line view walkthrough"),
            ("Section 8", "User Authentication Subsystem", "Two-phase OTP lifecycle, 10-minute expiry, brute-force ceiling, rate limits"),
            ("Section 9", "Google Sign-In / OAuth 2.0 Integration & Roadmap", "OAuth 2.0 theory, codebase status (allauth installed, UI button, activation)"),
            ("Section 10", "Centralized Transactional Email Subsystem", "SMTP configuration (shahbazbutt22ee@gmail.com), 4 email templates"),
            ("Section 11", "Stripe Payment Gateway Integration A-to-Z", "Hosted checkout session, card-only restriction, webhook verification, fulfillment"),
        ]),
        ("Part III: Course Engine, APIs, Validation & Lifecycles", [
            ("Section 12", "Course and Enrollment Subsystem", "Course hierarchy, dynamic progress calculation, automated certificates"),
            ("Section 13", "RESTful API Architecture & Client-Side AJAX", "Status of DRF, native JsonResponse endpoints, DRF theoretical concepts"),
            ("Section 14", "Forms and Input Validation", "StudentRegistrationForm, OTPVerificationForm, UserLoginForm, clean methods"),
            ("Section 15", "Security Architecture & Vulnerability Mitigation", "CSRF defense, PBKDF2 hashing, SQL injection immunity, session security"),
            ("Section 16", "Error Handling Architecture & Custom Exceptions", "Domain exceptions (core/exceptions.py), custom 404/500 handlers, Stripe errors"),
            ("Section 17", "Complete End-to-End Request Lifecycles", "Detailed traces: Signup, Login, Stripe Purchase, Live Search, Lesson Progress"),
        ]),
        ("Part IV: Advanced Python, Third-Party Tools & Deployment", [
            ("Section 18", "Important Python Language Concepts in Learnix", "Decorators, OOP mixins, Context managers, secrets, type hints, comprehensions"),
            ("Section 19", "Third-Party Libraries Reference Table", "Exhaustive table of all 13 dependencies with rationale, usage, key classes"),
            ("Section 20", "Environment & Configuration Management", ".env structure, decoupling credentials, security guidelines"),
            ("Section 21", "Git & Project Workflow", "Branching, .gitignore guardrails, requirements.txt, virtual environments"),
            ("Section 22", "Deployment & Production Architecture", "Gunicorn WSGI, WhiteNoise static caching, PostgreSQL pooling, PaaS release"),
        ]),
        ("Part V: Viva Preparation, Strategy & Quick Revision", [
            ("Section 23", "How to Explain This Project in an Evaluation / Viva", "18 core domains: What, Why, How, Where, Likely Question & Model Answer"),
            ("Section 24", "Code Explanation Rules and Live Demonstration Strategies", "7 golden rules, walkthrough sequences, edge-case defense, live checklist"),
            ("Section 25", "Final Quick Revision: 7 Cheat Sheets & Top 50 Viva Q&As", "7 high-yield architectural sheets + 50 concise model answers"),
        ])
    ]

    for part_title, sections in toc_items:
        toc.append(Paragraph(f"<b>{part_title}</b>", ParagraphStyle(
            'TOCPart', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=PRIMARY_DARK, spaceBefore=6, spaceAfter=3
        )))
        part_data = []
        for sec_num, sec_title, sec_desc in sections:
            part_data.append([
                Paragraph(f"<b>{sec_num}</b>", style_body_bold),
                Paragraph(f"<b>{sec_title}</b><br/><font color='#64748B'>{sec_desc}</font>", style_body)
            ])
        part_table = Table(part_data, colWidths=[90, 450])
        part_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('LINELEFT', (0,0), (0,-1), 2.5, ACCENT_CYAN),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
            ('BOX', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        toc.append(part_table)
        toc.append(spacer(4))

    toc.append(PageBreak())
    return toc


def generate_pdf():
    """
    Main compilation routine that builds the complete PDF document.
    """
    start_time = time.time()
    pdf_filename = "Learnix_Django_Backend_Complete_Documentation.pdf"
    pdf_path = os.path.abspath(pdf_filename)

    print(f"Starting compilation of {pdf_filename}...")

    # Configure document template with 0.5-inch margins (36 pt)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []

    # 1. Cover Page
    print("Building Cover Page...")
    story.extend(build_cover_page())

    # 2. Table of Contents
    print("Building Table of Contents...")
    story.extend(build_table_of_contents())

    # 3. Part 1 (Sections 1 to 5)
    print("Building Part 1 (Sections 1 to 5)...")
    story.extend(build_part1())
    story.append(PageBreak())

    # 4. Part 2 (Sections 6 to 11)
    print("Building Part 2 (Sections 6 to 11)...")
    story.extend(build_part2())
    story.append(PageBreak())

    # 5. Part 3 (Sections 12 to 17)
    print("Building Part 3 (Sections 12 to 17)...")
    story.extend(build_part3())
    story.append(PageBreak())

    # 6. Part 4 (Sections 18 to 22)
    print("Building Part 4 (Sections 18 to 22)...")
    story.extend(build_part4())
    story.append(PageBreak())

    # 7. Part 5 (Sections 23 to 25)
    print("Building Part 5 (Sections 23 to 25)...")
    story.extend(build_part5())

    print(f"Total flowables assembled: {len(story)}. Rendering PDF via NumberedCanvas...")

    # Build PDF with two-pass NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)

    elapsed = time.time() - start_time
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"Successfully generated: {pdf_path}")
    print(f"File size: {file_size_mb:.2f} MB in {elapsed:.2f} seconds.")


if __name__ == '__main__':
    generate_pdf()
