"""Batch database operations for bulk inserts/updates"""

import logging
from typing import List, TypeVar, Generic, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


class BatchOperations(Generic[T]):
    """Batch database operations handler"""

    def __init__(self, session: AsyncSession, batch_size: int = 1000):
        self.session = session
        self.batch_size = batch_size
        self.insert_buffer: List[dict] = []
        self.update_buffer: List[tuple] = []

    async def add_insert(self, model_class: type[T], data: dict) -> None:
        """Add item to insert buffer"""
        self.insert_buffer.append(data)

        if len(self.insert_buffer) >= self.batch_size:
            await self.flush_inserts(model_class)

    async def flush_inserts(self, model_class: type[T]) -> int:
        """Execute buffered inserts"""
        if not self.insert_buffer:
            return 0

        try:
            await self.session.execute(
                insert(model_class).values(self.insert_buffer)
            )
            await self.session.commit()

            inserted = len(self.insert_buffer)
            logger.info(f"Bulk inserted {inserted} {model_class.__name__} records")

            self.insert_buffer.clear()
            return inserted

        except Exception as e:
            logger.error(f"Batch insert error: {e}")
            await self.session.rollback()
            raise

    async def bulk_insert(self, model_class: type[T], data_list: List[dict]) -> int:
        """Bulk insert with automatic batching"""
        total_inserted = 0

        for i in range(0, len(data_list), self.batch_size):
            batch = data_list[i : i + self.batch_size]

            try:
                await self.session.execute(insert(model_class).values(batch))
                await self.session.commit()
                total_inserted += len(batch)
                logger.debug(f"Inserted batch of {len(batch)} records")

            except Exception as e:
                logger.error(f"Batch insert error: {e}")
                await self.session.rollback()
                raise

        logger.info(f"Bulk inserted total {total_inserted} {model_class.__name__} records")
        return total_inserted

    async def bulk_update(
        self, model_class: type[T], values_list: List[dict], filter_key: str
    ) -> int:
        """Bulk update records

        Args:
            model_class: SQLAlchemy model class
            values_list: List of dicts with values to update
            filter_key: The key to filter by (usually 'id')
        """
        updated = 0

        for values in values_list:
            filter_val = values.pop(filter_key)

            try:
                result = await self.session.execute(
                    update(model_class)
                    .where(getattr(model_class, filter_key) == filter_val)
                    .values(**values)
                )
                updated += result.rowcount

            except Exception as e:
                logger.error(f"Batch update error: {e}")
                await self.session.rollback()
                raise

        if updated > 0:
            await self.session.commit()
            logger.info(f"Bulk updated {updated} {model_class.__name__} records")

        return updated

    async def close(self, model_class: Optional[type[T]] = None) -> int:
        """Close and flush any remaining data"""
        if model_class and self.insert_buffer:
            return await self.flush_inserts(model_class)
        return 0


async def batch_process(
    items: List[Any],
    process_func,
    batch_size: int = 100,
) -> int:
    """Process items in batches

    Args:
        items: List of items to process
        process_func: Async function that processes a batch
        batch_size: Size of each batch
    """
    total_processed = 0

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        try:
            processed = await process_func(batch)
            total_processed += processed
            logger.debug(f"Processed batch of {len(batch)} items")

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            raise

    logger.info(f"Total processed {total_processed} items")
    return total_processed
