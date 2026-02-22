"""
CRUD operations for API keys.

Security features:
- API keys are hashed with bcrypt before storage
- Key prefix stored for identification
- Secure random key generation
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey, APIKeyRole
from app.utils.auth import hash_api_key, generate_api_key, get_api_key_prefix


async def create_api_key(
    db: AsyncSession,
    name: str,
    role: APIKeyRole = APIKeyRole.USER,
    description: Optional[str] = None,
    rate_limit_requests: int = 100,
    rate_limit_period: int = 60,
    expires_in_days: Optional[int] = None,
) -> tuple[APIKey, str]:
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
        Tuple of (APIKey instance, plain text key)
        IMPORTANT: Plain text key is only returned once!
    """
    # Generate secure random key
    plain_key = generate_api_key()

    # Hash the key for storage
    key_hash = hash_api_key(plain_key)

    # Get prefix for identification
    key_prefix = get_api_key_prefix(plain_key)

    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
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

    return (api_key, plain_key)


async def get_api_key_by_key(
    db: AsyncSession, key: str
) -> Optional[APIKey]:
    """
    Get API key by key string.

    Note: This requires iterating through all keys and verifying hashes,
    which is inefficient. For production, consider using a lookup table
    with key prefix as index.

    Args:
        db: Database session
        key: API key string

    Returns:
        APIKey instance or None
    """
    from app.utils.auth import verify_api_key

    # Get all active keys
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    all_keys = result.scalars().all()

    # Verify against each key
    for api_key in all_keys:
        if verify_api_key(key, api_key.key_hash):
            return api_key

    return None


async def get_api_key_by_id(
    db: AsyncSession, api_key_id: int
) -> Optional[APIKey]:
    """
    Get API key by ID.

    Args:
        db: Database session
        api_key_id: API key ID

    Returns:
        APIKey instance or None
    """
    result = await db.execute(
        select(APIKey).where(APIKey.id == api_key_id)
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
    api_key = await get_api_key_by_id(db, api_key_id)

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


async def delete_api_key(
    db: AsyncSession, api_key_id: int
) -> bool:
    """
    Permanently delete an API key.

    Args:
        db: Database session
        api_key_id: API key ID

    Returns:
        True if deleted, False if not found
    """
    api_key = await get_api_key_by_id(db, api_key_id)

    if not api_key:
        return False

    await db.delete(api_key)
    await db.commit()
    return True
