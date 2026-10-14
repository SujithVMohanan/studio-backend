from core.exceptions.messages import get_error_message
from core.responses import ResponseInfo
from rest_framework.views import exception_handler


def handle_exception(exc, context):

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
        error_code=getattr(exc, "auth_code", None),
    )
    return response
