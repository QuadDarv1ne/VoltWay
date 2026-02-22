"""
Station repository with specialized queries.

Supports both standard SQL and PostGIS for geospatial queries.
"""

import re
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.station import Station
from app.repositories.base import BaseRepository
from app.utils.geo import haversine_distance
from app.utils.postgis_utils import create_bbox


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
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Station]:
        """
        Get stations within radius with optional filters.

        Uses PostGIS if enabled and available, otherwise falls back to
        bounding box + Haversine calculation.
        """
        if settings.use_postgis:
            return await self._get_by_location_postgis(
                db, latitude, longitude, radius_km,
                connector_type=connector_type,
                min_power_kw=min_power_kw,
                status=status,
                skip=skip,
                limit=limit,
            )
        else:
            return await self._get_by_location_haversine(
                db, latitude, longitude, radius_km,
                connector_type=connector_type,
                min_power_kw=min_power_kw,
                status=status,
                skip=skip,
                limit=limit,
            )

    async def _get_by_location_postgis(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float,
        *,
        connector_type: Optional[str] = None,
        min_power_kw: Optional[float] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Station]:
        """Get stations using PostGIS geospatial functions"""
        from sqlalchemy import func, text

        # PostGIS query with ST_DistanceSphere
        query = select(
            Station,
            (func.ST_DistanceSphere(
                func.ST_MakePoint(Station.longitude, Station.latitude),
                func.ST_MakePoint(longitude, latitude),
            ) / 1000).label("distance_km")
        ).where(
            func.ST_DistanceSphere(
                func.ST_MakePoint(Station.longitude, Station.latitude),
                func.ST_MakePoint(longitude, latitude),
            ) <= radius_km * 1000  # Convert to meters
        )

        # Apply filters
        if connector_type:
            sanitized = re.sub(r"([%_\\])", r"\\\1", connector_type)
            query = query.where(Station.connector_type.ilike(f"%{sanitized}%"))

        if min_power_kw:
            query = query.where(Station.power_kw >= min_power_kw)

        if status:
            query = query.where(Station.status == status)

        # Order by distance
        query = query.order_by(text("distance_km ASC"))
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        rows = result.all()
        return [row[0] for row in rows]  # Return only Station objects

    async def _get_by_location_haversine(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float,
        *,
        connector_type: Optional[str] = None,
        min_power_kw: Optional[float] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Station]:
        """Get stations using bounding box + Haversine calculation"""
        # Bounding box optimization
        min_lat, max_lat, min_lon, max_lon = create_bbox(
            latitude, longitude, radius_km
        )

        query = select(Station).where(
            Station.latitude.between(min_lat, max_lat),
            Station.longitude.between(min_lon, max_lon),
        )

        # Apply filters
        if connector_type:
            sanitized = re.sub(r"([%_\\])", r"\\\1", connector_type)
            query = query.where(Station.connector_type.ilike(f"%{sanitized}%"))

        if min_power_kw:
            query = query.where(Station.power_kw >= min_power_kw)

        if status:
            query = query.where(Station.status == status)

        result = await db.execute(query)
        stations = list(result.scalars().all())

        # Precise distance filtering using Haversine
        filtered = [
            s
            for s in stations
            if haversine_distance(latitude, longitude, s.latitude, s.longitude)
            <= radius_km
        ]

        # Sort by distance and apply pagination
        filtered.sort(
            key=lambda s: haversine_distance(
                latitude, longitude, s.latitude, s.longitude
            )
        )
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

    async def upsert_stations(
        self,
        db: AsyncSession,
        stations_data: List[dict],
        batch_size: int = 20,
    ) -> dict:
        """
        Bulk upsert stations using PostgreSQL ON CONFLICT.

        Args:
            db: Database session
            stations_data: List of station data dictionaries
            batch_size: Number of records per batch

        Returns:
            Dict with added, updated, total counts
        """
        from sqlalchemy.dialects.postgresql import insert
        from datetime import datetime

        added_count = 0
        updated_count = 0

        # Process in batches
        for i in range(0, len(stations_data), batch_size):
            batch = stations_data[i : i + batch_size]

            # Prepare data for bulk insert
            insert_values = []
            for data in batch:
                # Ensure last_updated is set
                if "last_updated" not in data:
                    data["last_updated"] = datetime.utcnow()
                insert_values.append(data)

            if not insert_values:
                continue

            # Build insert statement with upsert on conflict
            stmt = insert(Station).values(insert_values)

            # On conflict (latitude, longitude), update all fields except id
            stmt = stmt.on_conflict_do_update(
                index_elements=[Station.latitude, Station.longitude],
                set_={
                    "title": stmt.excluded.title,
                    "address": stmt.excluded.address,
                    "connector_type": stmt.excluded.connector_type,
                    "power_kw": stmt.excluded.power_kw,
                    "status": stmt.excluded.status,
                    "price": stmt.excluded.price,
                    "hours": stmt.excluded.hours,
                    "last_updated": stmt.excluded.last_updated,
                },
            )

            # Execute and track results
            result = await db.execute(stmt)

            # Count added vs updated (PostgreSQL returns this info)
            added_count += result.rowcount

        await db.commit()

        return {
            "added": added_count,
            "updated": updated_count,
            "total": len(stations_data),
        }


# Global instance
station_repository = StationRepository()
