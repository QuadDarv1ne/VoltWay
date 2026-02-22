"""
Redis cache client wrapper.

Provides Redis-specific caching operations with fallback handling.
"""

import logging
import pickle
from typing import Any, Dict, List, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis cache client with error handling and fallback support.

    Features:
    - Automatic reconnection
    - Pickle serialization
    - Error handling with graceful degradation
    """

    def __init__(self, redis_url: str):
        """
        Initialize Redis client.

        Args:
            redis_url: Redis connection URL
        """
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = redis.from_url(self._redis_url)
            self._client.ping()
            self._connected = True
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            self._client = None

    def is_connected(self) -> bool:
        """
        Check if Redis is connected.

        Returns:
            True if connected
        """
        if not self._connected or self._client is None:
            return False

        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis.

        Args:
            key: Cache key

        Returns:
            Deserialized value or None
        """
        if not self.is_connected():
            return None

        try:
            value = self._client.get(key)  # type: ignore
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self._connected = False
            return None

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Set value in Redis.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds

        Returns:
            True if successful
        """
        if not self.is_connected():
            return False

        try:
            serialized = pickle.dumps(value)
            result = self._client.setex(key, expire, serialized)  # type: ignore
            return bool(result)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self._connected = False
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from Redis.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self.is_connected():
            return False

        try:
            result = self._client.delete(key)  # type: ignore
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "stations:*")

        Returns:
            List of matching keys
        """
        if not self.is_connected():
            return []

        try:
            result = self._client.keys(pattern)  # type: ignore
            return [k.decode() if isinstance(k, bytes) else k for k in result]
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []

    def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys.

        Args:
            keys: List of keys to delete

        Returns:
            Number of keys deleted
        """
        if not self.is_connected():
            return 0

        try:
            if keys:
                return self._client.delete(*keys)  # type: ignore
            return 0
        except Exception as e:
            logger.error(f"Redis delete_many error: {e}")
            return 0

    def clear(self) -> None:
        """Clear all Redis keys (use with caution!)."""
        if not self.is_connected():
            return

        try:
            self._client.flushdb()  # type: ignore
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics.

        Returns:
            Dictionary with Redis stats
        """
        if not self.is_connected():
            return {"connected": False}

        try:
            info = self._client.info("memory")  # type: ignore
            return {
                "connected": True,
                "memory_used": info.get("used_memory_human", "unknown"),
                "memory_peak": info.get("used_memory_peak_human", "unknown"),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"connected": False, "error": str(e)}
