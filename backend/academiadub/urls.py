"""AcademiaHub URL configuration."""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static


def health_check(request):
    """Liveness probe — returns 200 if the API is running."""
    return JsonResponse({"status": "ok", "service": "academiadub-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),

    # Phase 1 — Identity & Access
    path("api/auth/", include("apps.identity.urls")),

    # Phase 2 — Catalogue
    path("api/catalogue/", include("apps.catalogue.urls")),

    # Phase 3 — Content Engine
    path("api/content/", include("apps.content.urls")),

    # Phase 4 — Downloads
    path("api/downloads/", include("apps.downloads.urls")),

    # Phase 5 — Practice & Code Lab
    # path("api/practice/", include("apps.practice.urls")),
    path("api/codelab/", include("apps.codelab.urls")),

    # Phase 6 — Classes
    # path("api/classes/", include("apps.classes.urls")),

    # Platform (cross-cutting)
    # path("api/platform/", include("apps.platform.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
