from django.db import models
from django.conf import settings
from apps.catalogue.models import Topic


class UserProgress(models.Model):
    """Tracks a user's read/completion state per topic."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="progress")
    state = models.CharField(
        max_length=20,
        choices=[
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="in_progress",
    )
    read_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "topic")
        ordering = ["-read_at"]

    def __str__(self):
        return f"{self.user.email} — {self.topic.title} [{self.state}]"


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "topic")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} ⭐ {self.topic.title}"
