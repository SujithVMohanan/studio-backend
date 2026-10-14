"""Cache helpers that keep working when the cache backend is unavailable."""

from core.cache.safe_cache import SafeCache

__all__ = ["SafeCache"]
