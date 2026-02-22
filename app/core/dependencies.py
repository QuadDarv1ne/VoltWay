"""
Dependency injection for FastAPI endpoints.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.repositories.station import StationRepository, station_repository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency with proper cleanup"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_station_repository() -> StationRepository:
    """Get station repository instance"""
    return station_repository


def get_request_id(request: Request) -> str:
    """Get request ID from request state"""
    return getattr(request.state, "request_id", "unknown")


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="API key for authentication"),
    db: AsyncSession = Depends(get_db),
) -> "APIKey":
    """
    Verify API key for protected endpoints.
    
    Args:
        x_api_key: API key from header
        db: Database session
        
    Returns:
        APIKey instance if valid
        
    Raises:
        HTTPException: If key is missing, invalid, or expired
    """
    from app.crud.api_key import get_api_key_by_key, update_last_used
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    api_key = await get_api_key_by_key(db, x_api_key)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not api_key.is_valid():
        detail = "API key expired" if api_key.is_expired() else "API key inactive"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Update last used timestamp (fire and forget)
    await update_last_used(db, api_key)
    
    return api_key


async def require_admin(
    api_key: "APIKey" = Depends(verify_api_key),
) -> "APIKey":
    """
    Require admin role for endpoint access.
    
    Args:
        api_key: Verified API key
        
    Returns:
        APIKey instance if admin
        
    Raises:
        HTTPException: If not admin
    """
    from app.models.api_key import APIKeyRole
    
    if api_key.role != APIKeyRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return api_key


def get_pagination_params(
    skip: int = 0, limit: int = 100
) -> tuple[int, int]:
    """
    Get and validate pagination parameters.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        Tuple of (skip, limit)
        
    Raises:
        HTTPException: If parameters are invalid
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative",
        )
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000",
        )
    return skip, limit
