from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookmarkViewSet, UserProgressViewSet

router = DefaultRouter()
router.register(r"progress", UserProgressViewSet, basename="progress")
router.register(r"bookmarks", BookmarkViewSet, basename="bookmark")

urlpatterns = [
    path("", include(router.urls)),
]
