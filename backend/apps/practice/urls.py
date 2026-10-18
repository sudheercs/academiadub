from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import QuizAdminViewSet, QuizViewSet

router = DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"admin/quizzes", QuizAdminViewSet, basename="quiz-admin")

urlpatterns = [
    path("", include(router.urls)),
]
