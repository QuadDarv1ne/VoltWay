from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.station import Station
from app.schemas.station import StationCreate


def get_stations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Station).offset(skip).limit(limit).all()


def get_station(db: Session, station_id: int):
    return db.query(Station).filter(Station.id == station_id).first()


def create_station(db: Session, station: StationCreate):
    db_station = Station(**station.model_dump())
    db.add(db_station)
    db.commit()
    db.refresh(db_station)
    return db_station


# Async CRUD operations for use with async endpoints

import re


async def get_stations_async(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    connector_type: Optional[str] = None,
    min_power_kw: Optional[float] = None,
) -> List[Station]:
    """Get stations with optional filters (async version)"""
    query = select(Station)

    if connector_type:
        # Sanitize input to prevent SQL injection in LIKE clause
        # Escape special LIKE characters: %, _, \
        sanitized_connector = re.sub(r"([%_\\])", r"\\\1", connector_type)
        # Use parameterized query with escape character
        query = query.where(Station.connector_type.ilike(f"%{sanitized_connector}%"))

    if min_power_kw:
        query = query.where(Station.power_kw >= min_power_kw)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_station_async(db: AsyncSession, station_id: int) -> Optional[Station]:
    """Get station by ID (async version)"""
    query = select(Station).where(Station.id == station_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_stations_by_location_async(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_km: float,
    skip: int = 0,
    limit: int = 100,
) -> List[Station]:
    """Get stations within a radius (async version with bounding box optimization)"""
    # Bounding box for early filtering
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / 111.0  # Simplified, will be refined in geo utils

    lat_min = latitude - lat_delta
    lat_max = latitude + lat_delta
    lon_min = longitude - lon_delta
    lon_max = longitude + lon_delta

    query = select(Station).where(
        Station.latitude.between(lat_min, lat_max),
        Station.longitude.between(lon_min, lon_max),
    )

    result = await db.execute(query)
    stations = result.scalars().all()

    # Apply haversine filter in Python for accuracy
    from app.utils.geo import haversine_distance

    filtered = [
        s
        for s in stations
        if haversine_distance(latitude, longitude, s.latitude, s.longitude) <= radius_km
    ]

    return filtered[skip : skip + limit]


async def create_station_async(db: AsyncSession, station: StationCreate) -> Station:
    """Create a new station (async version)"""
    db_station = Station(**station.model_dump())
    db.add(db_station)
    await db.commit()
    await db.refresh(db_station)
    return db_station


async def get_station_count_async(db: AsyncSession) -> int:
    """Get total number of stations (async version)"""
    query = select(func.count()).select_from(Station)
    result = await db.execute(query)
    return result.scalar()
