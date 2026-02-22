"""
Admin endpoints for monitoring and management.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import verify_api_key
from app.services.circuit_breaker import (
    api_ninjas_breaker,
    open_charge_map_breaker,
)
from app.utils.cache.manager import cache

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/circuit-breakers", dependencies=[Depends(verify_api_key)])
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """
    Get status of all circuit breakers.
    
    Requires API key authentication.
    """
    return {
        "circuit_breakers": [
            open_charge_map_breaker.get_stats(),
            api_ninjas_breaker.get_stats(),
        ]
    }


@router.post("/circuit-breakers/{name}/reset", dependencies=[Depends(verify_api_key)])
async def reset_circuit_breaker(name: str) -> Dict[str, str]:
    """
    Manually reset a circuit breaker.
    
    Args:
        name: Circuit breaker name (OpenChargeMap or APINinjas)
        
    Requires API key authentication.
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


@router.get("/cache/stats", dependencies=[Depends(verify_api_key)])
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Requires API key authentication.
    """
    return cache.stats()


@router.post("/cache/clear", dependencies=[Depends(verify_api_key)])
async def clear_cache() -> Dict[str, str]:
    """
    Clear all cache entries.
    
    Use with caution! This will clear all cached data.
    
    Requires API key authentication.
    """
    cache.clear()
    return {"message": "Cache cleared successfully"}


@router.post("/cache/clear-stations", dependencies=[Depends(verify_api_key)])
async def clear_station_cache() -> Dict[str, Any]:
    """
    Clear only station-related cache entries.
    
    Requires API key authentication.
    """
    count = cache.clear_station_cache()
    return {
        "message": "Station cache cleared successfully",
        "entries_cleared": count,
    }
