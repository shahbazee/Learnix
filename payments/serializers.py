from rest_framework import serializers

from courses.models import Course, Enrollment
from courses.serializers import CourseListSerializer

from .models import Invoice, PaymentTransaction


class CheckoutSerializer(serializers.Serializer):
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
        if course.is_free:
            raise serializers.ValidationError(
                {
                    'course_id':
                        'This course is free. Enroll directly.'
                }
            )
        if Enrollment.objects.filter(
            user=request.user, course=course, is_active=True
        ).exists():
            raise serializers.ValidationError(
                {'course_id': 'Already enrolled in this course.'}
            )
        if PaymentTransaction.objects.filter(
            user=request.user, course=course, status='PENDING'
        ).exists():
            raise serializers.ValidationError(
                {'course_id': 'Checkout already in progress.'}
            )
        attrs['course'] = course
        return attrs


class PaymentTransactionSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'order_number', 'course', 'amount',
            'currency', 'status', 'created_at',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(
        source='transaction.order_number', read_only=True
    )
    course_title = serializers.CharField(
        source='transaction.course.title', read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'order_number',
            'course_title', 'billing_name', 'billing_email',
            'subtotal', 'tax_amount', 'total_amount',
            'issued_at', 'pdf_file',
        ]
