"""Production settings — Render (backend) + Supabase (DB) + Cloudflare Workers (frontend).

Environment variables required on Render:
  SECRET_KEY, DATABASE_URL, REDIS_URL, ALLOWED_HOSTS,
  CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS,
  DEFAULT_FROM_EMAIL, EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
  AUTH_COOKIE_DOMAIN
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# ── Security ──────────────────────────────────────────────────────────────────

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Render terminates TLS at the proxy layer and forwards via this header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── Supabase PostgreSQL — enforce SSL ─────────────────────────────────────────
# DATABASE_URL is injected by Render from the env var.
# Supabase requires SSL — append ?sslmode=require if not already in the URL.

import dj_database_url as _dj  # noqa: E402
import os as _os  # noqa: E402

_db_url = _os.getenv("DATABASE_URL", "")
if _db_url and "sslmode" not in _db_url:
    _db_url += ("&" if "?" in _db_url else "?") + "sslmode=require"

DATABASES = {
    "default": _dj.parse(
        _db_url,
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}
# Override the engine check from base.py — Supabase is PostgreSQL
_SUPPORTED_ENGINES = {
    "django.db.backends.postgresql",
    "django.db.backends.mysql",
}

# ── Email — SMTP (use Resend, Brevo, or any SMTP service) ────────────────────
# Set EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD on Render dashboard
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# ── Static files — WhiteNoise (already in MIDDLEWARE in base.py) ──────────────
# Render serves static files directly from the dyno via WhiteNoise.
# For media files (uploads), use Supabase Storage or AWS S3.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ── Sessions ──────────────────────────────────────────────────────────────────
# Persist sessions in Supabase DB with cache fallback, so users/admins don't get
# logged out when Render sleeps or restarts.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"

