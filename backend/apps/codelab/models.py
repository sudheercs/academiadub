import base64
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

MAX_STORAGE_BYTES = 100 * 1024 * 1024  # 100 MB per user


def _total_used_bytes(user, exclude_snippet_id=None, exclude_file_id=None):
    """Sum of all code + file bytes for a user."""
    qs_s = CodeSnippet.objects.filter(user=user)
    qs_f = CodeFile.objects.filter(user=user)
    if exclude_snippet_id:
        qs_s = qs_s.exclude(pk=exclude_snippet_id)
    if exclude_file_id:
        qs_f = qs_f.exclude(pk=exclude_file_id)
    used_s = qs_s.aggregate(t=models.Sum("size_bytes"))["t"] or 0
    used_f = qs_f.aggregate(t=models.Sum("size_bytes"))["t"] or 0
    return used_s + used_f


def validate_user_storage(
    user, new_size_bytes, exclude_snippet_id=None, exclude_file_id=None
):
    """
    Raise ValidationError if adding new_size_bytes would exceed the 100 MB quota.
    """
    used = _total_used_bytes(user, exclude_snippet_id, exclude_file_id)
    if used + new_size_bytes > MAX_STORAGE_BYTES:
        remaining_mb = (MAX_STORAGE_BYTES - used) / (1024 * 1024)
        raise ValidationError(
            f"Storage limit exceeded. You have {remaining_mb:.1f} MB remaining "
            f"of your 100 MB allowance."
        )


class CodeFolder(models.Model):
    """A personal folder a student uses to organise their saved code snippets and files."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_folders",
    )
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("user", "name")]

    def __str__(self):
        return f"{self.user.email} / {self.name}"


class CodeSnippet(models.Model):
    """A saved Python/JS code file. Counts against the 100 MB quota."""

    LANGUAGE_CHOICES = [
        ("python", "Python"),
        ("javascript", "JavaScript"),
        ("typescript", "TypeScript"),
        ("bash", "Bash"),
        ("text", "Plain Text"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_snippets",
    )
    folder = models.ForeignKey(
        CodeFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snippets",
    )
    title = models.CharField(max_length=200, default="Untitled")
    language = models.CharField(
        max_length=20, choices=LANGUAGE_CHOICES, default="python"
    )
    code = models.TextField()
    size_bytes = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.email} / {self.folder.name if self.folder else '—'} / {self.title}"

    def save(self, *args, **kwargs):
        self.size_bytes = len(self.code.encode("utf-8"))
        validate_user_storage(self.user, self.size_bytes, exclude_snippet_id=self.pk)
        super().save(*args, **kwargs)


class CodeFile(models.Model):
    """
    An arbitrary file (txt, csv, json, …) created or uploaded by a student.

    Content is stored as base64 in a TextField so we don't need a separate
    media volume — it lives entirely in the database and counts against the
    100 MB per-user quota.

    Students create these by:
      (a) Running Python code that writes files → output_files are auto-saved here
      (b) Uploading a file directly via the My Code panel
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_files",
    )
    folder = models.ForeignKey(
        CodeFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="files",
    )
    filename = models.CharField(
        max_length=255, help_text="Original filename, e.g. 'data.csv'"
    )
    mime_type = models.CharField(max_length=100, default="text/plain")
    # Base64-encoded raw bytes
    content_b64 = models.TextField(help_text="Base64-encoded file content")
    size_bytes = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.email} / {self.filename} ({self.size_bytes} B)"

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def content_text(self) -> str:
        """Decode base64 content to a UTF-8 string (for text files)."""
        try:
            return base64.b64decode(self.content_b64).decode("utf-8")
        except Exception:
            return ""

    @classmethod
    def from_text(cls, user, filename, text: str, folder=None, mime_type="text/plain"):
        """Convenience factory that encodes a text string and returns (unsaved) instance."""
        raw = text.encode("utf-8")
        b64 = base64.b64encode(raw).decode("ascii")
        return cls(
            user=user,
            folder=folder,
            filename=filename,
            mime_type=mime_type,
            content_b64=b64,
        )

    @classmethod
    def from_b64(
        cls,
        user,
        filename,
        b64_content: str,
        folder=None,
        mime_type="application/octet-stream",
    ):
        """Factory from raw base64 string (as returned by the code runner)."""
        raw = base64.b64decode(b64_content)
        return cls(
            user=user,
            folder=folder,
            filename=filename,
            mime_type=mime_type,
            content_b64=b64_content,
            size_bytes=len(raw),
        )

    def save(self, *args, **kwargs):
        # Recompute size_bytes from the actual decoded length
        try:
            self.size_bytes = len(base64.b64decode(self.content_b64))
        except Exception:
            self.size_bytes = 0
        validate_user_storage(self.user, self.size_bytes, exclude_file_id=self.pk)
        super().save(*args, **kwargs)
