"""
LRU Cache implementation for in-memory caching.

Used as a fallback when Redis is unavailable.
"""

import logging
from collections import OrderedDict
from threading import Lock
from time import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Thread-safe in-memory LRU (Least Recently Used) cache.

    Features:
    - Automatic expiration of entries
    - Thread-safe operations
    - O(1) get and set operations
    - Configurable maximum size
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries in cache
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]

            # Check if expired
            if expiry is not None and time() > expiry:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Set value in cache with expiration.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (0 for no expiration)

        Returns:
            True if successful
        """
        with self._lock:
            # If key exists, move to end
            if key in self._cache:
                self._cache.move_to_end(key)

            expiry: Optional[float] = time() + expire if expire > 0 else None
            self._cache[key] = (value, expiry)

            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

            return True

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching pattern (simple prefix matching).

        Args:
            pattern: Pattern to match (supports * wildcard at end)

        Returns:
            List of matching keys
        """
        with self._lock:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k for k in self._cache.keys() if k.startswith(prefix)]
            return [k for k in self._cache.keys() if k == pattern]

    def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys.

        Args:
            keys: List of keys to delete

        Returns:
            Number of keys deleted
        """
        with self._lock:
            count = 0
            for key in keys:
                if key in self._cache:
                    del self._cache[key]
                    count += 1
            return count

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
            }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = time()
            expired_keys = [
                key
                for key, (_, expiry) in self._cache.items()
                if expiry is not None and current_time > expiry
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)
