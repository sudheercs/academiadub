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


class Course(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="courses")
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")],
        default="beginner"
    )
    status = models.CharField(
        max_length=20, 
        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
        default="draft"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subject', 'slug')
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.subject.slug} / {self.title}"

    @property
    def name(self):
        return self.title

    @name.setter
    def name(self, value):
        self.title = value


class TopicManager(models.Manager):
    def create(self, **kwargs):
        if 'subject' in kwargs and 'course' not in kwargs:
            subject = kwargs.pop('subject')
            course, _ = Course.objects.get_or_create(
                subject=subject,
                slug="general",
                defaults={"title": f"{subject.name} - General", "status": "published"}
            )
            kwargs['course'] = course
        return super().create(**kwargs)


class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
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

    objects = TopicManager()

    class Meta:
        unique_together = ('course', 'slug')
        ordering = ['order', 'created_at']

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", None)
        super().__init__(*args, **kwargs)
        if subject and (not hasattr(self, 'course_id') or not self.course_id):
            self._pending_subject = subject

    def save(self, *args, **kwargs):
        if not self.course_id and hasattr(self, '_pending_subject') and self._pending_subject:
            course, _ = Course.objects.get_or_create(
                subject=self._pending_subject,
                slug="general",
                defaults={"title": f"{self._pending_subject.name} - General", "status": "published"}
            )
            self.course = course
        super().save(*args, **kwargs)

    @property
    def subject(self):
        return self.course.subject if self.course_id else None

    def __str__(self):
        if self.course_id:
            return f"{self.course.subject.slug} / {self.course.slug} / {self.title}"
        return self.title


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


class TopicVersionEvent(models.Model):
    ACTION_CHOICES = [
        ("created", "Draft created"),
        ("updated", "Draft updated"),
        ("submitted", "Submitted for review"),
        ("approved", "Approved"),
        ("returned", "Returned for edits"),
        ("published", "Published"),
        ("archived", "Archived"),
        ("unpublished", "Unpublished"),
    ]

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="version_events")
    version = models.ForeignKey(
        TopicVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    version_no = models.PositiveIntegerField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="topic_version_events",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.topic_id} v{self.version_no}: {self.action}"
