FROM python:3.12-slim

WORKDIR /runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create an unprivileged user for code execution
RUN useradd -m -s /bin/sh sandbox

COPY runner.py .

# NOTE: Phase 5 will harden this with gVisor or Firecracker.
# For Phase 0, this is a stub that returns a mock response.

EXPOSE 9000

USER sandbox
CMD ["python", "runner.py"]
