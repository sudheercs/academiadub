import uuid
from django.db import models
from django.conf import settings
from apps.catalogue.models import Topic


class Quiz(models.Model):
    """A quiz attached to a topic, containing multiple questions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_mark = models.PositiveIntegerField(default=70, help_text="Percentage required to pass (0-100)")
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Optional time limit in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "quizzes"

    def __str__(self):
        return f"{self.title} [{self.topic.title}]"


class Question(models.Model):
    """A single multiple-choice question in a quiz."""
    QUESTION_TYPES = [
        ("mcq", "Multiple Choice (single answer)"),
        ("multi", "Multiple Choice (multiple answers)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField(help_text="The question text (Markdown supported)")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default="mcq")
    explanation = models.TextField(blank=True, help_text="Shown after the user answers")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Q: {self.text[:60]}"


class Choice(models.Model):
    """An answer choice for a Question."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.text[:60]}"


class Attempt(models.Model):
    """
    Records one attempt by a user on a quiz.

    Lifecycle:
        in_progress  → created when the student first clicks "Start Quiz"
        submitted    → finalised when the student explicitly submits (or time expires)

    This separation is what makes started_at and submitted_at differ realistically.
    """
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("submitted",   "Submitted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    score_percent = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    answers = models.JSONField(
        default=dict,
        help_text="Map of question_id -> list of chosen choice_ids"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.email} → {self.quiz.title} ({self.status})"

