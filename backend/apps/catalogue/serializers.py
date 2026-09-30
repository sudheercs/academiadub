from rest_framework import serializers
from .models import Subject, Topic, TopicVersion


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "slug", "name", "icon", "description", "status")


class TopicListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = Topic
        fields = ("id", "subject", "parent", "slug", "title", "difficulty", "access_level", "status", "order")


class TopicVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicVersion
        fields = ("id", "version_no", "blocks", "author", "state", "review_note", "created_at")
        read_only_fields = ("author", "created_at", "version_no")


class TopicDetailSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ("id", "subject", "parent", "slug", "title", "difficulty", "access_level", "status", "order", "content")

    def get_content(self, obj):
        # Only return the content blocks if it's published and we have a current_version_id
        if obj.status == "published" and obj.current_version_id:
            version = obj.versions.filter(version_no=obj.current_version_id).first()
            if version:
                return version.blocks
        return []
