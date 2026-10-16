from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuizViewSet, QuizAdminViewSet

router = DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"admin/quizzes", QuizAdminViewSet, basename="quiz-admin")

urlpatterns = [
    path("", include(router.urls)),
]
