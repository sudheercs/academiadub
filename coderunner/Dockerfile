FROM python:3.12-slim

WORKDIR /runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# The runner runs as root only to create a restricted Unix socket and drop the
# code subprocess to a separate UID/GID with no network access.
RUN groupadd --gid 20000 runner-api \
    && groupadd --gid 20001 student \
    && useradd --uid 20000 --gid 20000 --no-create-home --shell /usr/sbin/nologin sandbox \
    && useradd --uid 20001 --gid 20001 --no-create-home --shell /usr/sbin/nologin student

COPY runner.py .

ENV CODE_RUNNER_SOCKET=/run/coderunner/runner.sock
CMD ["python", "runner.py"]
