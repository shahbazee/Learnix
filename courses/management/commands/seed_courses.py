"""
Management command to seed Learnix database with courses and curriculum.
Populates categories, instructors, courses, modules, and lessons.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from courses.models import CourseCategory, Course, CourseModule, Lesson, Enrollment, LessonProgress
from payments.models import PaymentTransaction, Invoice

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds Learnix with masterclass courses, modules, and lessons"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Learnix curricula..."))

        # 1. Instructors
        instructors_data = [
            ("elena_rostova", "Elena", "Rostova", "Lead AI Fellow · Ex-DeepMind"),
            ("alex_vance", "Alex", "Vance", "Staff Architect · Ex-Google Brain"),
            ("marcus_jin", "Marcus", "Jin", "Principal SRE · Cloud Infrastructure"),
            ("sarah_lin", "Sarah", "Lin", "NLP Lab Lead, PhD · Vector Systems"),
            ("devon_hayes", "Devon", "Hayes", "Red Team Director · Zero-Trust"),
        ]

        instructors = {}
        for username, fname, lname, headline in instructors_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": fname,
                    "last_name": lname,
                    "email": f"{username}@learnix.com",
                    "is_active": True,
                }
            )
            if created:
                user.set_password("LearnixPass2026!")
                user.save()
            if hasattr(user, 'profile'):
                user.profile.headline = headline
                user.profile.save()
            instructors[username] = user

        # 2. Categories
        categories_data = [
            ("Python & Django", "python-django", "terminal"),
            ("Machine Learning & LLMs", "ml-llms", "psychology"),
            ("System Design", "system-design", "lan"),
            ("Cloud & DevOps", "cloud-devops", "cloud"),
            ("Zero-Trust Security", "security", "security"),
            ("Distributed Data", "distributed-data", "database"),
        ]

        categories = {}
        for name, slug, icon in categories_data:
            cat, _ = CourseCategory.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "icon": icon}
            )
            categories[slug] = cat

        # 3. Courses Data
        courses_catalog = [
            {
                "title": "Full-Stack Django 5 & Multi-Agent AI",
                "slug": "full-stack-django-5-multi-agent-ai",
                "category": categories["python-django"],
                "instructor": instructors["elena_rostova"],
                "level": "INTERMEDIATE",
                "price": Decimal("89.00"),
                "rating": Decimal("4.98"),
                "reviews_count": 1120,
                "short_description": "Build autonomous multi-agent swarms with LangGraph, Django 5 async websockets, PGVector embeddings, and sub-50ms inference orchestration.",
                "thumbnail_url": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=80",
                "modules": [
                    ("Foundations: Asynchronous Django & Channels", [
                        ("1.1 Architecture Overview & ASGI Event Loops", 860, True),
                        ("1.2 WebSockets & ASGI Handlers Setup", 1335, True),
                        ("1.3 Redis Pub/Sub Layer Integration", 1720, False),
                        ("1.4 ASGI Middleware & Cryptographic Handshakes", 1185, False),
                    ]),
                    ("Agentic Workflows with LangGraph & Django", [
                        ("2.1 Multi-Agent State Graph Architecture", 1450, False),
                        ("2.2 Tool Calling & ReAct Execution Loops", 1620, False),
                        ("2.3 Human-in-the-Loop Interrupt Workflows", 1980, False),
                    ]),
                    ("Vector Databases & Hybrid Search Indexing", [
                        ("3.1 Qdrant Vector Cluster Deployment", 1200, False),
                        ("3.2 Dense vs Sparse Vector Hybrids", 1400, False),
                    ]),
                ]
            },
            {
                "title": "Distributed Systems in Rust & Go",
                "slug": "distributed-systems-rust-go",
                "category": categories["system-design"],
                "instructor": instructors["alex_vance"],
                "level": "ADVANCED",
                "price": Decimal("99.00"),
                "rating": Decimal("4.94"),
                "reviews_count": 640,
                "short_description": "Master Raft consensus, concurrent actor models, sharded distributed key-value stores, and fault-tolerant network topologies under extreme partition failure.",
                "thumbnail_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
                "modules": [
                    ("Raft Consensus & Distributed Log Replication", [
                        ("1.1 Leader Election State Transitions", 1100, True),
                        ("1.2 Log Invariants & Snapshotting", 1420, True),
                        ("1.3 Network Split-Brain Simulations", 1850, False),
                    ]),
                    ("High-Performance Sharding Topologies", [
                        ("2.1 Consistent Hashing with Virtual Nodes", 1250, False),
                        ("2.2 Multi-Paxos and Dynamic Membership", 1950, False),
                    ]),
                ]
            },
            {
                "title": "High-Scale Kubernetes & Cloud Architecture",
                "slug": "high-scale-kubernetes-cloud-architecture",
                "category": categories["cloud-devops"],
                "instructor": instructors["marcus_jin"],
                "level": "ADVANCED",
                "price": Decimal("119.00"),
                "rating": Decimal("4.89"),
                "reviews_count": 480,
                "short_description": "Custom CRDs, zero-downtime deployments with Istio, multi-region cluster federation, and eBPF kernel network monitoring in live production clusters.",
                "thumbnail_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1200&q=80",
                "modules": [
                    ("Advanced Operator SDK & Custom Resource Controllers", [
                        ("1.1 Controller-Runtime Architecture", 1020, True),
                        ("1.2 Reconcile Loops & Finalizers", 1450, False),
                        ("1.3 Multi-Cluster Global Ingress Meshes", 1750, False),
                    ]),
                ]
            },
            {
                "title": "Production LLMs: RAG & Fine-Tuning",
                "slug": "production-llms-rag-fine-tuning",
                "category": categories["ml-llms"],
                "instructor": instructors["sarah_lin"],
                "level": "INTERMEDIATE",
                "price": Decimal("95.00"),
                "rating": Decimal("4.92"),
                "reviews_count": 890,
                "short_description": "QLoRA parameter-efficient training, reranking with hybrid sparse-dense vectors, evaluation pipelines, and low-latency vLLM inference clusters.",
                "thumbnail_url": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=1200&q=80",
                "modules": [
                    ("Quantized Model LoRA Architectures", [
                        ("1.1 4-bit NormalFloat & Double Quantization", 1150, True),
                        ("1.2 Supervised Fine-Tuning on Custom Corpora", 1640, False),
                    ]),
                ]
            },
            {
                "title": "Modern Web Security & Zero-Trust",
                "slug": "modern-web-security-zero-trust",
                "category": categories["security"],
                "instructor": instructors["devon_hayes"],
                "level": "BEGINNER",
                "price": Decimal("79.00"),
                "rating": Decimal("4.91"),
                "reviews_count": 312,
                "short_description": "mTLS handshakes, OAuth2.1 + PKCE flows, continuous device attestation, supply chain SBOM verification, and defense against sub-domain takeovers.",
                "thumbnail_url": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80",
                "modules": [
                    ("Identity Foundation & Cryptographic Tokens", [
                        ("1.1 PKCE Authorization Code Flows", 950, True),
                        ("1.2 Mutual TLS & SPIFFE/SPIRE Attestation", 1320, False),
                    ]),
                ]
            },
            {
                "title": "High-Throughput Vector Databases & Embeddings",
                "slug": "high-throughput-vector-databases-embeddings",
                "category": categories["distributed-data"],
                "instructor": instructors["sarah_lin"],
                "level": "ADVANCED",
                "price": Decimal("119.00"),
                "rating": Decimal("4.95"),
                "reviews_count": 530,
                "short_description": "Architect HNSW graph indices, product quantization, scalar compression, and distributed Milvus & Qdrant sharding for billion-scale retrieval.",
                "thumbnail_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80",
                "modules": [
                    ("Vector Indexing Math & HNSW Graphs", [
                        ("1.1 Approximate Nearest Neighbor Math", 1080, True),
                        ("1.2 Product Quantization & Cache Alignment", 1540, False),
                    ]),
                ]
            },
        ]

        # 4. Insert or Update Courses
        for cdata in courses_catalog:
            course, _ = Course.objects.update_or_create(
                slug=cdata["slug"],
                defaults={
                    "title": cdata["title"],
                    "category": cdata["category"],
                    "instructor": cdata["instructor"],
                    "level": cdata["level"],
                    "price": cdata["price"],
                    "rating": cdata["rating"],
                    "reviews_count": cdata["reviews_count"],
                    "short_description": cdata["short_description"],
                    "thumbnail_url": cdata["thumbnail_url"],
                    "is_published": True,
                }
            )

            # Insert Modules & Lessons
            for mod_idx, (mod_title, lessons) in enumerate(cdata["modules"], start=1):
                module, _ = CourseModule.objects.update_or_create(
                    course=course,
                    order_number=mod_idx,
                    defaults={"title": mod_title}
                )
                for les_idx, (les_title, duration, is_prev) in enumerate(lessons, start=1):
                    Lesson.objects.update_or_create(
                        module=module,
                        order_number=les_idx,
                        defaults={
                            "title": les_title,
                            "duration_seconds": duration,
                            "is_preview": is_prev,
                            "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                        }
                    )

        # 5. Seed Demo Student Sarah Jenkins with active enrollment & progress
        student, created = User.objects.get_or_create(
            username="sarah",
            defaults={
                "first_name": "Sarah",
                "last_name": "Jenkins",
                "email": "sarah@learnix.edu",
                "is_active": True,
            }
        )
        student.set_password("LearnixDemo2026!")
        student.save()
        if hasattr(student, 'profile'):
            student.profile.headline = "Staff Engineer // Autonomous Agentic Systems"
            student.profile.bio = "Building resilient distributed microservices and multi-agent AI pipelines with Django and LangGraph."
            student.profile.save()

        # Enroll in primary course: full-stack-django-5-multi-agent-ai
        primary_course = Course.objects.filter(slug="full-stack-django-5-multi-agent-ai").first()
        if primary_course:
            enrollment, _ = Enrollment.objects.get_or_create(
                user=student,
                course=primary_course,
                defaults={"is_active": True, "progress_percent": 78.00}
            )
            # Mark first 6 lessons completed
            all_lessons = list(Lesson.objects.filter(module__course=primary_course).order_by("module__order_number", "order_number"))
            for les in all_lessons[:6]:
                LessonProgress.objects.get_or_create(
                    user=student,
                    lesson=les,
                    defaults={"is_completed": True, "completed_at": timezone.now()}
                )
            enrollment.calculate_progress()

            # Seed billing transaction & invoice
            tx, _ = PaymentTransaction.objects.get_or_create(
                user=student,
                course=primary_course,
                defaults={
                    "order_number": "LRN-98214",
                    "amount": Decimal("349.00"),
                    "currency": "USD",
                    "status": "COMPLETED",
                }
            )
            if not hasattr(tx, 'invoice'):
                Invoice.objects.get_or_create(
                    transaction=tx,
                    defaults={
                        "invoice_number": "INV-2026-98214",
                        "billing_name": "Sarah Jenkins",
                        "billing_email": "sarah@learnix.edu",
                        "subtotal": Decimal("349.00"),
                        "tax_amount": Decimal("0.00"),
                        "total_amount": Decimal("349.00"),
                    }
                )

        # Enroll in secondary course: distributed-systems-rust-go
        secondary_course = Course.objects.filter(slug="distributed-systems-rust-go").first()
        if secondary_course:
            e2, _ = Enrollment.objects.get_or_create(
                user=student,
                course=secondary_course,
                defaults={"is_active": True, "progress_percent": 35.00}
            )
            tx2, _ = PaymentTransaction.objects.get_or_create(
                user=student,
                course=secondary_course,
                defaults={
                    "order_number": "LRN-87109",
                    "amount": Decimal("289.00"),
                    "currency": "USD",
                    "status": "COMPLETED",
                }
            )
            if not hasattr(tx2, 'invoice'):
                Invoice.objects.get_or_create(
                    transaction=tx2,
                    defaults={
                        "invoice_number": "INV-2026-87109",
                        "billing_name": "Sarah Jenkins",
                        "billing_email": "sarah@learnix.edu",
                        "subtotal": Decimal("289.00"),
                        "tax_amount": Decimal("0.00"),
                        "total_amount": Decimal("289.00"),
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(courses_catalog)} courses and demo student Sarah Jenkins into Learnix!"))
