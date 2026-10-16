import base64
import mimetypes

from rest_framework import serializers

from .models import CodeFolder, CodeSnippet, CodeFile, MAX_STORAGE_BYTES


class CodeFolderSerializer(serializers.ModelSerializer):
    snippet_count = serializers.IntegerField(source="snippets.count", read_only=True)
    file_count    = serializers.IntegerField(source="files.count",    read_only=True)

    class Meta:
        model  = CodeFolder
        fields = ["id", "name", "snippet_count", "file_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── Code Snippets ─────────────────────────────────────────────────────────────

class CodeSnippetListSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True, default=None)

    class Meta:
        model  = CodeSnippet
        fields = ["id", "title", "language", "folder", "folder_name",
                  "size_bytes", "created_at", "updated_at"]
        read_only_fields = ["id", "size_bytes", "created_at", "updated_at"]


class CodeSnippetDetailSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True, default=None)

    class Meta:
        model  = CodeSnippet
        fields = ["id", "title", "language", "folder", "folder_name",
                  "code", "size_bytes", "created_at", "updated_at"]
        read_only_fields = ["id", "size_bytes", "created_at", "updated_at"]

    def validate(self, data):
        code = data.get("code", getattr(self.instance, "code", ""))
        size_bytes = len(code.encode("utf-8"))
        user = self.context["request"].user
        from .models import validate_user_storage
        validate_user_storage(
            user, size_bytes,
            exclude_snippet_id=self.instance.pk if self.instance else None,
        )
        return data


# ── Code Files ────────────────────────────────────────────────────────────────

class CodeFileListSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True, default=None)

    class Meta:
        model  = CodeFile
        fields = ["id", "filename", "mime_type", "folder", "folder_name",
                  "size_bytes", "created_at", "updated_at"]
        read_only_fields = ["id", "size_bytes", "created_at", "updated_at"]


class CodeFileDetailSerializer(serializers.ModelSerializer):
    """
    Full serialiser — includes content_b64 and a decoded text preview.
    content_b64 can be set on write.  content_text is read-only (decoded view).
    """
    folder_name  = serializers.CharField(source="folder.name", read_only=True, default=None)
    content_text = serializers.SerializerMethodField()

    class Meta:
        model  = CodeFile
        fields = ["id", "filename", "mime_type", "folder", "folder_name",
                  "content_b64", "content_text", "size_bytes", "created_at", "updated_at"]
        read_only_fields = ["id", "size_bytes", "content_text", "created_at", "updated_at"]

    def get_content_text(self, obj):
        """Return decoded UTF-8 text for text/* files; None for binary."""
        if obj.mime_type and not obj.mime_type.startswith("text/"):
            return None
        return obj.content_text

    def validate_content_b64(self, value):
        try:
            base64.b64decode(value, validate=True)
        except Exception:
            raise serializers.ValidationError("content_b64 must be valid base64.")
        return value

    def validate(self, data):
        b64 = data.get("content_b64", getattr(self.instance, "content_b64", ""))
        try:
            size_bytes = len(base64.b64decode(b64))
        except Exception:
            size_bytes = 0

        user = self.context["request"].user
        from .models import validate_user_storage
        validate_user_storage(
            user, size_bytes,
            exclude_file_id=self.instance.pk if self.instance else None,
        )
        return data


class CodeFileUploadSerializer(serializers.Serializer):
    """
    Accepts a multipart file upload and converts it to a CodeFile.
    Used by POST /api/codelab/files/upload/
    """
    file   = serializers.FileField()
    folder = serializers.UUIDField(required=False, allow_null=True)

    def validate_file(self, upload):
        MAX_SINGLE = 10 * 1024 * 1024   # 10 MB per file upload
        if upload.size > MAX_SINGLE:
            raise serializers.ValidationError("Single file upload limit is 10 MB.")
        return upload


class StorageUsageSerializer(serializers.Serializer):
    used_bytes  = serializers.IntegerField()
    total_bytes = serializers.IntegerField()
    used_mb     = serializers.FloatField()
    total_mb    = serializers.FloatField()
    used_pct    = serializers.FloatField()
