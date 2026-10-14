
from django.contrib.auth.hashers import check_password, make_password
from django.utils.crypto import constant_time_compare
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.users.repository import UserRepository
from core.exceptions.auth import AuthFailed
from core.utils.jwt_blacklist import blacklist_access_token
from core.utils.tokens import issue_tokens, rotate_tokens


_INVALID_CREDENTIALS = "Invalid email or password."
_INVALID_REFRESH_TOKEN = "Refresh token is invalid or expired."

_dummy_password_hash = make_password(None)


def _password_matches(user: User | None, password: str) -> bool:
    if user is not None and user.has_usable_password():
        return user.check_password(password)

    check_password(password, _dummy_password_hash)
    return False


def _parse_refresh(raw_refresh: str) -> RefreshToken:
    try:
        return RefreshToken(raw_refresh)
    except TokenError:
        raise AuthFailed(
            _INVALID_REFRESH_TOKEN,
            code="INVALID_REFRESH_TOKEN",
        ) from None


def _validate_refresh_owner(refresh: RefreshToken, user: User) -> None:
    token_user_id = refresh.get(api_settings.USER_ID_CLAIM)

    if not constant_time_compare(str(token_user_id), str(user.pk)):
        raise AuthFailed(
            _INVALID_REFRESH_TOKEN,
            code="INVALID_REFRESH_TOKEN",
        )


class AuthService:
    @staticmethod
    def login(*, validated_data: dict) -> tuple[dict, User]:
        user = UserRepository.get_by_email(validated_data["email"])
        password = validated_data["password"]

        if not _password_matches(user, password):
            raise AuthFailed(
                _INVALID_CREDENTIALS,
                code="INVALID_CREDENTIALS",
            )

        if not user.is_active:
            raise AuthFailed(
                "Account is disabled.",
                code="ACCOUNT_DISABLED",
            )

        UserRepository.update_last_login(user)

        return issue_tokens(user), user

    @staticmethod
    def refresh(*, validated_data: dict) -> dict:
        refresh = _parse_refresh(validated_data["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)

        user = UserRepository.get_active_by_id(user_id)

        if user is None:
            raise AuthFailed(
                "Account is disabled.",
                code="ACCOUNT_DISABLED",
            )

        _validate_refresh_owner(refresh, user)

        return rotate_tokens(refresh, user)

    @staticmethod
    def logout(
        *,
        user: User,
        access_token: str,
        validated_data: dict,
    ) -> None:
        raw_refresh = validated_data.get("refresh")

        if raw_refresh:
            refresh = _parse_refresh(raw_refresh)
            _validate_refresh_owner(refresh, user)
            refresh.blacklist()

        blacklist_access_token(access_token)
