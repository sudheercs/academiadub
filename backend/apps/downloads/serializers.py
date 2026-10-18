from rest_framework import serializers

from .models import Download


class DownloadSerializer(serializers.ModelSerializer):
    """Public-facing: no raw file URL exposed directly."""
    topic_title = serializers.CharField(source="topic.title", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Download
        fields = (
            "id", "title", "description", "topic", "topic_title",
            "mime_type", "file_size_bytes", "access_level", "file_url", "created_at",
        )

    def get_file_url(self, obj):
        """
        Returns a presigned-style URL for the file.
        In local dev this is a direct /media/ URL.
        In production this should be replaced with a short-lived S3 presigned URL
        generated via boto3 (see views.py generate_download_url).
        """
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class DownloadUploadSerializer(serializers.ModelSerializer):
    """Staff-only: used when uploading a new file."""

    class Meta:
        model = Download
        fields = ("id", "topic", "title", "description", "file", "access_level")

    def create(self, validated_data):
        file = validated_data.get("file")
        if file:
            validated_data["file_size_bytes"] = file.size
            validated_data["mime_type"] = getattr(file, "content_type", "application/octet-stream")
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)
