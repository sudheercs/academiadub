"""
Django base settings for AcademiaHub.
Do NOT use this file directly — import from local.py / staging.py / production.py.
"""

import os
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured


def _env_value(name, default=None, *, cast=None):
    """Return an env value from the shell or a safe default."""
    value = os.getenv(name)
    if value is not None:
        if cast is not None:
            return cast(value)
        return value
    if default is not None:
        if cast is not None:
            if isinstance(default, str):
                return cast(default)
            return default
        return default
    return config(name, default=default, cast=cast)


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = _env_value("SECRET_KEY", default="dev-secret-key-not-for-production")
DEBUG = _env_value("DEBUG", default=False, cast=lambda value: value.lower() in {"1", "true", "yes", "on"})
ALLOWED_HOSTS = _env_value("ALLOWED_HOSTS", default="localhost", cast=Csv())

# ── Installed apps ───────────────────────────────────────────────────────────

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "storages",
]

LOCAL_APPS = [
    "apps.identity",
    "apps.catalogue",
    "apps.content",
    "apps.downloads",
    "apps.practice",
    "apps.codelab",
    "apps.classes",
    "apps.platform",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "academiadub.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "academiadub.wsgi.application"
ASGI_APPLICATION = "academiadub.asgi.application"

# ── Database ─────────────────────────────────────────────────────────────────

import dj_database_url

DATABASE_URL = os.getenv("DATABASE_URL") or config("DATABASE_URL", default="")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must be set to a mysql:// connection string.")

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)
}
_SUPPORTED_ENGINES = {
    "django.db.backends.mysql",
    "django.db.backends.postgresql",
}
if DATABASES["default"]["ENGINE"] not in _SUPPORTED_ENGINES:
    raise ImproperlyConfigured(
        f"DATABASE_URL engine '{DATABASES['default']['ENGINE']}' is not supported. "
        "Use a mysql:// or postgres:// URL."
    )

# ── Cache ─────────────────────────────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL") or ""
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "academiadub-local-cache",
        }
    }

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ── Auth ──────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = "identity.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── DRF ───────────────────────────────────────────────────────────────────────

from datetime import timedelta

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.identity.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "login": "10/minute",     # Applied to auth endpoints
        "coderun": "20/minute",   # Applied to /api/codelab/run/
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "academiadub.exception_handler.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── Internationalisation ──────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ── Static & Media ────────────────────────────────────────────────────────────

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Email ─────────────────────────────────────────────────────────────────────

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@academiadub.in")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ── AWS ───────────────────────────────────────────────────────────────────────

AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="ap-south-1")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None  # Private by default — signed URLs for access
AWS_S3_SIGNATURE_VERSION = "s3v4"

# ── CORS ──────────────────────────────────────────────────────────────────────

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
AUTH_COOKIE_DOMAIN = config("AUTH_COOKIE_DOMAIN", default="")

# ── Security headers (tightened per environment) ──────────────────────────────

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Trust proxy in prod
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ── Logging ───────────────────────────────────────────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": %(message)s}',
        },
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ── Feature flags ─────────────────────────────────────────────────────────────

ENABLE_CODE_LAB = config("ENABLE_CODE_LAB", default=False, cast=bool)
ENABLE_PAYMENTS = config("ENABLE_PAYMENTS", default=False, cast=bool)
CODE_RUNNER_SOCKET = config(
    "CODE_RUNNER_SOCKET",
    default="/run/coderunner/runner.sock",
)
CODE_RUNNER_TIMEOUT_SECONDS = config("CODE_RUNNER_TIMEOUT_SECONDS", default=5, cast=int)
