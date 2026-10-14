from typing import Any

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import Token

from core.utils.jwt_blacklist import is_access_token_blacklisted


class JWTAccessBlacklistAuthentication(JWTAuthentication):

    def get_validated_token(self, raw_token: bytes) -> Token:
        validated_token = super().get_validated_token(raw_token)
        if is_access_token_blacklisted(validated_token):
            raise InvalidToken("Token has been expired by logout.")
        return validated_token

    def get_user(self, validated_token: Token) -> Any:
        user = super().get_user(validated_token)
        if user is None or not user.is_active:
            raise InvalidToken("User is inactive or deleted.")
        return user
