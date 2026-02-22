"""
Cache manager with Redis and in-memory fallback.

Provides unified cache interface with automatic failover.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.utils.cache.lru import LRUCache
from app.utils.cache.redis_client import RedisClient
from app.utils.logging import log_cache_operation

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Unified cache manager with Redis primary and LRU fallback.

    Features:
    - Automatic failover to in-memory cache
    - Dual-write strategy for reliability
    - Cache statistics and monitoring
    - Station-specific cache operations
    """

    def __init__(self, max_memory_cache_size: int = 1000):
        """
        Initialize cache manager.

        Args:
            max_memory_cache_size: Maximum size of in-memory cache
        """
        self._memory_cache = LRUCache(max_size=max_memory_cache_size)
        self._redis_client: Optional[RedisClient] = None
        self._use_memory_fallback = False

        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis client."""
        try:
            self._redis_client = RedisClient(settings.redis_url)
            if not self._redis_client.is_connected():
                logger.warning("Redis unavailable, using in-memory cache")
                self._use_memory_fallback = True
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
            self._use_memory_fallback = True
            self._redis_client = None

    def _get_redis(self) -> Optional[RedisClient]:
        """Get Redis client if available and connected."""
        if self._redis_client and not self._use_memory_fallback:
            if self._redis_client.is_connected():
                return self._redis_client
            else:
                logger.warning("Redis connection lost, falling back to memory")
                self._use_memory_fallback = True
        return None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        redis = self._get_redis()

        if redis:
            try:
                value = redis.get(key)
                if value is not None:
                    log_cache_operation("get", key, success=True, client="redis")
                    return value
                # Also check memory cache as backup
                value = self._memory_cache.get(key)
                if value is not None:
                    log_cache_operation("get", key, success=True, client="memory")
                    return value
                log_cache_operation("get", key, success=True, hit=False, client="redis")
                return None
            except Exception as e:
                logger.error(f"Cache get error: {e}")
                self._use_memory_fallback = True
                return self._memory_cache.get(key)
        else:
            result = self._memory_cache.get(key)
            log_cache_operation("get", key, success=result is not None, client="memory")
            return result

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds

        Returns:
            True if successful
        """
        # Always write to memory cache as backup
        self._memory_cache.set(key, value, expire)

        # Try Redis if available
        redis = self._get_redis()
        if redis:
            try:
                result = redis.set(key, value, expire)
                log_cache_operation("set", key, success=result, client="redis")
                return result
            except Exception as e:
                logger.error(f"Cache set error: {e}")
                self._use_memory_fallback = True

        log_cache_operation("set", key, success=True, client="memory")
        return True

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        # Delete from memory
        self._memory_cache.delete(key)

        # Delete from Redis if available
        redis = self._get_redis()
        if redis:
            try:
                result = redis.delete(key)
                log_cache_operation("delete", key, success=result, client="redis")
                return result
            except Exception as e:
                logger.error(f"Cache delete error: {e}")

        log_cache_operation("delete", key, success=True, client="memory")
        return True

    def clear(self) -> None:
        """Clear all cache entries."""
        self._memory_cache.clear()

        redis = self._get_redis()
        if redis:
            try:
                redis.clear()
            except Exception as e:
                logger.error(f"Cache clear error: {e}")

    def get_station_cache_key(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        radius_km: Optional[float],
        connector_type: Optional[str],
        min_power_kw: Optional[float],
        skip: int,
        limit: int,
    ) -> str:
        """
        Generate cache key for station search.

        Args:
            latitude: Search latitude
            longitude: Search longitude
            radius_km: Search radius in km
            connector_type: Connector type filter
            min_power_kw: Minimum power filter
            skip: Pagination skip
            limit: Pagination limit

        Returns:
            Cache key string
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "radius": radius_km,
            "connector": connector_type,
            "min_power": min_power_kw,
            "skip": skip,
            "limit": limit,
        }
        key_parts = [f"{k}:{v}" for k, v in params.items() if v is not None]
        return f"stations:{':'.join(key_parts)}"

    def clear_station_cache(self) -> int:
        """
        Clear all station-related cache entries.

        Returns:
            Number of entries cleared
        """
        count = 0

        # Clear from memory
        memory_keys = self._memory_cache.keys("stations:*")
        if memory_keys:
            count += self._memory_cache.delete_many(memory_keys)

        # Clear from Redis
        redis = self._get_redis()
        if redis:
            try:
                redis_keys = redis.keys("stations:*")
                if redis_keys:
                    count += redis.delete_many(redis_keys)
            except Exception as e:
                logger.error(f"Error clearing Redis station cache: {e}")
                self._use_memory_fallback = True

        logger.info(f"Cleared {count} station cache entries")
        return count

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats: Dict[str, Any] = {
            "memory_cache": self._memory_cache.stats(),
            "redis_connected": self._redis_client is not None
            and not self._use_memory_fallback,
            "using_fallback": self._use_memory_fallback,
        }

        if self._redis_client and not self._use_memory_fallback:
            redis_stats = self._redis_client.stats()
            stats.update({"redis": redis_stats})

        return stats

    def cleanup(self) -> int:
        """
        Cleanup expired entries.

        Returns:
            Number of entries cleaned up
        """
        return self._memory_cache.cleanup_expired()


# Global cache instance
cache = CacheManager()
