"""
Batch processing for external API calls.

Reduces API calls by batching requests and caching results.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BatchProcessor:
    """
    Batch processor for API calls.
    
    Collects requests and processes them in batches to reduce API calls.
    """

    def __init__(
        self,
        batch_size: int = 10,
        max_wait_time: float = 1.0,
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Maximum batch size before processing
            max_wait_time: Maximum time to wait before processing (seconds)
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self._queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._processing = False

    async def add(
        self,
        key: str,
        processor: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Add request to batch queue.
        
        Args:
            key: Unique key for deduplication
            processor: Async function to process request
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Processing result
        """
        future = asyncio.Future()

        async with self._lock:
            # Check if request already in queue (deduplication)
            for item in self._queue:
                if item["key"] == key:
                    logger.debug(f"Request {key} already in queue, reusing")
                    return await item["future"]

            # Add to queue
            self._queue.append({
                "key": key,
                "processor": processor,
                "args": args,
                "kwargs": kwargs,
                "future": future,
            })

            # Start processing if batch is full
            if len(self._queue) >= self.batch_size:
                asyncio.create_task(self._process_batch())
            elif not self._processing:
                # Schedule processing after max_wait_time
                asyncio.create_task(self._schedule_processing())

        return await future

    async def _schedule_processing(self) -> None:
        """Schedule batch processing after max_wait_time"""
        self._processing = True
        await asyncio.sleep(self.max_wait_time)
        await self._process_batch()

    async def _process_batch(self) -> None:
        """Process current batch"""
        async with self._lock:
            if not self._queue:
                self._processing = False
                return

            batch = self._queue[:]
            self._queue.clear()
            self._processing = False

        logger.info(f"Processing batch of {len(batch)} requests")

        # Process all requests concurrently
        tasks = []
        for item in batch:
            task = asyncio.create_task(
                self._process_item(item)
            )
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_item(self, item: Dict[str, Any]) -> None:
        """Process single item from batch"""
        try:
            result = await item["processor"](*item["args"], **item["kwargs"])
            item["future"].set_result(result)
        except Exception as e:
            logger.error(f"Error processing batch item {item['key']}: {e}")
            item["future"].set_exception(e)


# Global batch processor instance
batch_processor = BatchProcessor(batch_size=10, max_wait_time=1.0)
