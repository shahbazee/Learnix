from rest_framework import serializers

from .models import (
    Certificate,
    Course,
    CourseCategory,
    CourseModule,
    Enrollment,
    Lesson,
    LessonProgress,
)


class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = ['id', 'name', 'slug', 'icon', 'description']
        read_only_fields = ['id', 'slug']


class LessonSerializer(serializers.ModelSerializer):
    formatted_duration = serializers.ReadOnlyField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'video_url', 'content',
            'duration_seconds', 'formatted_duration',
            'order_number', 'is_preview',
        ]


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    total_duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = CourseModule
        fields = [
            'id', 'title', 'order_number',
            'total_duration_seconds', 'lessons',
        ]


class CourseListSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(
        source='category.name', read_only=True
    )
    is_free = serializers.ReadOnlyField()
    thumbnail_url = serializers.CharField(
        source='get_thumbnail_url', read_only=True
    )
    lessons_count = serializers.IntegerField(read_only=True)
    total_duration = serializers.CharField(
        source='total_duration_hours_display', read_only=True
    )

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'instructor_name',
            'category_name', 'short_description', 'price',
            'is_free', 'level', 'thumbnail_url', 'rating',
            'reviews_count', 'lessons_count',
            'total_duration',
        ]

    def get_instructor_name(self, obj):
        full_name = obj.instructor.get_full_name()
        return full_name or obj.instructor.username


class CourseDetailSerializer(CourseListSerializer):
    modules = CourseModuleSerializer(many=True, read_only=True)
    category = CourseCategorySerializer(read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            'full_description', 'category', 'modules',
            'created_at', 'updated_at',
        ]


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'title', 'category', 'short_description',
            'full_description', 'price', 'level',
            'thumbnail', 'thumbnail_url', 'is_published',
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Price cannot be negative.'
            )
        return value


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    is_completed = serializers.ReadOnlyField()
    completed_lessons_count = serializers.ReadOnlyField()
    total_lessons_count = serializers.ReadOnlyField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'course', 'enrolled_at', 'is_active',
            'progress_percent', 'is_completed',
            'completed_lessons_count', 'total_lessons_count',
        ]


class EnrollSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        try:
            course = Course.objects.get(
                id=attrs['course_id'], is_published=True
            )
        except Course.DoesNotExist:
            raise serializers.ValidationError(
                {'course_id': 'Course not found.'}
            )
        if not course.is_free:
            raise serializers.ValidationError(
                {'course_id': 'Paid courses need checkout.'}
            )
        if Enrollment.objects.filter(
            user=request.user, course=course
        ).exists():
            raise serializers.ValidationError(
                {'course_id': 'Already enrolled in this course.'}
            )
        attrs['course'] = course
        return attrs


class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(
        source='lesson.title', read_only=True
    )

    class Meta:
        model = LessonProgress
        fields = [
            'id', 'lesson', 'lesson_title', 'is_completed',
            'completed_at', 'last_accessed_at',
        ]
        read_only_fields = ['id', 'last_accessed_at']


class MarkLessonCompleteSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField(write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        try:
            lesson = Lesson.objects.select_related(
                'module__course'
            ).get(id=attrs['lesson_id'])
        except Lesson.DoesNotExist:
            raise serializers.ValidationError(
                {'lesson_id': 'Lesson not found.'}
            )
        if not Enrollment.objects.filter(
            user=request.user,
            course=lesson.module.course,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                {'lesson_id': 'Enroll in the course first.'}
            )
        attrs['lesson'] = lesson
        return attrs


class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source='course.title', read_only=True
    )

    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_id', 'course_title',
            'verification_hash', 'ceus', 'issued_at',
            'pdf_file',
        ]
