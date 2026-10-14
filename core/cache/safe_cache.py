import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger("studio")


class SafeCache:

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        try:
            return cache.get(key, default)
        except Exception:
            logger.warning("cache_get_failed key=%s", key, exc_info=True)
            return default

    @staticmethod
    def set(key: str, value: Any, timeout: int | None = None) -> bool:
        try:
            cache.set(key, value, timeout=timeout)
            return True
        except Exception:
            logger.warning("cache_set_failed key=%s", key, exc_info=True)
            return False

    @staticmethod
    def delete(key: str) -> bool:
        try:
            cache.delete(key)
            return True
        except Exception:
            logger.warning("cache_delete_failed key=%s", key, exc_info=True)
            return False
