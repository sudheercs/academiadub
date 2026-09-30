"""
Code Runner — Phase 0 stub.
Returns a mock response. Real sandbox (gVisor/Firecracker) is implemented in Phase 5.
Listens on port 9000, accepts POST /run with JSON body: {language, code, tests}.
"""

import json
import os
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

            if language not in ALLOWED_LANGUAGES:
                self._respond(400, {"error": f"Language '{language}' not supported. Allowed: {ALLOWED_LANGUAGES}"})
                return

            # Phase 0 stub — real execution in Phase 5
            self._respond(200, {
                "stdout": "# Code runner is a stub in Phase 0.\n# Real sandboxed execution arrives in Phase 5.",
                "stderr": "",
                "exit_code": 0,
                "runtime_ms": 0,
                "stub": True,
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
        pass  # Suppress default HTTP logging; use structured logging in Phase 5


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9000), RunnerHandler)
    print(f"Code runner stub listening on :9000 (allowed: {ALLOWED_LANGUAGES})")
    server.serve_forever()
