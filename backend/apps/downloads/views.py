import mimetypes
# pyrefly: ignore [missing-import]
from django.http import FileResponse, Http404
from django.utils.encoding import smart_str
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Download, DownloadLog
from .serializers import DownloadSerializer, DownloadUploadSerializer


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


class DownloadViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve downloads attached to a topic.
    A separate /serve/ action streams the file with access-control checks
    and logs the download event.
    """
    serializer_class = DownloadSerializer
    permission_classes = [permissions.AllowAny]  # Queryset does access filtering

    def get_queryset(self):
        qs = Download.objects.filter(is_active=True)
        topic_id = self.request.query_params.get("topic")
        if topic_id:
            qs = qs.filter(topic_id=topic_id)
        return qs

    @action(detail=True, methods=["get"], url_path="serve")
    def serve(self, request, pk=None):
        """
        Streams the file to the client after access checks.
        In production: redirect to a short-lived S3 presigned URL instead.
        """
        download = self.get_object()
        user = request.user

        # --- Access control gates ---
        if download.access_level in ("login", "paid") and not user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        if download.access_level == "paid" and not user.is_staff:
            return Response({"detail": "Premium access required."}, status=status.HTTP_403_FORBIDDEN)

        # Log the download
        DownloadLog.objects.create(
            download=download,
            user=user if user.is_authenticated else None,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        # --- LOCAL DEV: stream from filesystem ---
        # --- PRODUCTION: replace with boto3 presigned URL redirect ---
        try:
            file_handle = download.file.open("rb")
        except Exception:
            raise Http404("File not found on storage.")

        mime = download.mime_type or (
            mimetypes.guess_type(download.file.name)[0] or "application/octet-stream"
        )
        filename = smart_str(download.file.name.split("/")[-1])

        response = FileResponse(file_handle, content_type=mime)
        
        is_download = request.query_params.get("download", "").lower() == "true"
        disposition = "attachment" if is_download else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        
        if download.file_size_bytes:
            response["Content-Length"] = download.file_size_bytes
        return response


class DownloadAdminViewSet(viewsets.ModelViewSet):
    """Staff-only CMS endpoint for uploading and managing downloads."""
    serializer_class = DownloadUploadSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Download.objects.all()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return DownloadSerializer
        return DownloadUploadSerializer
