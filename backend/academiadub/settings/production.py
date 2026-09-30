"""Production settings — maximum security, no DEBUG."""
from .staging import *  # noqa: F401, F403

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True

# Tighten Content-Security-Policy via a middleware or header at the load balancer level
