from typing import cast

from rest_framework.request import Request

from apps.users.models import User


def authenticated_user(request: Request) -> User:
    """Only call from views guarded by IsAuthenticated."""
    return cast(User, request.user)
