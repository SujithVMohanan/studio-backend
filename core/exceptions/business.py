from rest_framework import status
from rest_framework.exceptions import APIException, NotFound


class BusinessConflict(APIException):
    status_code    = status.HTTP_409_CONFLICT
    default_detail = "Request conflicts with the current state."

    def __init__(self, detail: str | None = None, *, code: str = "CONFLICT") -> None:
        super().__init__(detail)
        self.error_code = code


class ResourceNotFound(NotFound):
    def __init__(self, detail: str = "Not found.", *, code: str = "NOT_FOUND") -> None:
        super().__init__(detail)
        self.error_code = code
