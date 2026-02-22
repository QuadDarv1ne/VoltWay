import logging
import re
import time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.api.exceptions import StationNotFoundError, InvalidFilterError, DatabaseError
from app.database import get_async_db
from app.utils import geo
from app.utils.cache.manager import cache
from app.utils.logging import log_performance, log_cache_operation

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

        # Build query
        query = select(models.station.Station)

        # Фильтр по типу разъема с санитизацией для предотвращения SQL injection
        if connector_type:
            # Экранирование специальных символов LIKE: %, _, \
            sanitized_connector = re.sub(r"([%_\\])", r"\\\1", connector_type)
            query = query.where(
                models.station.Station.connector_type.ilike(f"%{sanitized_connector}%")
            )

        # Фильтр по мощности
        if min_power_kw:
            query = query.where(models.station.Station.power_kw >= min_power_kw)

        # Проверяем, есть ли геофильтр
        if latitude is not None and longitude is not None and radius_km is not None:
            # Для геофильтра используем async версию функции
            stations = await geo.get_geospatial_filter_async(
                db,
                latitude,
                longitude,
                radius_km,
                connector_type,
                min_power_kw,
                skip,
                limit,
            )
            logger.info(f"Найдено {len(stations)} станций с геофильтрацией")
        else:
            # Без геофильтра используем обычный SQL запрос
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            stations = result.scalars().all()
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

        query = select(models.station.Station).where(
            models.station.Station.id == station_id
        )
        result = await db.execute(query)
        db_station = result.scalar_one_or_none()

        if db_station is None:
            logger.warning(f"Станция с ID {station_id} не найдена")
            raise StationNotFoundError(station_id)

        return db_station
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
            update_stations_from_api, latitude, longitude, radius, db
        )
        logger.info(
            f"Запущено обновление кэша для координат ({latitude}, {longitude}), "
            f"радиус {radius} км"
        )
        return {"message": "Cache update started in background"}
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления кэша: {e}")
        raise DatabaseError("update_cache", str(e))


async def update_stations_from_api(
    lat: float, lon: float, radius: int, db: AsyncSession
):
    """Фоновая задача для обновления станций из API"""
    from app.services.external_api import fetch_stations_from_open_charge_map

    try:
        logger.info(f"Starting cache update for lat={lat}, lon={lon}, radius={radius}")
        stations_data = await fetch_stations_from_open_charge_map(lat, lon, radius)

        if not stations_data:
            logger.warning(
                f"Нет данных для обновления кэша для координат ({lat}, {lon})"
            )
            return

        added_count = 0
        for data in stations_data:
            # Проверка существования станции
            query = select(models.station.Station).where(
                (models.station.Station.latitude == data["latitude"])
                & (models.station.Station.longitude == data["longitude"])
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if not existing:
                station = models.station.Station(**data)
                db.add(station)
                added_count += 1

        await db.commit()
        # Clear the station cache after updating
        cache.cache.clear_station_cache()
        logger.info(
            f"Cache updated with {added_count} new stations out of "
            f"{len(stations_data)} total"
        )
    except Exception as e:
        logger.error(f"Error updating cache: {e}")
        await db.rollback()
