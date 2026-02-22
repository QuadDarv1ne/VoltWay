import logging
import time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api.exceptions import StationNotFoundError, InvalidFilterError, DatabaseError
from app.database import get_async_db
from app.repositories.station import station_repository
from app.schemas.pagination import PaginatedResponse, PaginationInfo
from app.services.station import station_service
from app.utils.cache.manager import cache
from app.utils.logging import log_performance

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[schemas.Station],
    summary="Get stations with pagination",
)
async def read_stations(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        20, le=100, ge=1, description="Maximum number of items to return"
    ),
    latitude: Optional[float] = Query(
        None, ge=-90, le=90, description="Latitude center"
    ),
    longitude: Optional[float] = Query(
        None, ge=-180, le=180, description="Longitude center"
    ),
    radius_km: Optional[float] = Query(
        None, gt=0, le=100, description="Search radius in km"
    ),
    connector_type: Optional[str] = Query(None, description="Connector type filter"),
    min_power_kw: Optional[float] = Query(
        None, gt=0, description="Minimum power in kW"
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get list of stations with filtering and pagination.

    - **skip**: Number of items to skip (for pagination)
    - **limit**: Maximum number of items to return (1-100)
    - **latitude**: Latitude coordinate for location search
    - **longitude**: Longitude coordinate for location search
    - **radius_km**: Search radius in kilometers
    - **connector_type**: Filter by connector type (CCS, CHAdeMO, Type 2)
    - **min_power_kw**: Filter by minimum power in kW

    Returns paginated list of stations with metadata.
    """
    try:
        # Validate filter parameters
        if connector_type and len(connector_type) > 50:
            raise InvalidFilterError(
                "connector_type filter is too long", {"connector_type": connector_type}
            )

        # Generate cache key
        cache_key = cache.cache.get_station_cache_key(
            latitude, longitude, radius_km, connector_type, min_power_kw, skip, limit
        )

        # Try to get from cache first
        start_time = time.time()
        cached_result = cache.cache.get(cache_key)
        cache_duration = (time.time() - start_time) * 1000

        if cached_result is not None:
            logger.info(f"Cache hit for key: {cache_key}")
            log_performance(
                start_time,
                "cache_get",
                cache_key=cache_key,
                hit=True,
                duration_ms=cache_duration,
            )
            return cached_result
        else:
            log_performance(
                start_time,
                "cache_get",
                cache_key=cache_key,
                hit=False,
                duration_ms=cache_duration,
            )

        # Get total count for pagination metadata
        total_count = await station_repository.count_by_filters(
            db=db,
            connector_type=connector_type,
            min_power_kw=min_power_kw,
        )

        # Use repository for database queries
        if latitude is not None and longitude is not None and radius_km is not None:
            # Geospatial query using repository
            stations = await station_repository.get_by_location(
                db=db,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                connector_type=connector_type,
                min_power_kw=min_power_kw,
                skip=skip,
                limit=limit,
            )
            # For geospatial queries, use filtered count
            total_count = len(stations)
            logger.info(f"Found {len(stations)} stations with geofilter")
        else:
            # Simple filter query using repository
            stations = await station_repository.get_by_filters(
                db=db,
                connector_type=connector_type,
                min_power_kw=min_power_kw,
                skip=skip,
                limit=limit,
            )
            logger.info(f"Found {len(stations)} stations")

        # Create pagination metadata
        pagination = PaginationInfo.create(
            skip=skip,
            limit=limit,
            total=total_count,
        )

        # Build paginated response
        response = PaginatedResponse(
            items=stations,
            pagination=pagination,
        )

        # Cache the result for 10 minutes
        start_time = time.time()
        cache_success = cache.cache.set(cache_key, response.model_dump(), expire=600)
        cache_duration = (time.time() - start_time) * 1000
        log_performance(
            start_time,
            "cache_set",
            cache_key=cache_key,
            success=cache_success,
            duration_ms=cache_duration,
        )

        return response
    except InvalidFilterError:
        raise
    except Exception as e:
        logger.error(
            f"Error getting stations: {e}",
            extra={
                "error_type": type(e).__name__,
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km,
            },
        )
        raise DatabaseError("get_stations", str(e))


@router.get("/search", response_model=PaginatedResponse[schemas.Station])
async def search_stations(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    latitude: Optional[float] = Query(
        None, ge=-90, le=90, description="Latitude center"
    ),
    longitude: Optional[float] = Query(
        None, ge=-180, le=180, description="Longitude center"
    ),
    radius_km: Optional[float] = Query(
        None, gt=0, le=100, description="Search radius in km"
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        50, le=100, ge=1, description="Maximum number of items to return"
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Full-text search for stations.

    - **q**: Search query (minimum 2 characters)
    - **latitude**: Optional latitude for location filter
    - **longitude**: Optional longitude for location filter
    - **radius_km**: Optional radius for location filter in km

    Returns stations matching the search query with relevance ranking.
    """
    try:
        # Track search metrics
        from app.utils.metrics import station_searches_total
        has_location = latitude is not None and longitude is not None
        station_searches_total.labels(
            search_type="fulltext",
            has_location=str(has_location).lower(),
            has_filters="true" if radius_km else "false",
        ).inc()

        # Perform full-text search
        stations = await station_repository.search_full_text(
            db=db,
            search_query=q,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            skip=skip,
            limit=limit,
        )

        # Get total count for pagination
        total_count = len(stations)

        # Create pagination metadata
        pagination = PaginationInfo.create(
            skip=skip,
            limit=limit,
            total=total_count,
        )

        return PaginatedResponse(
            items=stations,
            pagination=pagination,
        )

    except Exception as e:
        logger.error(f"Error in full-text search: {e}")
        raise DatabaseError("search_stations", str(e))


@router.get("/suggestions", response_model=List[str])
async def get_search_suggestions(
    prefix: str = Query(..., min_length=1, max_length=50, description="Search prefix"),
    limit: int = Query(10, le=20, ge=1, description="Maximum suggestions"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get search suggestions for autocomplete.

    - **prefix**: Search prefix for autocomplete
    - **limit**: Maximum number of suggestions (1-20)

    Returns list of station titles starting with the prefix.
    """
    try:
        suggestions = await station_repository.get_search_suggestions(
            db=db,
            prefix=prefix,
            limit=limit,
        )
        return suggestions

    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        return []


@router.get("/{station_id}", response_model=schemas.Station)
async def read_station(
    request: Request, station_id: int, db: AsyncSession = Depends(get_async_db)
):
    """Получить информацию о конкретной станции"""
    try:
        # Проверка корректности ID
        if station_id <= 0:
            raise InvalidFilterError(
                "station_id must be positive", {"station_id": station_id}
            )

        # Use repository for single station retrieval
        station = await station_repository.get(db, station_id)

        if station is None:
            logger.warning(f"Станция с ID {station_id} не найдена")
            raise StationNotFoundError(station_id)

        return station
    except (StationNotFoundError, InvalidFilterError):
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении станции {station_id}: {e}")
        raise DatabaseError("get_station", str(e))


@router.post("/update_cache")
async def update_cache(
    request: Request,
    background_tasks: BackgroundTasks,
    latitude: float = Query(55.7558, ge=-90, le=90, description="Широта центра"),
    longitude: float = Query(37.6173, ge=-180, le=180, description="Долгота центра"),
    radius: int = Query(50, ge=1, le=100, description="Радиус в км"),
    db: AsyncSession = Depends(get_async_db),
):
    """Обновление кэша данными из внешних API"""
    try:
        background_tasks.add_task(
            station_service.update_stations_from_api,
            latitude,
            longitude,
            radius,
        )
        logger.info(
            f"Запущено обновление кэша для координат ({latitude}, {longitude}), "
            f"радиус {radius} км"
        )
        return {"message": "Cache update started in background"}
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления кэша: {e}")
        raise DatabaseError("update_cache", str(e))
