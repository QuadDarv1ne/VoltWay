"""
Memory optimization utilities for improved performance and reduced memory footprint.

This module provides tools for:
- Lazy loading of large datasets
- Memory pooling for frequently used objects
- Streaming support for bulk operations
- Object recycling and efficient memory management
"""

import asyncio
import gc
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, TypeVar
from functools import wraps
import psutil
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MemoryPool:
    """
    Object pool for reusing frequently-created objects.
    Reduces garbage collection overhead and memory fragmentation.
    """

    def __init__(self, factory: Callable[[], T], max_size: int = 100):
        """
        Initialize memory pool.

        Args:
            factory: Callable that creates new objects
            max_size: Maximum pool size before reusing
        """
        self.factory = factory
        self.max_size = max_size
        self.pool: List[T] = []
        self.lock = asyncio.Lock()

    async def acquire(self) -> T:
        """Acquire object from pool or create new one."""
        async with self.lock:
            if self.pool:
                return self.pool.pop()
            return self.factory()

    async def release(self, obj: T) -> None:
        """Release object back to pool."""
        async with self.lock:
            if len(self.pool) < self.max_size:
                self.pool.append(obj)
            else:
                del obj

    async def clear(self) -> None:
        """Clear all objects in pool."""
        async with self.lock:
            self.pool.clear()
            gc.collect()


class LazyLoader:
    """
    Lazy loading wrapper for expensive computations.
    Delays evaluation until value is actually needed.
    """

    def __init__(self, loader: Callable[[], Any]):
        """
        Initialize lazy loader.

        Args:
            loader: Callable that loads the expensive resource
        """
        self.loader = loader
        self._value = None
        self._loaded = False

    @property
    def value(self) -> Any:
        """Get value, loading if necessary."""
        if not self._loaded:
            self._value = self.loader()
            self._loaded = True
        return self._value

    def reset(self) -> None:
        """Reset lazy loader."""
        self._value = None
        self._loaded = False


class StreamingProcessor:
    """
    Process large datasets in streaming fashion to reduce memory usage.
    """

    @staticmethod
    async def stream_process(
        items: List[T],
        chunk_size: int = 100,
        processor: Optional[Callable[[T], Any]] = None,
    ) -> AsyncGenerator[T, None]:
        """
        Stream process items in chunks.

        Args:
            items: List of items to process
            chunk_size: Size of chunks to process
            processor: Optional processor function

        Yields:
            Processed items one at a time
        """
        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            for item in chunk:
                if processor:
                    yield await processor(item) if asyncio.iscoroutinefunction(processor) else processor(item)
                else:
                    yield item
                await asyncio.sleep(0)  # Allow other tasks to run

    @staticmethod
    async def batch_stream(
        items: List[T],
        batch_size: int = 50,
    ) -> AsyncGenerator[List[T], None]:
        """
        Stream items in batches.

        Args:
            items: List of items
            batch_size: Batch size

        Yields:
            Batches of items
        """
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]
            await asyncio.sleep(0)  # Allow garbage collection


class MemoryMonitor:
    """Monitor and log memory usage."""

    def __init__(self, threshold_mb: int = 500):
        """
        Initialize memory monitor.

        Args:
            threshold_mb: Memory usage threshold in MB
        """
        self.threshold_mb = threshold_mb
        self.process = psutil.Process()

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        mem_info = self.process.memory_info()
        return {
            "rss_mb": mem_info.rss / 1024 / 1024,  # Resident set size
            "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual memory size
            "percent": self.process.memory_percent(),
        }

    def log_memory_usage(self) -> None:
        """Log current memory usage."""
        mem = self.get_memory_usage()
        logger.info(
            f"Memory usage - RSS: {mem['rss_mb']:.2f}MB, "
            f"VMS: {mem['vms_mb']:.2f}MB, Percent: {mem['percent']:.2f}%"
        )

        if mem["rss_mb"] > self.threshold_mb:
            logger.warning(
                f"High memory usage detected: {mem['rss_mb']:.2f}MB "
                f"(threshold: {self.threshold_mb}MB)"
            )
            gc.collect()  # Force garbage collection

    async def monitor_with_callback(
        self,
        callback: Callable[[], Any],
        check_interval: int = 60,
    ) -> None:
        """
        Monitor memory and call callback if threshold exceeded.

        Args:
            callback: Function to call on high memory
            check_interval: Check interval in seconds
        """
        try:
            while True:
                mem = self.get_memory_usage()
                if mem["rss_mb"] > self.threshold_mb:
                    await callback()
                await asyncio.sleep(check_interval)
        except asyncio.CancelledError:
            pass


def memory_efficient(chunk_size: int = 100):
    """
    Decorator for memory-efficient async operations.
    Automatically chunks large lists and allows garbage collection.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # If result is a list, yield in chunks
            if isinstance(result, list) and len(result) > chunk_size:
                async for item in StreamingProcessor.stream_process(
                    result, chunk_size
                ):
                    yield item
            else:
                return result

        return wrapper

    return decorator


def optimized_cache(max_size: int = 128):
    """
    Decorator for memory-optimized caching with LRU eviction.
    """

    def decorator(func: Callable) -> Callable:
        cache: Dict[str, Any] = {}
        cache_order: List[str] = []

        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = str((args, tuple(sorted(kwargs.items()))))

            if cache_key in cache:
                # Move to end (most recently used)
                cache_order.remove(cache_key)
                cache_order.append(cache_key)
                return cache[cache_key]

            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            cache[cache_key] = result
            cache_order.append(cache_key)

            # Evict oldest if over size
            if len(cache) > max_size:
                oldest_key = cache_order.pop(0)
                del cache[oldest_key]
                gc.collect()

            return result

        wrapper.clear_cache = lambda: (cache.clear(), cache_order.clear())
        return wrapper

    return decorator


class BulkInsertBuffer:
    """Buffer for efficient bulk inserts."""

    def __init__(self, db_session, model, batch_size: int = 1000):
        """
        Initialize bulk insert buffer.

        Args:
            db_session: Database session
            model: SQLAlchemy model class
            batch_size: Batch size for bulk inserts
        """
        self.db_session = db_session
        self.model = model
        self.batch_size = batch_size
        self.buffer: List[Any] = []

    async def add(self, item: Any) -> None:
        """Add item to buffer."""
        self.buffer.append(item)
        if len(self.buffer) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush buffer to database."""
        if self.buffer:
            self.db_session.add_all(self.buffer)
            await self.db_session.commit()
            self.buffer.clear()
            gc.collect()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.flush()


__all__ = [
    "MemoryPool",
    "LazyLoader",
    "StreamingProcessor",
    "MemoryMonitor",
    "BulkInsertBuffer",
    "memory_efficient",
    "optimized_cache",
]
