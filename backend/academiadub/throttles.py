"""
Tighter rate throttles for sensitive endpoints.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """10 login attempts per minute per IP."""
    scope = "login"


class CodeRunRateThrottle(UserRateThrottle):
    """20 code executions per minute per authenticated user."""
    scope = "coderun"
