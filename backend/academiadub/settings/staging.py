"""Staging settings — mirrors production, less strict secrets."""

from .base import *

DEBUG = False

# AWS SES for email
EMAIL_BACKEND = "django_ses.SESBackend"
AWS_SES_REGION_NAME = "ap-south-1"
AWS_SES_REGION_ENDPOINT = "email.ap-south-1.amazonaws.com"

# S3 for media/file storage
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
