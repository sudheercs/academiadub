from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import (CourseViewSet, EditorTopicVersionViewSet, GlobalSearchView,
                    SubjectViewSet, TopicViewSet)

router = DefaultRouter()
router.register(r"subjects", SubjectViewSet, basename="subject")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"topics", TopicViewSet, basename="topic")

# Nested router for /topics/:id/versions/
topics_router = NestedDefaultRouter(router, r"topics", lookup="topic")
topics_router.register(
    r"versions", EditorTopicVersionViewSet, basename="topic-versions"
)

urlpatterns = [
    path("search/", GlobalSearchView.as_view(), name="global-search"),
    path("", include(router.urls)),
    path("", include(topics_router.urls)),
]
