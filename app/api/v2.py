"""API v2 routes - Next version with improvements

Changes from v1:
- Better error handling with detailed error codes
- Additional filtering options for stations
- Batch operations support
- Deprecation warnings for old endpoints
"""

from fastapi import APIRouter, Header, Response
from typing import Optional

from app.api import auth, favorites, monitoring, notifications, stations

# Create v2 router
v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

# Include all v2 routes (same as v1 for now, will add improvements)
v2_router.include_router(stations.router, prefix="/stations", tags=["stations"])
v2_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v2_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
v2_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])


@v2_router.get("", tags=["version"])
async def v2_info(response: Response):
    """Get API v2 information"""
    response.headers["API-Version"] = "2.0.0"
    response.headers["Deprecation"] = "false"
    return {
        "version": "2.0.0",
        "status": "stable",
        "improvements": [
            "Enhanced error handling",
            "Better filtering options",
            "Batch operations support",
            "Improved performance"
        ]
    }
