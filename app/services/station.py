"""
Station service layer for business logic.

This module contains the business logic for station operations,
separating API concerns from core functionality.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.station import Station
from app.repositories.station import station_repository
from app.services.external_api import fetch_stations_from_open_charge_map
from app.utils.cache.manager import cache

logger = logging.getLogger(__name__)


class StationService:
    """Service for station business logic"""

    def __init__(self):
        self.repository = station_repository

    async def update_stations_from_api(
        self,
        lat: float,
        lon: float,
        radius: int,
    ) -> Dict[str, int]:
        """
        Update station data from external API.

        Uses bulk upsert for better performance.

        Args:
            lat: Latitude center
            lon: Longitude center
            radius: Search radius in km

        Returns:
            Dict with statistics: added, updated, total
        """
        async with AsyncSessionLocal() as db:
            try:
                logger.info(
                    f"Starting cache update for lat={lat}, lon={lon}, radius={radius}"
                )
                stations_data = await fetch_stations_from_open_charge_map(
                    lat, lon, radius
                )

                if not stations_data:
                    logger.warning(
                        f"Нет данных для обновления кэша для координат ({lat}, {lon})"
                    )
                    return {"added": 0, "updated": 0, "total": 0}

                # Use bulk upsert for better performance
                result = await self.repository.upsert_stations(
                    db=db,
                    stations_data=stations_data,
                    batch_size=20,
                )

                # Clear the station cache after updating
                cache.cache.clear_station_cache()

                logger.info(
                    f"Cache updated: {result['added']} added, "
                    f"{result['updated']} updated, {result['total']} total"
                )

                return result

            except Exception as e:
                logger.error(f"Error updating cache: {e}", exc_info=True)
                await db.rollback()
                return {"added": 0, "updated": 0, "total": 0, "error": str(e)}

    async def get_station_with_details(
        self, db: AsyncSession, station_id: int
    ) -> Optional[Station]:
        """
        Get station with related details.

        Uses selectinload to avoid N+1 queries.
        """
        from sqlalchemy.orm import selectinload

        query = (
            select(Station)
            .options(selectinload(Station.favorited_by))
            .where(Station.id == station_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_stations_count(self, db: AsyncSession) -> int:
        """Get total stations count"""
        return await self.repository.count(db)

    async def get_available_stations(
        self,
        db: AsyncSession,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> List[Station]:
        """Get only available stations"""
        if latitude and longitude and radius_km:
            return await self.repository.get_by_location(
                db=db,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                status="available",
            )
        else:
            return await self.repository.get_by_filters(
                db=db,
                status="available",
            )


# Global instance
station_service = StationService()
