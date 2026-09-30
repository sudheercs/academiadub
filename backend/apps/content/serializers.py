from rest_framework import serializers
from .models import UserProgress, Bookmark
from apps.catalogue.models import Topic


class UserProgressSerializer(serializers.ModelSerializer):
    topic_title = serializers.CharField(source="topic.title", read_only=True)
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)

    class Meta:
        model = UserProgress
        fields = ("id", "topic", "topic_title", "topic_slug", "state", "read_at", "completed_at")
        read_only_fields = ("user", "read_at")


class BookmarkSerializer(serializers.ModelSerializer):
    topic_title = serializers.CharField(source="topic.title", read_only=True)
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)
    subject_slug = serializers.CharField(source="topic.subject.slug", read_only=True)

    class Meta:
        model = Bookmark
        fields = ("id", "topic", "topic_title", "topic_slug", "subject_slug", "created_at")
        read_only_fields = ("user", "created_at")
