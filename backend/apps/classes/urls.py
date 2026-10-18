from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    AssignmentViewSet,
    ClassCodeLoginView,
    ClassroomViewSet,
    JoinByCodeView,
)

router = DefaultRouter()
router.register("classrooms", ClassroomViewSet, basename="classroom")

# Nested: /classrooms/{classroom_pk}/assignments/
classes_router = routers.NestedDefaultRouter(router, "classrooms", lookup="classroom")
classes_router.register(
    "assignments", AssignmentViewSet, basename="classroom-assignments"
)

urlpatterns = [
    path("", include(router.urls)),
    path("", include(classes_router.urls)),
    path("join/", JoinByCodeView.as_view(), name="join-by-code"),
    path("login-with-code/", ClassCodeLoginView.as_view(), name="class-code-login"),
]
