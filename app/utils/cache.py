import json
import logging
import pickle
from typing import Any, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting value from cache: {e}")
            return None

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration time in seconds"""
        if not self.redis_client:
            return False

        try:
            serialized_value = pickle.dumps(value)
            result = self.redis_client.setex(key, expire, serialized_value)
            return result
        except Exception as e:
            logger.error(f"Error setting value to cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False

        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting value from cache: {e}")
            return False

    def get_station_cache_key(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        connector_type: Optional[str],
        min_power_kw: float,
        skip: int,
        limit: int,
    ) -> str:
        """Generate cache key for station search"""
        params = {
            "lat": latitude,
            "lon": longitude,
            "radius": radius_km,
            "connector": connector_type,
            "min_power": min_power_kw,
            "skip": skip,
            "limit": limit,
        }
        # Create a hashable representation of the parameters
        key_parts = [f"{k}:{v}" for k, v in params.items() if v is not None]
        return f"stations:{':'.join(key_parts)}"

    def clear_station_cache(self):
        """Clear all station-related cache entries"""
        if not self.redis_client:
            return 0

        try:
            # Find and delete all keys that start with "stations:"
            keys = self.redis_client.keys("stations:*")
            if keys:
                result = self.redis_client.delete(*keys)
                logger.info(f"Cleared {result} station cache entries")
                return result
            return 0
        except Exception as e:
            logger.error(f"Error clearing station cache: {e}")
            return 0


# Global cache instance
cache = CacheManager()
