import uuid

from django.conf import settings
from django.db import models

from apps.catalogue.models import Topic


class Download(models.Model):
    """
    A file attachment (PDF, notebook, zip) linked to a topic.
    In local dev, file is stored in MEDIA_ROOT.
    In production, django-storages routes it to S3 (ap-south-1).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="downloads")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="downloads/%Y/%m/")
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    access_level = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("login", "Login Required"), ("paid", "Paid")],
        default="login",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploads",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size_bytes = self.file.size
            import mimetypes
            
            # Register common Office mimetypes that might be missing on some systems
            mimetypes.add_type('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
            mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')
            mimetypes.add_type('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')
            
            mime_type, _ = mimetypes.guess_type(self.file.name)
            if mime_type:
                self.mime_type = mime_type
            else:
                self.mime_type = 'application/octet-stream' # Fallback
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} [{self.topic.title}]"


class DownloadLog(models.Model):
    """Audit trail: who downloaded what and when."""
    download = models.ForeignKey(Download, on_delete=models.CASCADE, related_name="logs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="download_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-downloaded_at"]

    def __str__(self):
        who = self.user.email if self.user else "anonymous"
        return f"{who} → {self.download.title}"
