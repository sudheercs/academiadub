from rest_framework import viewsets, permissions
from .models import Subject, Topic, TopicVersion
from .serializers import SubjectSerializer, TopicListSerializer, TopicDetailSerializer, TopicVersionSerializer


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for browsing subjects.
    Only published subjects are visible to standard users.
    """
    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Subject.objects.all()
        return Subject.objects.filter(status="published")


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for browsing topics.
    """
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TopicDetailSerializer
        return TopicListSerializer

    def get_queryset(self):
        # Filtering by subject
        subject_slug = self.request.query_params.get('subject', None)
        queryset = Topic.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(status="published")
            
        if subject_slug:
            queryset = queryset.filter(subject__slug=subject_slug)
            
        return queryset


class EditorTopicVersionViewSet(viewsets.ModelViewSet):
    """
    CMS API for editors to create and manage topic versions.
    """
    serializer_class = TopicVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        topic_id = self.kwargs.get('topic_pk')
        if not self.request.user.is_staff:
            return TopicVersion.objects.none() # Replace with actual RBAC check later
        return TopicVersion.objects.filter(topic_id=topic_id)

    def perform_create(self, serializer):
        topic_id = self.kwargs.get('topic_pk')
        topic = Topic.objects.get(pk=topic_id)
        
        # Auto-increment version
        latest = topic.versions.order_by('-version_no').first()
        next_version = (latest.version_no + 1) if latest else 1
        
        serializer.save(topic=topic, author=self.request.user, version_no=next_version)
