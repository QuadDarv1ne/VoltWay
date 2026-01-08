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
    Optimized with early filtering and reduced computation.
    """
    # Pre-calculate constants for better performance
    lat_rad = math.radians(lat)
    cos_lat = math.cos(lat_rad)
    
    # More precise delta calculations
    lat_delta = radius_km / 111.0  # 1 degree of latitude is ~111 km
    lon_delta = radius_km / (111.0 * abs(cos_lat))  # longitude varies with latitude

    lat_min = lat - lat_delta
    lat_max = lat + lat_delta
    lon_min = lon - lon_delta
    lon_max = lon + lon_delta

    # Filter by bounding box first (early filtering)
    bbox_filter = db.query(Station).filter(
        Station.latitude.between(lat_min, lat_max),
        Station.longitude.between(lon_min, lon_max),
    )

    # Pre-calculate values used in haversine calculation
    lat1_rad = math.radians(lat)
    lon1_rad = math.radians(lon)
    
    # Early rejection using simpler distance approximation for initial filtering
    # This reduces the number of expensive haversine calculations
    filtered_stations = []
    radius_km_squared = radius_km * radius_km
    
    for station in bbox_filter:
        # Quick square distance check (much faster than haversine)
        lat_diff = station.latitude - lat
        lon_diff = station.longitude - lon
        approx_distance_sq = lat_diff * lat_diff + lon_diff * lon_diff * cos_lat * cos_lat
        
        # If approximate distance squared is greater than radius squared, skip haversine
        if approx_distance_sq > radius_km_squared * 0.0001:  # Rough approximation factor
            continue
            
        # For borderline cases, use accurate haversine calculation
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
