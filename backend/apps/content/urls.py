from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProgressViewSet, BookmarkViewSet

router = DefaultRouter()
router.register(r"progress", UserProgressViewSet, basename="progress")
router.register(r"bookmarks", BookmarkViewSet, basename="bookmark")

urlpatterns = [
    path("", include(router.urls)),
]
