import secrets
import string
import uuid

from apps.catalogue.models import Topic
from django.conf import settings
from django.db import models


def _generate_join_code(length=8):
    """Uppercase alphanumeric code, unambiguous chars."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_student_secret(length=6):
    """Short numeric PIN for students."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


class Classroom(models.Model):
    """
    A class cohort owned by an instructor.
    Students join via a unique join_code.
    join_code is auto-generated on first save but can be overridden/regenerated in admin.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="taught_classes",
    )
    join_code = models.CharField(max_length=12, unique=True, db_index=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.join_code:
            # Keep generating until we get a unique code
            code = _generate_join_code()
            while Classroom.objects.filter(join_code=code).exists():
                code = _generate_join_code()
            self.join_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (by {self.instructor.email})"


class Enrollment(models.Model):
    """A student's membership in a class, with a personal secret for code-based login."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("dropped", "Dropped"),
        ("completed", "Completed"),
    ]
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="enrollments"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    # Personal secret code issued to this student for this class.
    # Login: class_code + student_secret → JWT
    student_secret = models.CharField(max_length=8, blank=True)

    class Meta:
        unique_together = ("classroom", "student")
        ordering = ["enrolled_at"]

    def save(self, *args, **kwargs):
        if not self.student_secret:
            self.student_secret = _generate_student_secret()
        super().save(*args, **kwargs)

    def regenerate_secret(self):
        self.student_secret = _generate_student_secret()
        self.save(update_fields=["student_secret"])

    def __str__(self):
        return f"{self.student.email} in {self.classroom.name}"


class Assignment(models.Model):
    """
    An instructor assigns a topic to a class with an optional deadline.
    """

    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="assignments"
    )
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="assignments"
    )
    title = models.CharField(max_length=200, blank=True)  # Override title if needed
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("classroom", "topic")
        ordering = ["due_at", "created_at"]

    def __str__(self):
        return f"{self.classroom.name} → {self.topic.title}"
