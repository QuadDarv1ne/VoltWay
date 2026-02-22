"""
Admin endpoints for monitoring and management.
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_db, get_pagination_params
from app.crud import api_key as api_key_crud
from app.models.api_key import APIKey, APIKeyRole
from app.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyInfo, APIKeyStats
from app.services.circuit_breaker import (
    api_ninjas_breaker,
    open_charge_map_breaker,
)
from app.utils.cache.manager import cache

router = APIRouter(prefix="/admin", tags=["admin"])


# Circuit Breaker Management
@router.get("/circuit-breakers", dependencies=[Depends(require_admin)])
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """
    Get status of all circuit breakers.
    
    Requires admin API key.
    """
    return {
        "circuit_breakers": [
            open_charge_map_breaker.get_stats(),
            api_ninjas_breaker.get_stats(),
        ]
    }


@router.post("/circuit-breakers/{name}/reset", dependencies=[Depends(require_admin)])
async def reset_circuit_breaker(name: str) -> Dict[str, str]:
    """
    Manually reset a circuit breaker.
    
    Args:
        name: Circuit breaker name (OpenChargeMap or APINinjas)
        
    Requires admin API key.
    """
    breakers = {
        "OpenChargeMap": open_charge_map_breaker,
        "APINinjas": api_ninjas_breaker,
    }

    breaker = breakers.get(name)
    if not breaker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{name}' not found",
        )

    breaker.reset()
    return {"message": f"Circuit breaker '{name}' reset successfully"}


# Cache Management
@router.get("/cache/stats", dependencies=[Depends(require_admin)])
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Requires admin API key.
    """
    return cache.stats()


@router.post("/cache/clear", dependencies=[Depends(require_admin)])
async def clear_cache() -> Dict[str, str]:
    """
    Clear all cache entries.
    
    Use with caution! This will clear all cached data.
    
    Requires admin API key.
    """
    cache.clear()
    return {"message": "Cache cleared successfully"}


@router.post("/cache/clear-stations", dependencies=[Depends(require_admin)])
async def clear_station_cache() -> Dict[str, Any]:
    """
    Clear only station-related cache entries.
    
    Requires admin API key.
    """
    count = cache.clear_station_cache()
    return {
        "message": "Station cache cleared successfully",
        "entries_cleared": count,
    }


# API Key Management
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: APIKey = Depends(require_admin),
) -> APIKey:
    """
    Create a new API key.
    
    Requires admin API key.
    
    Returns the key only once - save it securely!
    """
    api_key = await api_key_crud.create_api_key(
        db=db,
        name=key_data.name,
        role=key_data.role,
        description=key_data.description,
        rate_limit_requests=key_data.rate_limit_requests,
        rate_limit_period=key_data.rate_limit_period,
        expires_in_days=key_data.expires_in_days,
    )
    return api_key


@router.get("/api-keys", response_model=List[APIKeyInfo])
async def list_api_keys(
    pagination: tuple[int, int] = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: APIKey = Depends(require_admin),
) -> List[APIKey]:
    """
    List all API keys (without the actual key values).
    
    Requires admin API key.
    """
    skip, limit = pagination
    return await api_key_crud.list_api_keys(db, skip=skip, limit=limit)


@router.delete("/api-keys/{key_id}")
async def deactivate_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    _: APIKey = Depends(require_admin),
) -> Dict[str, str]:
    """
    Deactivate an API key.
    
    Requires admin API key.
    """
    success = await api_key_crud.deactivate_api_key(db, key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with ID {key_id} not found",
        )
    
    return {"message": f"API key {key_id} deactivated successfully"}


@router.get("/api-keys/stats", response_model=APIKeyStats)
async def get_api_key_stats(
    db: AsyncSession = Depends(get_db),
    _: APIKey = Depends(require_admin),
) -> APIKeyStats:
    """
    Get API key statistics.
    
    Requires admin API key.
    """
    keys = await api_key_crud.list_api_keys(db, skip=0, limit=10000)
    
    total = len(keys)
    active = sum(1 for k in keys if k.is_active)
    expired = sum(1 for k in keys if k.is_expired())
    
    by_role = {}
    for role in APIKeyRole:
        by_role[role.value] = sum(1 for k in keys if k.role == role.value)
    
    return APIKeyStats(
        total_keys=total,
        active_keys=active,
        expired_keys=expired,
        by_role=by_role,
    )
