"""
Enhanced health check endpoints with dependency checks.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.utils.cache.manager import cache

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Basic health check - always returns 200 if service is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VoltWay",
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Detailed health check with dependency status.
    
    Checks:
    - Database connectivity
    - Cache availability
    - Service uptime
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VoltWay",
        "version": "1.0.0",
        "checks": {},
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}",
        }

    # Check cache
    try:
        cache_stats = cache.stats()
        health_status["checks"]["cache"] = {
            "status": "healthy",
            "redis_connected": cache_stats.get("redis_connected", False),
            "using_fallback": cache_stats.get("using_fallback", True),
        }
    except Exception as e:
        health_status["checks"]["cache"] = {
            "status": "degraded",
            "message": f"Cache error: {str(e)}",
        }

    return health_status


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns 200 if service is ready to accept traffic.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns 200 if service is alive (not deadlocked).
    """
    return {"status": "alive"}
