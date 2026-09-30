"""Local development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relaxed CORS for local dev
CORS_ALLOW_ALL_ORIGINS = True

# Django debug toolbar (optional — install separately)
INTERNAL_IPS = ["127.0.0.1"]

# Disable throttling in local dev
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
