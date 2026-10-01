import uuid
from django.db import models
from django.conf import settings
from apps.catalogue.models import Topic


class Classroom(models.Model):
    """
    A class cohort owned by an instructor.
    Students join via a unique join_code.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="taught_classes",
    )
    join_code = models.CharField(max_length=12, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} (by {self.instructor.email})"


class Enrollment(models.Model):
    """A student's membership in a class."""
    STATUS_CHOICES = [
        ("active", "Active"),
        ("dropped", "Dropped"),
        ("completed", "Completed"),
    ]
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("classroom", "student")
        ordering = ["enrolled_at"]

    def __str__(self):
        return f"{self.student.email} in {self.classroom.name}"


class Assignment(models.Model):
    """
    An instructor assigns a topic to a class with an optional deadline.
    """
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="assignments")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200, blank=True)  # Override title if needed
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("classroom", "topic")
        ordering = ["due_at", "created_at"]

    def __str__(self):
        return f"{self.classroom.name} → {self.topic.title}"
