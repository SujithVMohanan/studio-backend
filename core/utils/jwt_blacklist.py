from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import (
    AccessToken,
    RefreshToken,
)

from core.cache import SafeCache

ACCESS_BLACKLIST_PREFIX = "jwt:blacklist:access:"


def _access_cache_key(jti: str) -> str:
    return f"{ACCESS_BLACKLIST_PREFIX}{jti}"


def blacklist_access_token(raw_token: str) -> None:
    token = AccessToken(raw_token)
    jti = token["jti"]
    ttl = max(int(token["exp"]) - int(timezone.now().timestamp()), 1)
    SafeCache.set(_access_cache_key(jti), 1, timeout=ttl)


def is_access_token_blacklisted(validated_token) -> bool:
    jti = validated_token.get("jti")
    if not jti:
        return False
    return SafeCache.get(_access_cache_key(jti)) is not None


def blacklist_refresh_token(raw_refresh: str) -> None:
    RefreshToken(raw_refresh).blacklist()


def logout_tokens(*, refresh_token: str | None = None, access_token: str | None = None) -> None:
    if not refresh_token and not access_token:
        raise TokenError("Refresh or access token is required.")

    if refresh_token:
        try:
            blacklist_refresh_token(refresh_token)
        except TokenError as exc:
            raise TokenError("Refresh token is invalid or already expired.") from exc

    if not access_token:
        return
    try:
        blacklist_access_token(access_token)
    except TokenError:
        pass
