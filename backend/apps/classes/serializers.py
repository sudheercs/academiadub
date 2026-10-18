import random
import string

from apps.catalogue.serializers import TopicListSerializer
from rest_framework import serializers

from .models import Assignment, Classroom, Enrollment


def generate_join_code(length=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class EnrollmentSerializer(serializers.ModelSerializer):
    student_email = serializers.EmailField(source="student.email", read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "student",
            "student_email",
            "status",
            "student_secret",
            "enrolled_at",
        )
        read_only_fields = ("id", "student", "student_secret", "enrolled_at")


class AssignmentSerializer(serializers.ModelSerializer):
    topic = TopicListSerializer(read_only=True)
    topic_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=__import__(
            "apps.catalogue.models", fromlist=["Topic"]
        ).Topic.objects.all(),
        source="topic",
    )

    class Meta:
        model = Assignment
        fields = ("id", "topic", "topic_id", "title", "due_at", "created_at")
        read_only_fields = ("id", "created_at")


class ClassroomSerializer(serializers.ModelSerializer):
    instructor_email = serializers.EmailField(source="instructor.email", read_only=True)
    student_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = (
            "id",
            "name",
            "description",
            "instructor_email",
            "join_code",
            "is_active",
            "student_count",
            "assignment_count",
            "created_at",
        )
        read_only_fields = ("id", "join_code", "created_at")

    def get_student_count(self, obj):
        return obj.enrollments.filter(status="active").count()

    def get_assignment_count(self, obj):
        return obj.assignments.count()

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user
        validated_data["join_code"] = generate_join_code()
        return super().create(validated_data)


class ClassroomDetailSerializer(ClassroomSerializer):
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)

    class Meta(ClassroomSerializer.Meta):
        fields = ClassroomSerializer.Meta.fields + ("enrollments", "assignments")
