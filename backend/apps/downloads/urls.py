from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DownloadAdminViewSet, DownloadViewSet

router = DefaultRouter()
router.register(r"files", DownloadViewSet, basename="download")
router.register(r"admin/files", DownloadAdminViewSet, basename="download-admin")

urlpatterns = [
    path("", include(router.urls)),
]
