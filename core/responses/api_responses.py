from rest_framework import status
from rest_framework.response import Response
from core.exceptions.messages import get_error_message

class ResponseInfo:

    def __init__(self):
        self.response = {
            "status": False,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "",
            "data": {},
            "errors": {},
        }

    @staticmethod
    def body(*, ok=True, code=200, message="", data=None, errors=None, error_code=None):
        payload = {
            "status"        : ok,
            "status_code"   : code,
            "message"       : message,
            "data"          : {} if data is None else data,
            "errors"        : {} if errors is None else errors,
        }
        if error_code:
            payload["code"] = error_code
        return payload

    @classmethod
    def _reply(cls, *, ok, code, message="", data=None, errors=None, error_code=None):
        return Response(
            cls.body(
                ok=ok,
                code=code,
                message=message,
                data=data,
                errors=errors,
                error_code=error_code,
            ),
            status=code,
        )


    @classmethod
    def ok(cls, data=None, message="Success"):
        return cls._reply(
            ok=True, code=status.HTTP_200_OK, message=message, data=data
            )
    

    @classmethod
    def created(cls, data=None, message="Created successfully"):
        return cls._reply(
            ok=True, code=status.HTTP_201_CREATED, message=message, data=data
        )


    @classmethod
    def accepted(cls, data=None, message="Accepted"):
        return cls._reply(
            ok=True, code=status.HTTP_202_ACCEPTED, message=message, data=data
        )


    @classmethod
    def no_content(cls, message="Deleted successfully"):
        return cls._reply(
            ok=True, code=status.HTTP_204_NO_CONTENT, message=message
            )
    

    @classmethod
    def bad_request(cls, message="Bad request", errors=None, error_code=None, data=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_400_BAD_REQUEST,
            message   = message,
            errors    = errors,
            error_code= error_code,
            data      = data,
        )

    @classmethod
    def validation_error(
        cls,
        errors,
        message="Validation failed",
        error_code=None,
        data=None,
    ):
        

        payload = errors if isinstance(errors, dict) else {"detail": errors}
        return cls.bad_request(
            message=get_error_message(payload) or message or "Validation failed",
            errors=payload,
            error_code=error_code or "VALIDATION_ERROR",
            data=data,
        )


    @classmethod
    def unauthorized(cls, message="Authentication required", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_401_UNAUTHORIZED,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )

    @classmethod
    def forbidden(cls, message="You do not have permission", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_403_FORBIDDEN,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )

    @classmethod
    def not_found(cls, message="Not found", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_404_NOT_FOUND,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )

    @classmethod
    def method_not_allowed(cls, message="Method not allowed", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_405_METHOD_NOT_ALLOWED,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )


    @classmethod
    def conflict(cls, message="Conflict", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_409_CONFLICT,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )

    @classmethod
    def unprocessable(cls, message="Validation failed", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_422_UNPROCESSABLE_ENTITY,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )


    @classmethod
    def too_many_requests(cls, message="Too many requests", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_429_TOO_MANY_REQUESTS,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )

    @classmethod
    def server_error(cls, message="Something went wrong", errors=None, error_code=None):
        return cls._reply(
            ok        = False,
            code      = status.HTTP_500_INTERNAL_SERVER_ERROR,
            message   = message,
            errors    = errors,
            error_code= error_code,
        )
