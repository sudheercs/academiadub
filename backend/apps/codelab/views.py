import logging
import base64
import http.client
import json
import socket
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.db.models import Sum
from rest_framework import views, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from academiadub.throttles import CodeRunRateThrottle
from .models import CodeFolder, CodeSnippet, CodeFile, MAX_STORAGE_BYTES, _total_used_bytes
from .serializers import (
    CodeFolderSerializer,
    CodeSnippetListSerializer,
    CodeSnippetDetailSerializer,
    CodeFileListSerializer,
    CodeFileDetailSerializer,
    CodeFileUploadSerializer,
    StorageUsageSerializer,
)

logger = logging.getLogger("apps")


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


class CodeRunView(views.APIView):
    """
    Proxy endpoint that forwards code execution requests to the isolated coderunner service.
    - Open to all (unauthenticated users can try the playground)
    - Rate-limited: anon 20/min (IP-based), authenticated 60/min
    - Now supports input_files (sent to runner) and output_files (returned from runner).
      If authenticated, output_files are auto-saved to the user's library.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [CodeRunRateThrottle]

    def post(self, request):
        language = request.data.get("language")
        code = request.data.get("code")
        input_files = request.data.get("input_files", {})  # {filename: base64_content}
        folder_id = request.data.get("folder_id") # optional folder to save outputs into

        if not language or not code:
            return Response({"error": "Language and code are required."}, status=status.HTTP_400_BAD_REQUEST)

        timeout = getattr(settings, "CODE_RUNNER_TIMEOUT_SECONDS", 5)

        connection = UnixSocketHTTPConnection(settings.CODE_RUNNER_SOCKET, timeout + 1)
        try:
            connection.request(
                "POST",
                "/run",
                body=json.dumps({
                    "language": language,
                    "code": code,
                    "input_files": input_files,
                }),
                headers={"Content-Type": "application/json"},
            )
            runner_response = connection.getresponse()
            response_body = runner_response.read(12 * 1024 * 1024 + 1)
            if len(response_body) > 12 * 1024 * 1024:
                return Response(
                    {"error": "Code runner returned an oversized response."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            runner_data = json.loads(response_body)
            
            # Auto-save output files if authenticated
            if request.user.is_authenticated and "output_files" in runner_data:
                save_warnings = []
                folder = None
                if folder_id:
                    folder = CodeFolder.objects.filter(id=folder_id, user=request.user).first()
                
                for filename, b64_content in runner_data["output_files"].items():
                    try:
                        # Try to update existing file in same folder with same name, or create new
                        cf = CodeFile.objects.filter(user=request.user, folder=folder, filename=filename).first()
                        if cf:
                            cf.content_b64 = b64_content
                            cf.save()
                        else:
                            cf = CodeFile.from_b64(
                                user=request.user,
                                filename=filename,
                                b64_content=b64_content,
                                folder=folder
                            )
                            cf.save()
                    except (DatabaseError, ValidationError, ValueError) as e:
                        logger.warning(f"Failed to auto-save output file {filename}: {e}")
                        save_warnings.append({
                            "filename": filename,
                            "detail": "Could not save to your code library.",
                        })
                if save_warnings:
                    runner_data["save_warnings"] = save_warnings

            return Response(runner_data, status=runner_response.status)

        except (socket.timeout, TimeoutError):
            return Response(
                {"error": "Code runner timed out.", "stderr": "Execution timed out.", "exit_code": 124},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:
            return Response(
                {"error": f"Failed to contact code runner: {str(e)}", "stderr": "Internal runner error.", "exit_code": 1},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            connection.close()


# ── Code Storage ──────────────────────────────────────────────────────────────

class CodeFolderViewSet(viewsets.ModelViewSet):
    """
    CRUD for the current user's code folders.
    """
    serializer_class = CodeFolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CodeFolder.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CodeSnippetViewSet(viewsets.ModelViewSet):
    """
    CRUD for the current user's saved code snippets.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CodeSnippet.objects.filter(user=self.request.user)
        folder_id = self.request.query_params.get("folder")
        if folder_id == "none":
            qs = qs.filter(folder__isnull=True)
        elif folder_id:
            qs = qs.filter(folder_id=folder_id)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CodeSnippetListSerializer
        return CodeSnippetDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="storage")
    def storage(self, request):
        """Returns current quota usage for the authenticated user."""
        used = _total_used_bytes(request.user)
        used_mb = round(used / (1024 * 1024), 2)
        total_mb = round(MAX_STORAGE_BYTES / (1024 * 1024), 2)
        return Response({
            "used_bytes": used,
            "total_bytes": MAX_STORAGE_BYTES,
            "used_mb": used_mb,
            "total_mb": total_mb,
            "used_pct": round((used / MAX_STORAGE_BYTES) * 100, 1),
        })

class CodeFileViewSet(viewsets.ModelViewSet):
    """
    CRUD for the current user's saved files.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CodeFile.objects.filter(user=self.request.user)
        folder_id = self.request.query_params.get("folder")
        if folder_id == "none":
            qs = qs.filter(folder__isnull=True)
        elif folder_id:
            qs = qs.filter(folder_id=folder_id)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CodeFileListSerializer
        return CodeFileDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """Handle multipart file uploads to CodeFile storage."""
        serializer = CodeFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data["file"]
        folder_id = serializer.validated_data.get("folder")
        
        folder = None
        if folder_id:
            folder = CodeFolder.objects.filter(id=folder_id, user=request.user).first()
            
        try:
            raw_bytes = uploaded_file.read()
            b64_content = base64.b64encode(raw_bytes).decode("ascii")
            
            # Check if file exists to overwrite, else create
            cf = CodeFile.objects.filter(user=request.user, folder=folder, filename=uploaded_file.name).first()
            if cf:
                cf.content_b64 = b64_content
                cf.mime_type = uploaded_file.content_type
                cf.save()
            else:
                cf = CodeFile.from_b64(
                    user=request.user,
                    filename=uploaded_file.name,
                    b64_content=b64_content,
                    folder=folder,
                    mime_type=uploaded_file.content_type or "application/octet-stream"
                )
                cf.save()
                
            return Response(CodeFileDetailSerializer(cf).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
