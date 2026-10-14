from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


def issue_tokens(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {
        "token_type": "Bearer",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def rotate_tokens(refresh: RefreshToken, user: User) -> dict[str, str]:
    if not api_settings.ROTATE_REFRESH_TOKENS:
        return {
            "token_type": "Bearer",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    if api_settings.BLACKLIST_AFTER_ROTATION:
        refresh.blacklist()
    return issue_tokens(user)
