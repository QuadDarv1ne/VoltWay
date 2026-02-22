"""
Base repository pattern implementation.

Provides generic CRUD operations and can be extended for specific models.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        *,
        load_relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get a single record by ID with optional relationship loading.

        Args:
            db: Database session
            id: Record ID
            load_relationships: List of relationship names to eager load

        Returns:
            Model instance or None
        """
        query = select(self.model).where(self.model.id == id)

        # Add eager loading for relationships
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        load_relationships: Optional[List[str]] = None,
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and optional relationship loading.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records
            load_relationships: List of relationship names to eager load

        Returns:
            List of model instances
        """
        query = select(self.model).offset(skip).limit(limit)

        # Add eager loading for relationships
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: Dict[str, Any]
    ) -> ModelType:
        """Update an existing record"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """Delete a record by ID"""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def count(self, db: AsyncSession) -> int:
        """Count total records"""
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)
        result = await db.execute(query)
        return result.scalar() or 0
