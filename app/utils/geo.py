import math
from typing import List, Tuple

from sqlalchemy import func

from app.models.station import Station


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371

    return c * r


def get_geospatial_filter(db, lat: float, lon: float, radius_km: float):
    """
    Return a SQLAlchemy filter for geospatial search using the Haversine formula.
    This is compatible with SQLite and provides accurate distance filtering.
    """
    # For SQLite, we need to use a simpler approach since SQLite doesn't support advanced geospatial functions
    # We'll use the bounding box approach but with better calculations
    lat_delta = radius_km / 111.0  # 1 degree of latitude is ~111 km
    lon_delta = radius_km / (
        111.0 * abs(math.cos(math.radians(lat)))
    )  # longitude varies with latitude

    lat_min = lat - lat_delta
    lat_max = lat + lat_delta
    lon_min = lon - lon_delta
    lon_max = lon + lon_delta

    # Filter by bounding box first
    bbox_filter = db.query(Station).filter(
        Station.latitude.between(lat_min, lat_max),
        Station.longitude.between(lon_min, lon_max),
    )

    # Then calculate actual distance and filter by radius
    filtered_stations = []
    for station in bbox_filter:
        distance = haversine_distance(lat, lon, station.latitude, station.longitude)
        if distance <= radius_km:
            filtered_stations.append(station)

    return filtered_stations


def get_postgis_filter(db, lat: float, lon: float, radius_km: float):
    """
    Return a PostgreSQL/PostGIS filter for geospatial search.
    This is more efficient for larger datasets.
    """
    # This would be used if we were using PostgreSQL with PostGIS
    # For now, we'll use the SQLAlchemy function approach
    from sqlalchemy.dialects.postgresql import insert

    # Using ST_DistanceSphere for accurate distance calculation
    distance_filter = (
        func.ST_DistanceSphere(
            func.ST_MakePoint(Station.longitude, Station.latitude),
            func.ST_MakePoint(lon, lat),
        )
        <= radius_km * 1000
    )  # Convert km to meters

    return db.query(Station).filter(distance_filter)
