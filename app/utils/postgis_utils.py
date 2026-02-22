"""
PostGIS utilities for geospatial queries.

Provides functions for:
- Distance calculations using Haversine formula
- Geospatial queries with PostGIS (if available)
- Fallback to SQLAlchemy for SQLite/standard PostgreSQL
"""

import math
from typing import List, Optional, Tuple
from sqlalchemy import select, func, column
from sqlalchemy.sql import Select

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points using Haversine formula.

    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point

    Returns:
        Distance in kilometers
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def create_bbox(
    latitude: float, longitude: float, radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Create a bounding box around a point for initial filtering.

    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Radius in kilometers

    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Approximate degrees per km (varies by latitude)
    lat_per_km = 1 / 111.32
    lon_per_km = 1 / (111.32 * math.cos(math.radians(latitude)))

    min_lat = latitude - radius_km * lat_per_km
    max_lat = latitude + radius_km * lat_per_km
    min_lon = longitude - radius_km * lon_per_km
    max_lon = longitude + radius_km * lon_per_km

    return (min_lat, max_lat, min_lon, max_lon)


def filter_by_location(
    query: Select,
    latitude: float,
    longitude: float,
    radius_km: float,
    use_postgis: bool = False,
) -> Select:
    """
    Filter stations by location.

    Args:
        query: SQLAlchemy query object
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Search radius in kilometers
        use_postgis: Whether to use PostGIS (default: False)

    Returns:
        Filtered query
    """
    if use_postgis:
        # PostGIS query with ST_DistanceSphere
        query = query.filter(
            func.ST_DistanceSphere(
                func.ST_MakePoint(column("longitude"), column("latitude")),
                func.ST_MakePoint(longitude, latitude),
            )
            <= radius_km * 1000  # Convert km to meters
        )
    else:
        # Fallback: Bounding box + Haversine in Python
        min_lat, max_lat, min_lon, max_lon = create_bbox(latitude, longitude, radius_km)

        query = query.filter(
            column("latitude") >= min_lat,
            column("latitude") <= max_lat,
            column("longitude") >= min_lon,
            column("longitude") <= max_lon,
        )

    return query


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, use_postgis: bool = False
) -> float:
    """
    Calculate distance between two points.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        use_postgis: Whether to use database calculation

    Returns:
        Distance in kilometers
    """
    return haversine_distance(lat1, lon1, lat2, lon2)


def get_nearby_stations_query(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    limit: int = 100,
    use_postgis: bool = False,
) -> Select:
    """
    Build query for nearby stations.

    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Search radius
        limit: Maximum results
        use_postgis: Whether to use PostGIS

    Returns:
        SQLAlchemy select query
    """
    from app.models.station import Station

    query = select(Station)
    query = filter_by_location(query, latitude, longitude, radius_km, use_postgis)
    query = query.limit(limit)

    return query
