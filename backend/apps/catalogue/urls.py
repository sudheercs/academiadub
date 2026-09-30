from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import SubjectViewSet, TopicViewSet, EditorTopicVersionViewSet

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'topics', TopicViewSet, basename='topic')

# Nested router for /topics/:id/versions/
topics_router = NestedDefaultRouter(router, r'topics', lookup='topic')
topics_router.register(r'versions', EditorTopicVersionViewSet, basename='topic-versions')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(topics_router.urls)),
]
