"""
CRUD operations for API keys.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey, APIKeyRole


async def create_api_key(
    db: AsyncSession,
    name: str,
    role: APIKeyRole = APIKeyRole.USER,
    description: Optional[str] = None,
    rate_limit_requests: int = 100,
    rate_limit_period: int = 60,
    expires_in_days: Optional[int] = None,
) -> APIKey:
    """
    Create a new API key.
    
    Args:
        db: Database session
        name: Human-readable name for the key
        role: Role/permission level
        description: Optional description
        rate_limit_requests: Number of requests allowed
        rate_limit_period: Period in seconds
        expires_in_days: Optional expiration in days
        
    Returns:
        Created APIKey instance
    """
    # Generate secure random key
    key = secrets.token_urlsafe(48)
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    api_key = APIKey(
        key=key,
        name=name,
        description=description,
        role=role.value,
        rate_limit_requests=rate_limit_requests,
        rate_limit_period=rate_limit_period,
        expires_at=expires_at,
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return api_key


async def get_api_key_by_key(
    db: AsyncSession, key: str
) -> Optional[APIKey]:
    """
    Get API key by key string.
    
    Args:
        db: Database session
        key: API key string
        
    Returns:
        APIKey instance or None
    """
    result = await db.execute(
        select(APIKey).where(APIKey.key == key)
    )
    return result.scalar_one_or_none()


async def update_last_used(
    db: AsyncSession, api_key: APIKey
) -> None:
    """
    Update last_used_at timestamp.
    
    Args:
        db: Database session
        api_key: APIKey instance
    """
    api_key.last_used_at = datetime.utcnow()
    await db.commit()


async def deactivate_api_key(
    db: AsyncSession, api_key_id: int
) -> bool:
    """
    Deactivate an API key.
    
    Args:
        db: Database session
        api_key_id: API key ID
        
    Returns:
        True if deactivated, False if not found
    """
    result = await db.execute(
        select(APIKey).where(APIKey.id == api_key_id)
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        return False
    
    api_key.is_active = False
    await db.commit()
    return True


async def list_api_keys(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[APIKey]:
    """
    List all API keys.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records
        
    Returns:
        List of APIKey instances
    """
    result = await db.execute(
        select(APIKey).offset(skip).limit(limit)
    )
    return list(result.scalars().all())
