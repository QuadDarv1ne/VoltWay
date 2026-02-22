"""
Cache module for VoltWay.

Provides unified caching with Redis and in-memory fallback.

Usage:
    from app.utils.cache import cache

    # Get/Set values
    cache.set("key", "value", expire=3600)
    value = cache.get("key")

    # Station-specific operations
    cache_key = cache.get_station_cache_key(lat, lon, radius, ...)
    cache.set(cache_key, stations)
    cache.clear_station_cache()

    # Statistics
    stats = cache.stats()
"""

from app.utils.cache.manager import CacheManager, cache
from app.utils.cache.lru import LRUCache
from app.utils.cache.redis_client import RedisClient

__all__ = [
    "cache",
    "CacheManager",
    "LRUCache",
    "RedisClient",
]
