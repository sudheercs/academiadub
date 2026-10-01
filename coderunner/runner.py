import json
import os
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

ALLOWED_LANGUAGES = os.getenv("ALLOWED_LANGUAGES", "python,javascript").split(",")
MAX_RUNTIME_SECONDS = int(os.getenv("MAX_RUNTIME_SECONDS", "5"))


class RunnerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "code-runner"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/run":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            language = body.get("language", "")
            code = body.get("code", "")

            if language not in ALLOWED_LANGUAGES:
                self._respond(400, {"error": f"Language '{language}' not supported. Allowed: {ALLOWED_LANGUAGES}"})
                return

            ext = ".py" if language == "python" else ".js"
            cmd = ["python"] if language == "python" else ["node"]

            # Create a temporary file to hold the code
            with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
                f.write(code)
                filepath = f.name

            cmd.append(filepath)

            start_time = time.time()
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=MAX_RUNTIME_SECONDS
                )
                stdout = result.stdout
                stderr = result.stderr
                exit_code = result.returncode
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode() if e.stdout else ""
                stderr = f"Execution timed out after {MAX_RUNTIME_SECONDS} seconds."
                exit_code = 124
            finally:
                os.remove(filepath)

            runtime_ms = int((time.time() - start_time) * 1000)

            self._respond(200, {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "runtime_ms": runtime_ms,
            })
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9000), RunnerHandler)
    print(f"Code runner listening on :9000 (allowed: {ALLOWED_LANGUAGES})")
    server.serve_forever()
