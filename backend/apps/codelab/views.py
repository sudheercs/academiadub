import base64
import logging

import requests
from django.conf import settings
from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from academiadub.throttles import CodeRunRateThrottle

from .models import (
    MAX_STORAGE_BYTES,
    CodeFile,
    CodeFolder,
    CodeSnippet,
    _total_used_bytes,
)
from .serializers import (
    CodeFileDetailSerializer,
    CodeFileListSerializer,
    CodeFileUploadSerializer,
    CodeFolderSerializer,
    CodeSnippetDetailSerializer,
    CodeSnippetListSerializer,
)

logger = logging.getLogger("apps")

PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

PISTON_LANGUAGES = {
    "python": {"language": "python", "version": "3.10.0"},
    "javascript": {"language": "javascript", "version": "18.15.0"},
}


class CodeRunView(views.APIView):
    """
    Proxy endpoint that forwards code execution requests to the Piston API.
    - Open to all (unauthenticated users can try the playground)
    - Rate-limited: anon 20/min (IP-based), authenticated 60/min
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [CodeRunRateThrottle]

    def post(self, request):
        language = request.data.get("language")
        code = request.data.get("code")
        input_files = request.data.get("input_files", {})

        if not language or not code:
            return Response(
                {"error": "Language and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if language not in PISTON_LANGUAGES:
            return Response(
                {
                    "error": f"Language '{language}' not supported. Allowed: python, javascript"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        lang_config = PISTON_LANGUAGES[language]
        ext = ".py" if language == "python" else ".js"

        # Build files list for Piston
        files = [{"name": f"main{ext}", "content": code}]

        # Add input files (decoded from base64)
        for filename, b64_content in input_files.items():
            try:
                content = base64.b64decode(b64_content).decode(
                    "utf-8", errors="replace"
                )
                files.append({"name": filename, "content": content})
            except Exception as e:
                logger.warning(f"Failed to decode input file {filename}: {e}")

        timeout = getattr(settings, "CODE_RUNNER_TIMEOUT_SECONDS", 5)

        try:
            response = requests.post(
                PISTON_API_URL,
                json={
                    "language": lang_config["language"],
                    "version": lang_config["version"],
                    "files": files,
                },
                timeout=timeout + 5,
            )

            if response.status_code != 200:
                return Response(
                    {
                        "error": "Code execution service error.",
                        "stderr": response.text,
                        "exit_code": 1,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            piston_data = response.json()
            run_result = piston_data.get("run", {})

            runner_data = {
                "stdout": run_result.get("stdout", ""),
                "stderr": run_result.get("stderr", ""),
                "exit_code": run_result.get("code", 1),
                "runtime_ms": 0,
                "output_files": {},
            }

            return Response(runner_data, status=status.HTTP_200_OK)

        except requests.Timeout:
            return Response(
                {
                    "error": "Code runner timed out.",
                    "stderr": "Execution timed out.",
                    "exit_code": 124,
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as e:
            return Response(
                {
                    "error": f"Failed to contact code runner: {e!s}",
                    "stderr": "Internal runner error.",
                    "exit_code": 1,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


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
        return Response(
            {
                "used_bytes": used,
                "total_bytes": MAX_STORAGE_BYTES,
                "used_mb": used_mb,
                "total_mb": total_mb,
                "used_pct": round((used / MAX_STORAGE_BYTES) * 100, 1),
            }
        )


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
            cf = CodeFile.objects.filter(
                user=request.user, folder=folder, filename=uploaded_file.name
            ).first()
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
                    mime_type=uploaded_file.content_type or "application/octet-stream",
                )
                cf.save()

            return Response(
                CodeFileDetailSerializer(cf).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
