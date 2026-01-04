from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app import crud, models, schemas
from app.database import get_db
from app.utils import geo, cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/stations", response_model=List[schemas.Station])
def read_stations(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(100, le=1000, ge=1, description="Максимальное количество возвращаемых записей"),
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Широта центра поиска"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Долгота центра поиска"),
    radius_km: Optional[float] = Query(None, gt=0, le=100, description="Радиус поиска в км"),
    connector_type: Optional[str] = Query(None, description="Тип разъема"),
    min_power_kw: Optional[float] = Query(None, gt=0, description="Минимальная мощность"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Station)

    # Фильтр по типу разъема
    if connector_type:
        query = query.filter(models.Station.connector_type.ilike(f"%{connector_type}%"))

    # Фильтр по мощности
    if min_power_kw:
        query = query.filter(models.Station.power_kw >= min_power_kw)

    try:
        # Generate cache key
        cache_key = cache.cache.get_station_cache_key(
            latitude, longitude, radius_km, connector_type, min_power_kw, skip, limit
        )
        
        # Try to get from cache first
        cached_result = cache.cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Cache hit for key: {cache_key}")
            return cached_result
        
        # Проверяем, есть ли геофильтр
        if latitude is not None and longitude is not None and radius_km is not None:
            # Для геофильтра используем специальную функцию, так как нужна точная фильтрация по расстоянию
            filtered_stations = geo.get_geospatial_filter(db, latitude, longitude, radius_km)
            
            # Применяем другие фильтры к отфильтрованным по геолокации станциям
            if connector_type:
                filtered_stations = [s for s in filtered_stations if connector_type.lower() in s.connector_type.lower()]
            if min_power_kw:
                filtered_stations = [s for s in filtered_stations if s.power_kw >= min_power_kw]
            
            # Применяем пагинацию
            start_idx = skip
            end_idx = skip + limit
            stations = filtered_stations[start_idx:end_idx]
            
            logger.info(f"Найдено {len(stations)} станций с геофильтрацией")
        else:
            # Без геофильтра используем обычный SQL запрос
            stations = query.offset(skip).limit(limit).all()
            logger.info(f"Найдено {len(stations)} станций")
        
        # Cache the result for 10 minutes
        cache.cache.set(cache_key, stations, expire=600)
        
        return stations
    except Exception as e:
        logger.error(f"Ошибка при получении станций: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при получении данных")

@router.get("/stations/{station_id}", response_model=schemas.Station)
def read_station(station_id: int, db: Session = Depends(get_db)):
    try:
        # Проверка корректности ID
        if station_id <= 0:
            raise HTTPException(status_code=400, detail="ID станции должен быть положительным числом")
        
        db_station = crud.get_station(db, station_id=station_id)
        if db_station is None:
            logger.warning(f"Станция с ID {station_id} не найдена")
            raise HTTPException(status_code=404, detail="Station not found")
        return db_station
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении станции {station_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/stations/update_cache")
async def update_cache(
    background_tasks: BackgroundTasks,
    latitude: float = Query(55.7558, ge=-90, le=90, description="Широта центра"),
    longitude: float = Query(37.6173, ge=-180, le=180, description="Долгота центра"),
    radius: int = Query(50, ge=1, le=100, description="Радиус в км"),
    db: Session = Depends(get_db)
):
    """Обновление кэша данными из внешних API"""
    try:
        background_tasks.add_task(update_stations_from_api, latitude, longitude, radius, db)
        logger.info(f"Запущено обновление кэша для координат ({latitude}, {longitude}), радиус {radius} км")
        return {"message": "Cache update started in background"}
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления кэша: {e}")
        raise HTTPException(status_code=500, detail="Ошибка запуска обновления кэша")

async def update_stations_from_api(lat: float, lon: float, radius: int, db: Session):
    """Фоновая задача для обновления станций из API"""
    from app.services.external_api import fetch_stations_from_open_charge_map

    try:
        logger.info(f"Starting cache update for lat={lat}, lon={lon}, radius={radius}")
        stations_data = await fetch_stations_from_open_charge_map(lat, lon, radius)
        
        if not stations_data:
            logger.warning(f"Нет данных для обновления кэша для координат ({lat}, {lon})")
            return

        added_count = 0
        for data in stations_data:
            # Проверка существования станции
            existing = db.query(models.Station).filter(
                models.Station.latitude == data["latitude"],
                models.Station.longitude == data["longitude"]
            ).first()

            if not existing:
                station = models.Station(**data)
                db.add(station)
                added_count += 1

        db.commit()
        # Clear the station cache after updating
        cache.cache.clear_station_cache()
        logger.info(f"Cache updated with {added_count} new stations out of {len(stations_data)} total")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")
        db.rollback()