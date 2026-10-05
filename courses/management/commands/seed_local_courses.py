from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import UserProfile
from courses.models import Course, CourseCategory, CourseModule, Lesson

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **options):
        db_host = settings.DATABASES["default"].get("HOST", "")
        if db_host not in ("localhost", "127.0.0.1"):
            raise CommandError(
                f"Database host '{db_host}' is not localhost or 127.0.0.1."
            )

        with transaction.atomic():
            instructor, _ = User.objects.get_or_create(
                username="learnix_instructor",
                defaults={
                    "first_name": "Learnix",
                    "last_name": "Instructor",
                    "email": "instructor@learnix.local",
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            instructor.set_unusable_password()
            instructor.is_staff = False
            instructor.is_superuser = False
            instructor.is_active = True
            instructor.save()

            profile, _ = UserProfile.objects.get_or_create(user=instructor)
            profile.role = UserProfile.ROLE_INSTRUCTOR
            profile.headline = "Learnix Instructor"
            profile.save()

            categories_data = [
                ("AI Systems", "ai-systems"),
                ("Distributed Systems", "distributed-systems"),
                ("Cloud Infrastructure", "cloud-infrastructure"),
                ("System Design", "system-design"),
            ]

            category_map = {}
            for name, slug in categories_data:
                cat, _ = CourseCategory.objects.get_or_create(
                    slug=slug, defaults={"name": name}
                )
                category_map[slug] = cat

            catalog = [
                {
                    "title": "Introduction to Neural Networks",
                    "slug": "intro-neural-networks",
                    "category": category_map["ai-systems"],
                    "level": "BEGINNER",
                    "price": Decimal("0.00"),
                    "short_description": (
                        "Learn the core principles of artificial neural "
                        "networks, forward propagation, and optimization."
                    ),
                    "full_description": (
                        "A comprehensive guide covering neural network "
                        "foundations, gradient descent, backpropagation, and "
                        "modern deep learning architectures."
                    ),
                    "modules": [
                        (
                            "Foundations of Deep Learning",
                            [
                                (
                                    "Perceptrons and Activation Functions",
                                    480,
                                    True,
                                ),
                                (
                                    "Forward Propagation and Loss Functions",
                                    540,
                                    False,
                                ),
                                (
                                    "Gradient Descent and Optimization",
                                    600,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Training Neural Networks",
                            [
                                ("Backpropagation Mechanics", 660, False),
                                ("Regularization and Dropout", 520, False),
                                (
                                    "Batch Normalization and Learning Rates",
                                    580,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Modern Architectures",
                            [
                                (
                                    "Convolutional Layers Overview",
                                    720,
                                    False,
                                ),
                                (
                                    "Recurrent Architectures and Sequences",
                                    640,
                                    False,
                                ),
                                (
                                    "Introduction to Transformer Blocks",
                                    780,
                                    False,
                                ),
                            ],
                        ),
                    ],
                },
                {
                    "title": "Advanced LLM Fine-Tuning",
                    "slug": "advanced-llm-fine-tuning",
                    "category": category_map["ai-systems"],
                    "level": "ADVANCED",
                    "price": Decimal("149.00"),
                    "short_description": (
                        "Master parameter-efficient fine-tuning techniques, "
                        "dataset preparation, and model alignment."
                    ),
                    "full_description": (
                        "In-depth exploration of LoRA, QLoRA, instruction "
                        "tuning pipelines, preference optimization, and "
                        "production deployment."
                    ),
                    "modules": [
                        (
                            "Parameter-Efficient Tuning",
                            [
                                ("Overview of LoRA and QLoRA", 510, True),
                                (
                                    "4-bit Quantization and Memory Footprint",
                                    620,
                                    False,
                                ),
                                ("Adapters and Weight Merging", 570, False),
                            ],
                        ),
                        (
                            "Instruction Datasets and Alignment",
                            [
                                (
                                    "Dataset Formatting and Tokenization",
                                    490,
                                    False,
                                ),
                                (
                                    "Supervised Fine-Tuning Execution",
                                    680,
                                    False,
                                ),
                                (
                                    "Direct Preference Optimization",
                                    750,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Evaluation and Deployment",
                            [
                                (
                                    "Benchmark Metrics and Perplexity",
                                    460,
                                    False,
                                ),
                                (
                                    "Serving Fine-Tuned Models with vLLM",
                                    700,
                                    False,
                                ),
                                (
                                    "Continuous Monitoring and Safety",
                                    530,
                                    False,
                                ),
                            ],
                        ),
                    ],
                },
                {
                    "title": (
                        "High-Throughput Vector Databases and Embeddings"
                    ),
                    "slug": "high-throughput-vector-databases-embeddings",
                    "category": category_map["ai-systems"],
                    "level": "ADVANCED",
                    "price": Decimal("119.00"),
                    "short_description": (
                        "Architect HNSW indices, quantization schemes, and "
                        "distributed vector retrieval pipelines at scale."
                    ),
                    "full_description": (
                        "Hands-on guide to approximate nearest neighbor "
                        "algorithms, scalar and product quantization, "
                        "and cluster sharding strategies."
                    ),
                    "modules": [
                        (
                            "Vector Search Foundations",
                            [
                                (
                                    "Embeddings and Distance Metrics",
                                    450,
                                    True,
                                ),
                                (
                                    "Exact Nearest Neighbors and Index Types",
                                    540,
                                    False,
                                ),
                                (
                                    "Dimensionality and Index Sizing",
                                    600,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Graph-Based Indexing",
                            [
                                ("HNSW Graph Construction", 680, False),
                                (
                                    "Product Quantization Techniques",
                                    720,
                                    False,
                                ),
                                (
                                    "Hybrid Search with Sparse Embeddings",
                                    610,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Distributed Retrieval at Scale",
                            [
                                (
                                    "Sharding and Replication in Vector DBs",
                                    640,
                                    False,
                                ),
                                (
                                    "Low-Latency Query Execution",
                                    580,
                                    False,
                                ),
                                (
                                    "Benchmarking Recall vs Latency",
                                    500,
                                    False,
                                ),
                            ],
                        ),
                    ],
                },
                {
                    "title": "Distributed Systems with Raft",
                    "slug": "distributed-systems-raft",
                    "category": category_map["distributed-systems"],
                    "level": "ADVANCED",
                    "price": Decimal("99.00"),
                    "short_description": (
                        "Implement consensus, leader election, and log "
                        "replication in fault-tolerant distributed networks."
                    ),
                    "full_description": (
                        "Covers consensus theory, Raft protocol invariants, "
                        "handling network partitions, and building "
                        "replicated state machines."
                    ),
                    "modules": [
                        (
                            "Consensus Fundamentals",
                            [
                                (
                                    "Introduction to Consensus and Partitions",
                                    490,
                                    True,
                                ),
                                ("The Raft State Machine", 560, False),
                                ("Leader Election Mechanics", 630, False),
                            ],
                        ),
                        (
                            "Log Replication and Safety",
                            [
                                (
                                    "Log Matching Property and Invariants",
                                    610,
                                    False,
                                ),
                                (
                                    "Handling Network Partitions",
                                    670,
                                    False,
                                ),
                                (
                                    "Log Compaction and Snapshots",
                                    580,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Production Implementation",
                            [
                                (
                                    "Dynamic Cluster Membership Changes",
                                    700,
                                    False,
                                ),
                                (
                                    "Persistent State and Disk Storage",
                                    540,
                                    False,
                                ),
                                (
                                    "Linearizable Read Semantics",
                                    650,
                                    False,
                                ),
                            ],
                        ),
                    ],
                },
                {
                    "title": "Kubernetes in Production",
                    "slug": "kubernetes-in-production",
                    "category": category_map["cloud-infrastructure"],
                    "level": "INTERMEDIATE",
                    "price": Decimal("129.00"),
                    "short_description": (
                        "Deploy, scale, and manage mission-critical container "
                        "workloads on production Kubernetes clusters."
                    ),
                    "full_description": (
                        "Practical masterclass covering cluster architecture, "
                        "networking, ingress patterns, stateful sets, and "
                        "production observability."
                    ),
                    "modules": [
                        (
                            "Cluster Architecture and Core Primitives",
                            [
                                (
                                    "Control Plane Internals and etcd",
                                    500,
                                    True,
                                ),
                                (
                                    "Pod Lifecycle and Resource Management",
                                    580,
                                    False,
                                ),
                                (
                                    "Declarative Workloads and Controllers",
                                    620,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Networking and Ingress",
                            [
                                (
                                    "Cluster Networking and CNI Plugins",
                                    640,
                                    False,
                                ),
                                (
                                    "Ingress Controllers and Gateway API",
                                    690,
                                    False,
                                ),
                                (
                                    "Service Mesh Architecture with Istio",
                                    710,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Production Operations and Reliability",
                            [
                                (
                                    "High Availability and Disaster Recovery",
                                    750,
                                    False,
                                ),
                                (
                                    "Node Autoscaling and Cluster Sizing",
                                    590,
                                    False,
                                ),
                                (
                                    "Observability, Metrics, and Alerts",
                                    530,
                                    False,
                                ),
                            ],
                        ),
                    ],
                },
                {
                    "title": "System Design Masterclass",
                    "slug": "system-design-masterclass",
                    "category": category_map["system-design"],
                    "level": "ADVANCED",
                    "price": Decimal("149.00"),
                    "short_description": (
                        "Design highly scalable, fault-tolerant distributed "
                        "systems for modern web-scale applications."
                    ),
                    "full_description": (
                        "Comprehensive blueprint covering architectural "
                        "trade-offs, database partitioning, caching layers, "
                        "and asynchronous messaging pipelines."
                    ),
                    "modules": [
                        (
                            "Architectural Foundations",
                            [
                                (
                                    "Scalability, Availability, and Latency",
                                    520,
                                    True,
                                ),
                                (
                                    "CAP Theorem and Consistency Models",
                                    600,
                                    False,
                                ),
                                (
                                    "Load Balancing and Reverse Proxies",
                                    570,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Data Layer and Caching Strategies",
                            [
                                (
                                    "Relational vs Non-Relational Databases",
                                    650,
                                    False,
                                ),
                                (
                                    "Database Sharding and Replication",
                                    720,
                                    False,
                                ),
                                (
                                    "Cache Invalidation and Redis Patterns",
                                    590,
                                    False,
                                ),
                            ],
                        ),
                        (
                            "Asynchronous Systems and Messaging",
                            [
                                (
                                    "Message Queues and Event Pipelines",
                                    660,
                                    False,
                                ),
                                (
                                    "Stream Processing with Apache Kafka",
                                    740,
                                    False,
                                ),
                                (
                                    "Rate Limiting and Resilience Patterns",
                                    580,
                                    False,
                                ),
                            ],
                        ),
                    ],
                },
            ]

            for item in catalog:
                course, _ = Course.objects.update_or_create(
                    slug=item["slug"],
                    defaults={
                        "title": item["title"],
                        "instructor": instructor,
                        "category": item["category"],
                        "short_description": item["short_description"],
                        "full_description": item["full_description"],
                        "price": item["price"],
                        "level": item["level"],
                        "is_published": True,
                        "reviews_count": 0,
                    },
                )

                for mod_idx, (mod_title, lessons) in enumerate(
                    item["modules"], start=1
                ):
                    module, _ = CourseModule.objects.update_or_create(
                        course=course,
                        order_number=mod_idx,
                        defaults={"title": mod_title},
                    )

                    for les_idx, (les_title, duration, is_prev) in enumerate(
                        lessons, start=1
                    ):
                        Lesson.objects.update_or_create(
                            module=module,
                            order_number=les_idx,
                            defaults={
                                "title": les_title,
                                "duration_seconds": duration,
                                "is_preview": is_prev,
                                "video_url": "",
                                "content": "",
                            },
                        )

        cat_count = CourseCategory.objects.count()
        course_count = Course.objects.count()
        module_count = CourseModule.objects.count()
        lesson_count = Lesson.objects.count()

        self.stdout.write(
            f"Categories: {cat_count}, Courses: {course_count}, "
            f"Modules: {module_count}, Lessons: {lesson_count}"
        )
