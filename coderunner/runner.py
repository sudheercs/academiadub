"""
AcademiaHub Code Runner
=======================
Sandboxed execution service.  POST /run runs arbitrary Python or JavaScript
code inside a temporary working directory and returns stdout, stderr, exit_code,
runtime, and any files the code wrote to disk.

Virtual filesystem API
----------------------
Request body (JSON):
  language    : "python" | "javascript"
  code        : str — the code to execute
  input_files : {filename: base64_content}  (optional)
                Files to inject into the working directory before execution.
                The student's code can open() them by name directly.

Response body (JSON):
  stdout      : str
  stderr      : str
  exit_code   : int
  runtime_ms  : int
  output_files: {filename: base64_content}
                Every regular file found in the working directory after execution
                (excluding the script itself).  Capped at 20 files, 10 MB total.
"""

import base64
import binascii
import grp
import json
import os
import pwd
import resource
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler
from socketserver import UnixStreamServer

ALLOWED_LANGUAGES = [
    language.strip()
    for language in os.getenv("ALLOWED_LANGUAGES", "python,javascript").split(",")
    if language.strip()
]
MAX_RUNTIME_SECONDS = int(os.getenv("MAX_RUNTIME_SECONDS", "5"))
MAX_OUTPUT_FILES = 20
MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MB total output files cap
MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_CODE_BYTES = 512 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_STDIO_BYTES = 256 * 1024
SOCKET_PATH = os.getenv("CODE_RUNNER_SOCKET", "/run/coderunner/runner.sock")


def _collect_output_files(workdir: str, script_name: str) -> dict[str, str]:
    """
    Walk workdir and collect every regular file except the script itself.
    Returns {relative_path: base64_encoded_content}.
    Stops once total bytes exceeds MAX_OUTPUT_BYTES or MAX_OUTPUT_FILES is reached.
    """
    collected = {}
    total_bytes = 0

    for root, dirs, files in os.walk(workdir):
        # Skip hidden directories (e.g. __pycache__)
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for fname in files:
            if len(collected) >= MAX_OUTPUT_FILES:
                break

            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, workdir)

            # Skip the script file itself
            if rel == script_name:
                continue

            try:
                if os.path.islink(fpath):
                    continue
                size = os.path.getsize(fpath)
                if total_bytes + size > MAX_OUTPUT_BYTES:
                    continue  # Skip oversized files silently
                with open(fpath, "rb") as f:
                    raw = f.read()
                collected[rel] = base64.b64encode(raw).decode("ascii")
                total_bytes += size
            except OSError:
                pass  # Ignore unreadable files

    return collected


class RunnerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "code-runner"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/run":
            self._respond(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                self._respond(413, {"error": "Request body is too large."})
                return
            body = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self._respond(400, {"error": "Invalid request body."})
            return
        if not isinstance(body, dict):
            self._respond(400, {"error": "Request body must be a JSON object."})
            return

        language = body.get("language", "")
        code = body.get("code", "")
        input_files = body.get("input_files", {})  # {filename: base64_content}

        if language not in ALLOWED_LANGUAGES:
            self._respond(
                400,
                {
                    "error": f"Language '{language}' not supported. Allowed: {ALLOWED_LANGUAGES}"
                },
            )
            return
        if not isinstance(code, str) or len(code.encode("utf-8")) > MAX_CODE_BYTES:
            self._respond(413, {"error": "Code is missing or exceeds the size limit."})
            return
        if not isinstance(input_files, dict) or len(input_files) > MAX_OUTPUT_FILES:
            self._respond(
                400, {"error": "input_files must be an object with at most 20 files."}
            )
            return

        ext = ".py" if language == "python" else ".js"
        cmd_prefix = (
            ["python"] if language == "python" else ["node", "--max-old-space-size=128"]
        )
        script_name = f"__student_code{ext}"

        # ── Create an isolated working directory for this run ──────────────────
        workdir = tempfile.mkdtemp(prefix="coderun_")
        try:
            total_input_bytes = 0
            for rel_path, b64_content in input_files.items():
                try:
                    if (
                        not isinstance(rel_path, str)
                        or not rel_path
                        or rel_path in (".", "..")
                        or os.path.basename(rel_path) != rel_path
                        or not isinstance(b64_content, str)
                    ):
                        raise ValueError("Invalid input filename or file content.")
                    raw = base64.b64decode(b64_content, validate=True)
                    total_input_bytes += len(raw)
                    if (
                        len(raw) > MAX_FILE_BYTES
                        or total_input_bytes > MAX_REQUEST_BYTES
                    ):
                        raise ValueError("Input files exceed the size limit.")
                    with open(os.path.join(workdir, rel_path), "wb") as f:
                        f.write(raw)
                except (ValueError, binascii.Error):
                    self._respond(400, {"error": "Invalid input file data."})
                    return

            # Write the student's code
            script_path = os.path.join(workdir, script_name)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            student = pwd.getpwnam("student")
            for root, directories, files in os.walk(workdir):
                os.chmod(root, 0o700)
                os.chown(root, student.pw_uid, student.pw_gid)
                for name in files:
                    path = os.path.join(root, name)
                    if os.path.islink(path):
                        continue
                    os.chmod(path, 0o600)
                    os.chown(path, student.pw_uid, student.pw_gid)

            cmd = cmd_prefix + [script_name]
            start_time = time.time()
            with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    cwd=workdir,
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": workdir},
                    close_fds=True,
                    start_new_session=True,
                    preexec_fn=_limit_student_process,
                )
                try:
                    process.wait(timeout=MAX_RUNTIME_SECONDS)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    stderr_file.write(
                        f"\nExecution timed out after {MAX_RUNTIME_SECONDS} seconds.".encode()
                    )
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout_file.seek(0)
                stderr_file.seek(0)
                stdout = stdout_file.read(MAX_STDIO_BYTES).decode(
                    "utf-8", errors="replace"
                )
                stderr = stderr_file.read(MAX_STDIO_BYTES).decode(
                    "utf-8", errors="replace"
                )
                exit_code = process.returncode

            runtime_ms = int((time.time() - start_time) * 1000)
            output_files = _collect_output_files(workdir, script_name)

        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        self._respond(
            200,
            {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "runtime_ms": runtime_ms,
                "output_files": output_files,  # {filename: base64}
            },
        )

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def _limit_student_process():
    student = pwd.getpwnam("student")
    cpu_limit = MAX_RUNTIME_SECONDS + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setgroups([])
    os.setgid(student.pw_gid)
    os.setuid(student.pw_uid)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    server = UnixStreamServer(SOCKET_PATH, RunnerHandler)
    os.chmod(SOCKET_PATH, 0o660)
    os.chown(
        SOCKET_PATH, pwd.getpwnam("sandbox").pw_uid, grp.getgrnam("runner-api").gr_gid
    )
    server.serve_forever()
