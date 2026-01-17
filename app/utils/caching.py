"""Function-level caching decorators"""

import hashlib
import json
import time
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union
from datetime import datetime, timedelta

import redis

from app.core.config import settings
from app.utils.metrics import cache_hits, cache_misses

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Redis client
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Failed to connect to Redis: {e}")
    redis_client = None


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_data = {
        "args": str(args),
        "kwargs": str(kwargs),
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def redis_cache(
    ttl: int = 300,
    key_prefix: str = "cache",
) -> Callable:
    """Decorator for caching function results in Redis

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if not redis_client:
                return await func(*args, **kwargs)

            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            try:
                # Try to get from cache
                cached = redis_client.get(key)
                if cached is not None:
                    cache_hits.labels(cache_name=key_prefix).inc()
                    logger.debug(f"Cache hit for key: {key}")
                    return json.loads(cached)

                cache_misses.labels(cache_name=key_prefix).inc()

            except Exception as e:
                logger.warning(f"Cache retrieval error: {e}")

            # Call function and cache result
            result = await func(*args, **kwargs)

            try:
                redis_client.setex(key, ttl, json.dumps(result, default=str))
            except Exception as e:
                logger.warning(f"Cache storage error: {e}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if not redis_client:
                return func(*args, **kwargs)

            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            try:
                # Try to get from cache
                cached = redis_client.get(key)
                if cached is not None:
                    cache_hits.labels(cache_name=key_prefix).inc()
                    logger.debug(f"Cache hit for key: {key}")
                    return json.loads(cached)

                cache_misses.labels(cache_name=key_prefix).inc()

            except Exception as e:
                logger.warning(f"Cache retrieval error: {e}")

            # Call function and cache result
            result = func(*args, **kwargs)

            try:
                redis_client.setex(key, ttl, json.dumps(result, default=str))
            except Exception as e:
                logger.warning(f"Cache storage error: {e}")

            return result

        # Return appropriate wrapper
        if hasattr(func, "__wrapped__"):
            # If it's an async function
            return async_wrapper
        else:
            return sync_wrapper

        return async_wrapper

    return decorator


def memory_cache(ttl: int = 300) -> Callable:
    """Simple in-memory cache decorator using dictionary"""

    def decorator(func: Callable) -> Callable:
        cache_store = {}
        cache_times = {}

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            key = cache_key(*args, **kwargs)

            # Check if key exists and not expired
            if key in cache_store:
                if time.time() - cache_times[key] < ttl:
                    cache_hits.labels(cache_name="memory").inc()
                    logger.debug(f"Memory cache hit for key: {key}")
                    return cache_store[key]
                else:
                    # Expired, remove
                    del cache_store[key]
                    del cache_times[key]

            cache_misses.labels(cache_name="memory").inc()

            # Call function and cache result
            result = await func(*args, **kwargs)
            cache_store[key] = result
            cache_times[key] = time.time()

            # Cleanup old entries if too many
            if len(cache_store) > 1000:
                oldest_key = min(cache_times, key=cache_times.get)
                del cache_store[oldest_key]
                del cache_times[oldest_key]

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            key = cache_key(*args, **kwargs)

            # Check if key exists and not expired
            if key in cache_store:
                if time.time() - cache_times[key] < ttl:
                    cache_hits.labels(cache_name="memory").inc()
                    logger.debug(f"Memory cache hit for key: {key}")
                    return cache_store[key]
                else:
                    # Expired, remove
                    del cache_store[key]
                    del cache_times[key]

            cache_misses.labels(cache_name="memory").inc()

            # Call function and cache result
            result = func(*args, **kwargs)
            cache_store[key] = result
            cache_times[key] = time.time()

            # Cleanup old entries if too many
            if len(cache_store) > 1000:
                oldest_key = min(cache_times, key=cache_times.get)
                del cache_store[oldest_key]
                del cache_times[oldest_key]

            return result

        return async_wrapper

    return decorator


def clear_cache(pattern: str = "*") -> None:
    """Clear cache entries matching pattern"""
    if not redis_client:
        logger.warning("Redis client not available")
        return

    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
