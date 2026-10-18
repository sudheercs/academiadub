from urllib.parse import urlparse

from rest_framework import serializers

from .models import Course, Subject, Topic, TopicVersion


class SubjectSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(source="courses.count", read_only=True)

    class Meta:
        model = Subject
        fields = ("id", "slug", "name", "icon", "description", "status", "course_count")


class CourseSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = (
            "id",
            "slug",
            "title",
            "name",
            "icon",
            "difficulty",
            "status",
            "order",
        )


class TopicListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = Topic
        fields = (
            "id",
            "subject",
            "course",
            "parent",
            "slug",
            "title",
            "difficulty",
            "access_level",
            "status",
            "order",
        )


class CourseListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    topic_count = serializers.IntegerField(source="topics.count", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "subject",
            "slug",
            "title",
            "name",
            "description",
            "icon",
            "difficulty",
            "status",
            "order",
            "topic_count",
        )


class CourseDetailSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    topics = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "subject",
            "slug",
            "title",
            "name",
            "description",
            "icon",
            "difficulty",
            "status",
            "order",
            "topics",
        )

    def get_topics(self, obj):
        user = self.context.get("request") and self.context["request"].user
        topics = obj.topics.all()
        if not (
            user
            and user.is_authenticated
            and user.has_permission("topic:manage", "subject", obj.subject_id)
        ):
            topics = topics.filter(status="published")
        return TopicListSerializer(topics, many=True, context=self.context).data


class TopicVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicVersion
        fields = (
            "id",
            "version_no",
            "blocks",
            "author",
            "state",
            "review_note",
            "created_at",
        )
        read_only_fields = (
            "author",
            "created_at",
            "version_no",
            "state",
            "review_note",
        )

    def validate_blocks(self, blocks):
        if not isinstance(blocks, list):
            raise serializers.ValidationError("Blocks must be a list.")
        if len(blocks) > 500:
            raise serializers.ValidationError(
                "A topic cannot contain more than 500 blocks."
            )

        block_fields = {
            "markdown": ({"content"}, {"content"}),
            "text": ({"content"}, {"content"}),
            "code": ({"content"}, {"content", "language"}),
            "code_lab": ({"content"}, {"content", "language"}),
            "youtube_video": ({"url"}, {"url", "caption"}),
            "callout": ({"content"}, {"content"}),
            "image": ({"src", "alt"}, {"src", "alt", "caption"}),
        }
        for index, block in enumerate(blocks):
            if not isinstance(block, dict):
                raise serializers.ValidationError(
                    {index: "Each block must be an object."}
                )
            block_type = block.get("type")
            if block_type not in block_fields:
                raise serializers.ValidationError({index: "Unsupported block type."})
            required, allowed = block_fields[block_type]
            if set(block) - (allowed | {"type"}):
                raise serializers.ValidationError(
                    {index: "Block contains unsupported fields."}
                )
            for field in required:
                if not isinstance(block.get(field), str):
                    raise serializers.ValidationError(
                        {index: f"{field} must be a string."}
                    )
            for field, value in block.items():
                if field != "type" and not isinstance(value, str):
                    raise serializers.ValidationError(
                        {index: f"{field} must be a string."}
                    )
                if field != "type" and len(value) > 100_000:
                    raise serializers.ValidationError({index: f"{field} is too long."})
            if block_type == "youtube_video":
                try:
                    parsed_url = urlparse(block["url"])
                    hostname = (parsed_url.hostname or "").lower()
                except ValueError:
                    parsed_url = None
                    hostname = ""
                if (
                    not parsed_url
                    or parsed_url.scheme != "https"
                    or hostname
                    not in {
                        "youtube.com",
                        "www.youtube.com",
                        "youtu.be",
                        "youtube-nocookie.com",
                        "www.youtube-nocookie.com",
                    }
                ):
                    raise serializers.ValidationError(
                        {index: "Video URL must point to YouTube."}
                    )
            if block_type == "image":
                src = block["src"]
                if not (src.startswith(("https://", "/media/"))):
                    raise serializers.ValidationError(
                        {index: "Image source must be HTTPS or a media path."}
                    )
        return blocks


class TopicDetailSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    course = CourseSummarySerializer(read_only=True)
    content = serializers.SerializerMethodField()
    access_gated = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = (
            "id",
            "subject",
            "course",
            "parent",
            "slug",
            "title",
            "difficulty",
            "access_level",
            "status",
            "order",
            "content",
            "access_gated",
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
            return user and (
                user.is_superuser or getattr(user, "has_active_subscription", False)
            )
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
