from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.permissions import (
    RequireTopicManagePermission,
    RequireTopicPublishPermission,
    subject_scope_ids,
)

from .models import Course, Subject, Topic, TopicVersion, TopicVersionEvent
from .serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    SubjectSerializer,
    TopicDetailSerializer,
    TopicListSerializer,
    TopicVersionSerializer,
)


def can_manage_all_topics(user):
    return user.is_authenticated and user.has_permission("topic:manage")


def visible_editorial_objects(queryset, user, subject_lookup):
    if can_manage_all_topics(user):
        return queryset
    scoped_subjects = [
        int(subject_id) for subject_id in subject_scope_ids(user, "topic:manage")
    ]
    return queryset.filter(
        Q(status="published") | Q(**{f"{subject_lookup}__in": scoped_subjects})
    )


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for browsing subjects.
    Only published subjects are visible to standard users.
    """

    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return visible_editorial_objects(Subject.objects.all(), self.request.user, "id")


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for browsing courses.
    Supports filtering by subject via ?subject=<slug>.
    """

    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer

    def get_queryset(self):
        subject_slug = self.request.query_params.get("subject", None)
        queryset = Course.objects.all().select_related("subject")

        queryset = visible_editorial_objects(queryset, self.request.user, "subject_id")

        if subject_slug:
            queryset = queryset.filter(subject__slug=subject_slug)

        return queryset


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for browsing topics.
    Supports filtering by subject via ?subject=<slug> and course via ?course=<slug>.
    """

    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TopicDetailSerializer
        return TopicListSerializer

    def get_queryset(self):
        subject_slug = self.request.query_params.get("subject", None)
        course_slug = self.request.query_params.get("course", None)
        queryset = Topic.objects.all().select_related("course", "course__subject")

        queryset = visible_editorial_objects(
            queryset, self.request.user, "course__subject_id"
        )

        if subject_slug:
            queryset = queryset.filter(course__subject__slug=subject_slug)

        if course_slug:
            queryset = queryset.filter(course__slug=course_slug)

        return queryset


class EditorTopicVersionViewSet(viewsets.ModelViewSet):
    """
    CMS API for editors to create and manage topic versions.
    """

    serializer_class = TopicVersionSerializer
    permission_classes = [permissions.IsAuthenticated, RequireTopicManagePermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def record_event(self, version, action, note=""):
        TopicVersionEvent.objects.create(
            topic=version.topic,
            version=version,
            version_no=version.version_no,
            actor=self.request.user,
            action=action,
            note=note,
        )

    def get_permission_scope(self, permission_key):
        topic = get_object_or_404(
            Topic.objects.select_related("course"),
            pk=self.kwargs.get("topic_pk"),
        )
        return "subject", topic.course.subject_id

    def get_permissions(self):
        required_permission = (
            RequireTopicPublishPermission
            if self.action in ("review", "publish", "unpublish")
            else RequireTopicManagePermission
        )
        return [permissions.IsAuthenticated(), required_permission()]

    def get_queryset(self):
        topic_id = self.kwargs.get("topic_pk")
        return TopicVersion.objects.filter(topic_id=topic_id).select_related(
            "author", "topic"
        )

    def perform_create(self, serializer):
        topic = get_object_or_404(Topic, pk=self.kwargs.get("topic_pk"))
        latest = topic.versions.order_by("-version_no").first()
        next_version = (latest.version_no + 1) if latest else 1
        with transaction.atomic():
            version = serializer.save(
                topic=topic,
                author=self.request.user,
                version_no=next_version,
                state="draft",
            )
            self.record_event(version, "created")

    def perform_update(self, serializer):
        if serializer.instance.state != "draft":
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"state": "Only draft versions can be edited."})
        with transaction.atomic():
            version = serializer.save()
            self.record_event(version, "updated")

    def perform_destroy(self, instance):
        if instance.state != "draft":
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"state": "Only draft versions can be deleted."})
        instance.delete()

    @action(detail=True, methods=["post"])
    def submit(self, request, topic_pk=None, pk=None):
        version = self.get_object()
        if version.state != "draft":
            return Response(
                {"detail": "Only draft versions can be submitted."}, status=400
            )
        with transaction.atomic():
            version.state = "in_review"
            version.save(update_fields=["state", "updated_at"])
            self.record_event(version, "submitted")
        return Response(self.get_serializer(version).data)

    @action(detail=True, methods=["post"])
    def review(self, request, topic_pk=None, pk=None):
        version = self.get_object()
        if version.state != "in_review":
            return Response(
                {"detail": "Only in-review versions can be reviewed."}, status=400
            )
        if version.author_id == request.user.id and not request.user.is_superuser:
            return Response(
                {"detail": "Authors cannot review their own versions."}, status=403
            )

        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            return Response({"approved": "A boolean value is required."}, status=400)
        version.state = "approved" if approved else "draft"
        version.review_note = str(request.data.get("review_note", ""))[:5000]
        with transaction.atomic():
            version.save(update_fields=["state", "review_note", "updated_at"])
            self.record_event(
                version,
                "approved" if approved else "returned",
                version.review_note,
            )
        return Response(self.get_serializer(version).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, topic_pk=None, pk=None):
        version = self.get_object()
        if version.state != "approved":
            return Response(
                {"detail": "Only approved versions can be published."}, status=400
            )

        with transaction.atomic():
            topic = Topic.objects.select_for_update().get(pk=version.topic_id)
            previous_versions = list(
                topic.versions.filter(state="published").exclude(pk=version.pk)
            )
            for previous in previous_versions:
                previous.state = "archived"
                previous.save(update_fields=["state", "updated_at"])
                self.record_event(previous, "archived")
            version.state = "published"
            version.save(update_fields=["state", "updated_at"])
            topic.current_version_id = version.version_no
            topic.status = "published"
            topic.save(update_fields=["current_version_id", "status", "updated_at"])
            self.record_event(version, "published")
        return Response(self.get_serializer(version).data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, topic_pk=None, pk=None):
        version = self.get_object()
        topic = version.topic
        if (
            version.state != "published"
            or topic.current_version_id != version.version_no
        ):
            return Response(
                {"detail": "This version is not currently published."}, status=400
            )
        with transaction.atomic():
            version.state = "archived"
            version.save(update_fields=["state", "updated_at"])
            topic.current_version_id = None
            topic.status = "draft"
            topic.save(update_fields=["current_version_id", "status", "updated_at"])
            self.record_event(version, "unpublished")
        return Response(self.get_serializer(version).data)


class GlobalSearchView(APIView):
    """
    Search across subjects, courses, and topics.
    Usage: /api/catalogue/search/?q=python
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"results": []})

        subjects = Subject.objects.filter(name__icontains=query)
        courses = Course.objects.filter(title__icontains=query)

        # Search by topic title
        topic_ids = set(
            Topic.objects.filter(title__icontains=query).values_list("id", flat=True)
        )

        # Search deep inside the JSON blocks of the current version
        matching_content = TopicVersion.objects.filter(
            version_no=F("topic__current_version_id"), blocks__icontains=query
        ).values_list("topic_id", flat=True)
        topic_ids.update(matching_content)

        topics = Topic.objects.filter(id__in=topic_ids)

        subjects = visible_editorial_objects(subjects, request.user, "id")
        courses = visible_editorial_objects(courses, request.user, "subject_id")
        topics = visible_editorial_objects(topics, request.user, "course__subject_id")

        results = []
        for s in subjects[:5]:
            results.append(
                {
                    "id": s.id,
                    "type": "subject",
                    "title": s.name,
                    "url": f"/subjects/{s.slug}",
                }
            )

        for c in courses.select_related("subject")[:5]:
            results.append(
                {
                    "id": c.id,
                    "type": "course",
                    "title": c.title,
                    "url": f"/subjects/{c.subject.slug}",
                }
            )

        for t in topics.select_related("course", "course__subject")[:10]:
            results.append(
                {
                    "id": t.id,
                    "type": "topic",
                    "title": t.title,
                    "url": f"/subjects/{t.course.subject.slug}/{t.slug}",
                }
            )

        return Response({"results": results})
