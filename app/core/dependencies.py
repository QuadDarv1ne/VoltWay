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
    x_api_key: Optional[str] = Header(None, description="API key for authentication")
) -> Optional[str]:
    """
    Verify API key for protected endpoints.
    
    Returns None if no key required, raises HTTPException if invalid.
    """
    # TODO: Implement actual API key verification
    # For now, just return the key if provided
    return x_api_key


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
