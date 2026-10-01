import requests
from django.conf import settings
from rest_framework import views, status, permissions
from rest_framework.response import Response

class CodeRunView(views.APIView):
    """
    Proxy endpoint that forwards code execution requests to the isolated coderunner service.
    """
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        language = request.data.get("language")
        code = request.data.get("code")

        if not language or not code:
            return Response({"error": "Language and code are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Forward to coderunner
        runner_url = f"{settings.CODE_RUNNER_URL}/run"
        timeout = getattr(settings, "CODE_RUNNER_TIMEOUT_SECONDS", 5)

        try:
            res = requests.post(
                runner_url,
                json={"language": language, "code": code},
                timeout=timeout + 1 # Add 1s buffer for the internal timeout
            )
            res.raise_for_status()
            return Response(res.json(), status=res.status_code)
        except requests.exceptions.Timeout:
            return Response(
                {"error": "Code runner timed out.", "stderr": "Execution timed out.", "exit_code": 124},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Failed to contact code runner: {str(e)}", "stderr": "Internal runner error.", "exit_code": 1},
                status=status.HTTP_502_BAD_GATEWAY
            )
