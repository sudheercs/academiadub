from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CodeRunView, CodeFolderViewSet, CodeSnippetViewSet, CodeFileViewSet

router = DefaultRouter()
router.register(r"folders",  CodeFolderViewSet,  basename="code-folder")
router.register(r"snippets", CodeSnippetViewSet, basename="code-snippet")
router.register(r"files",    CodeFileViewSet,    basename="code-file")

urlpatterns = [
    path("run/", CodeRunView.as_view(), name="codelab-run"),
    path("", include(router.urls)),
]
