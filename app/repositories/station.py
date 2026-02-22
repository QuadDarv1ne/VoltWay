"""
Station repository with specialized queries.
"""

import re
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import Station
from app.repositories.base import BaseRepository
from app.utils.geo import haversine_distance


class StationRepository(BaseRepository[Station]):
    """Repository for Station model with geospatial queries"""

    def __init__(self):
        super().__init__(Station)

    async def get_by_location(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float,
        *,
        connector_type: Optional[str] = None,
        min_power_kw: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Station]:
        """Get stations within radius with optional filters"""
        # Bounding box optimization
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * abs(latitude / 90.0 + 0.01))

        query = select(Station).where(
            Station.latitude.between(latitude - lat_delta, latitude + lat_delta),
            Station.longitude.between(longitude - lon_delta, longitude + lon_delta),
        )

        # Apply filters
        if connector_type:
            sanitized = re.sub(r"([%_\\])", r"\\\1", connector_type)
            query = query.where(Station.connector_type.ilike(f"%{sanitized}%"))

        if min_power_kw:
            query = query.where(Station.power_kw >= min_power_kw)

        result = await db.execute(query)
        stations = list(result.scalars().all())

        # Precise distance filtering
        filtered = [
            s
            for s in stations
            if haversine_distance(latitude, longitude, s.latitude, s.longitude)
            <= radius_km
        ]

        return filtered[skip : skip + limit]

    async def get_by_filters(
        self,
        db: AsyncSession,
        *,
        connector_type: Optional[str] = None,
        min_power_kw: Optional[float] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Station]:
        """Get stations with filters"""
        query = select(Station)

        if connector_type:
            sanitized = re.sub(r"([%_\\])", r"\\\1", connector_type)
            query = query.where(Station.connector_type.ilike(f"%{sanitized}%"))

        if min_power_kw:
            query = query.where(Station.power_kw >= min_power_kw)

        if status:
            query = query.where(Station.status == status)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def exists_at_location(
        self, db: AsyncSession, latitude: float, longitude: float
    ) -> bool:
        """Check if station exists at exact location"""
        query = select(Station).where(
            Station.latitude == latitude, Station.longitude == longitude
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None


# Global instance
station_repository = StationRepository()
