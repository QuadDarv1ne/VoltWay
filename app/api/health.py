"""
Enhanced health check endpoints with dependency checks.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any

import psutil
from fastapi import APIRouter, Depends, status
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.models.station import Station
from app.models.reservation import Reservation
from app.utils.cache.manager import cache

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Basic health check - always returns 200 if service is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VoltWay",
        "version": settings.app_version,
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
    - System metrics
    - Business metrics
    """
    from app.utils.metrics import update_system_metrics, cpu_usage, memory_usage
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VoltWay",
        "version": settings.app_version,
        "checks": {},
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        
        # Get station count
        station_count_query = select(func.count()).select_from(Station)
        station_count_result = await db.execute(station_count_query)
        station_count = station_count_result.scalar() or 0
        
        # Get active reservations
        active_query = select(func.count()).where(Reservation.status == "active")
        active_result = await db.execute(active_query.select())
        active_reservations = active_result.scalar() or 0
        
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
            "stations_count": station_count,
            "active_reservations": active_reservations,
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
            "status": "healthy" if cache_stats.get("redis_connected") else "degraded",
            "redis_connected": cache_stats.get("redis_connected", False),
            "using_fallback": cache_stats.get("using_fallback", True),
        }
    except Exception as e:
        health_status["checks"]["cache"] = {
            "status": "degraded",
            "message": f"Cache error: {str(e)}",
        }

    # System metrics
    try:
        update_system_metrics()
        health_status["checks"]["system"] = {
            "status": "healthy",
            "cpu_percent": cpu_usage.value,
            "memory_percent": memory_usage.labels(type="percent").value,
        }
    except Exception as e:
        health_status["checks"]["system"] = {
            "status": "degraded",
            "message": f"System metrics error: {str(e)}",
        }

    # External APIs
    health_status["checks"]["external_apis"] = {
        "status": "info",
        "open_charge_map_configured": bool(settings.open_charge_map_api_key),
        "api_ninjas_configured": bool(settings.api_ninjas_key),
    }

    # Environment
    health_status["checks"]["environment"] = {
        "debug_mode": settings.debug,
        "use_postgis": settings.use_postgis,
        "otel_enabled": os.getenv("ENABLE_OTEL", "false").lower() == "true",
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


@router.get("/health/metrics", status_code=status.HTTP_200_OK)
async def health_metrics(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Health metrics for monitoring dashboards.
    
    Returns detailed metrics without status checks.
    """
    # Station statistics
    station_stats_query = select(
        Station.status,
        func.count().label('count'),
        func.avg(Station.power_kw).label('avg_power'),
    ).group_by(Station.status)
    station_stats_result = await db.execute(station_stats_query)
    station_stats = [
        {
            "status": row.status,
            "count": row.count,
            "avg_power_kw": float(row.avg_power) if row.avg_power else 0,
        }
        for row in station_stats_result.all()
    ]
    
    # Reservation statistics
    reservation_stats_query = select(
        Reservation.status,
        func.count().label('count'),
    ).group_by(Reservation.status)
    reservation_stats_result = await db.execute(reservation_stats_query)
    reservation_stats = {
        row.status: row.count
        for row in reservation_stats_result.all()
    }
    
    # Review statistics
    from sqlalchemy import and_
    from app.models.review import Review
    
    review_stats_query = select(
        func.count().label('total'),
        func.avg(Review.rating).label('avg_rating'),
    ).where(
        and_(Review.is_approved == 1, Review.is_hidden == 0)
    )
    review_stats_result = await db.execute(review_stats_query)
    review_stats = review_stats_result.fetchone()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "stations": {
            "by_status": station_stats,
        },
        "reservations": {
            "by_status": reservation_stats,
        },
        "reviews": {
            "total": review_stats.total if review_stats else 0,
            "average_rating": float(review_stats.avg_rating) if review_stats and review_stats.avg_rating else 0,
        },
    }
