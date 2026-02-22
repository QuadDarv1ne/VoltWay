"""API v1 routes - Current stable version"""

from fastapi import APIRouter

from app.api import auth, favorites, monitoring, notifications, stations

# Create v1 router
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

# Include all v1 routes
v1_router.include_router(stations.router, prefix="/stations", tags=["stations"])
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
v1_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
v1_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
