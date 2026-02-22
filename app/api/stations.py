import logging
import time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api.exceptions import StationNotFoundError, InvalidFilterError, DatabaseError
from app.database import get_async_db
from app.repositories.station import station_repository
from app.services.station import station_service
from app.utils.cache.manager import cache
from app.utils.logging import log_performance

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[schemas.Station])
async def read_stations(
    request: Request,
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, le=1000, ge=1, description="Максимальное количество возвращаемых записей"
    ),
    latitude: Optional[float] = Query(
        None, ge=-90, le=90, description="Широта центра поиска"
    ),
    longitude: Optional[float] = Query(
        None, ge=-180, le=180, description="Долгота центра поиска"
    ),
    radius_km: Optional[float] = Query(
        None, gt=0, le=100, description="Радиус поиска в км"
    ),
    connector_type: Optional[str] = Query(None, description="Тип разъема"),
    min_power_kw: Optional[float] = Query(
        None, gt=0, description="Минимальная мощность"
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """Получить список станций с фильтрацией и пагинацией"""
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
            logger.info(f"Найдено {len(stations)} станций с геофильтрацией")
        else:
            # Simple filter query using repository
            stations = await station_repository.get_by_filters(
                db=db,
                connector_type=connector_type,
                min_power_kw=min_power_kw,
                skip=skip,
                limit=limit,
            )
            logger.info(f"Найдено {len(stations)} станций")

        # Cache the result for 10 minutes
        start_time = time.time()
        cache_success = cache.cache.set(cache_key, stations, expire=600)
        cache_duration = (time.time() - start_time) * 1000
        log_performance(
            start_time,
            "cache_set",
            cache_key=cache_key,
            success=cache_success,
            duration_ms=cache_duration,
        )

        return stations
    except InvalidFilterError:
        raise
    except Exception as e:
        logger.error(
            f"Ошибка при получении станций: {e}",
            extra={
                "error_type": type(e).__name__,
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km,
            },
        )
        raise DatabaseError("get_stations", str(e))


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
