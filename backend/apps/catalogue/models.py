from django.db import models
from django.conf import settings


class Subject(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, 
        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
        default="draft"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="subtopics")
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=150)
    difficulty = models.CharField(
        max_length=20,
        choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")],
        default="beginner"
    )
    access_level = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("login", "Login Required"), ("paid", "Paid")],
        default="free"
    )
    status = models.CharField(
        max_length=20, 
        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
        default="draft"
    )
    current_version_id = models.IntegerField(null=True, blank=True) # Will point to active TopicVersion.version_no
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subject', 'slug')
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.subject.slug} / {self.title}"


class TopicVersion(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField()
    blocks = models.JSONField(default=list)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="authored_topics")
    state = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"), 
            ("in_review", "In Review"), 
            ("approved", "Approved"), 
            ("published", "Published"), 
            ("archived", "Archived")
        ],
        default="draft"
    )
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('topic', 'version_no')
        ordering = ['-version_no']

    def __str__(self):
        return f"{self.topic.title} - v{self.version_no}"
