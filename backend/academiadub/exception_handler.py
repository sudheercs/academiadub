"""
Custom DRF exception handler.
Normalises all error responses to a consistent JSON envelope:
  { "error": "...", "detail": "..." }
and logs server errors with full stack traces.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — log it and return 500
        logger.exception("Unhandled exception in view %s", context.get("view"))
        return Response(
            {"error": "An internal server error occurred.", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Normalise DRF's default error shape
    if isinstance(response.data, dict):
        if "detail" not in response.data and "error" not in response.data:
            response.data = {"error": response.data}
    elif isinstance(response.data, list):
        response.data = {"error": response.data}

    return response
