from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.exceptions.messages import get_error_message
from core.responses import ResponseInfo


def handle_exception(exc: Exception, context: dict[str, Any]) -> Response | None:

    response = exception_handler(exc, context)
    if response is None:
        return None

    original = response.data
    errors = original if isinstance(original, dict) else {"detail": original}
    response.data = ResponseInfo.body(
        ok=False,
        code=response.status_code,
        message=get_error_message(original) or "Request failed",
        data={},
        errors=errors,
        error_code=getattr(exc, "error_code", None) or getattr(exc, "auth_code", None),
    )
    return response
