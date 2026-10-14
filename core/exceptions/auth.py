from typing import Any

from rest_framework.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)


class AuthFailed(AuthenticationFailed):
    def __init__(self, detail: str = "Authentication failed.", *, code: str = "AUTHENTICATION_FAILED") -> None:
        super().__init__(detail)
        self.auth_code = code


class AuthValidationError(ValidationError):
    def __init__(self, detail: Any, *, code: str = "VALIDATION_ERROR", message: str | None = None) -> None:
        super().__init__(detail)
        self.auth_code    = code
        self.auth_message = message or ""


class ProfileIncomplete(PermissionDenied):
    default_detail    = "Complete your profile to continue."
    default_code      = "profile_incomplete"
    auth_code         = "PROFILE_INCOMPLETE"
