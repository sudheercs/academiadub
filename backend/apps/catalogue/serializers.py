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
    access_gated = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = (
            "id", "subject", "parent", "slug", "title",
            "difficulty", "access_level", "status", "order",
            "content", "access_gated"
        )

    def _requesting_user(self):
        return self.context.get("request") and self.context["request"].user

    def _can_access(self, obj):
        user = self._requesting_user()
        if obj.access_level == "free":
            return True
        if obj.access_level == "login":
            return user and user.is_authenticated
        if obj.access_level == "paid":
            return user and (user.is_staff or getattr(user, "has_active_subscription", False))
        return False

    def get_access_gated(self, obj):
        """True when the user is not allowed to see the content."""
        return not self._can_access(obj)

    def get_content(self, obj):
        if not self._can_access(obj):
            return []  # Blocked — return empty, frontend shows the gate
        if obj.status == "published" and obj.current_version_id:
            version = obj.versions.filter(version_no=obj.current_version_id).first()
            if version:
                return version.blocks
        return []
