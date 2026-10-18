from django.utils import timezone
from rest_framework import permissions, viewsets

from .models import Bookmark, UserProgress
from .serializers import BookmarkSerializer, UserProgressSerializer


class UserProgressViewSet(viewsets.ModelViewSet):
    """
    CRUD for the current user's topic progress.
    POST /api/content/progress/ with { topic, state } to mark progress.
    """

    serializer_class = UserProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProgress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        state = serializer.validated_data.get("state", "in_progress")
        completed_at = timezone.now() if state == "completed" else None
        serializer.save(user=self.request.user, completed_at=completed_at)

    def perform_update(self, serializer):
        state = serializer.validated_data.get("state", serializer.instance.state)
        completed_at = (
            timezone.now() if state == "completed" else serializer.instance.completed_at
        )
        serializer.save(completed_at=completed_at)


class BookmarkViewSet(viewsets.ModelViewSet):
    """
    Manage the current user's bookmarks.
    """

    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
