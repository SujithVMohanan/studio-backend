from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from core.utils.jwt_blacklist import is_access_token_blacklisted


class JWTAccessBlacklistAuthentication(JWTAuthentication):

    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        if is_access_token_blacklisted(validated_token):
            raise InvalidToken(_("Token has been expired by logout."))
        return validated_token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user is None or not user.is_active:
            raise InvalidToken(_("User is inactive or deleted."))
        return user
