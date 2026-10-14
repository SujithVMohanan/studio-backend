from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


def issue_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "token_type": "Bearer",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def rotate_tokens(refresh: RefreshToken, user) -> dict:
    if not api_settings.ROTATE_REFRESH_TOKENS:
        return {
            "token_type": "Bearer",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    if api_settings.BLACKLIST_AFTER_ROTATION:
        refresh.blacklist()
    return issue_tokens(user)
