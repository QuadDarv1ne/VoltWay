from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app import crud, models, schemas
from app.database import get_db
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

    # Геофильтр (упрощенный, без реального расчета расстояния)
    # В реальном проекте использовать PostGIS или подобное
    if latitude is not None and longitude is not None and radius_km is not None:
        # Примерный фильтр по bounding box
        lat_min = latitude - (radius_km / 111.0)  # ~111 км на градус широты
        lat_max = latitude + (radius_km / 111.0)
        lon_min = longitude - (radius_km / (111.0 * abs(latitude)))  # Коррекция для долготы
        lon_max = longitude + (radius_km / (111.0 * abs(latitude)))
        query = query.filter(
            models.Station.latitude.between(lat_min, lat_max),
            models.Station.longitude.between(lon_min, lon_max)
        )

    try:
        stations = query.offset(skip).limit(limit).all()
        logger.info(f"Найдено {len(stations)} станций")
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
        logger.info(f"Cache updated with {added_count} new stations out of {len(stations_data)} total")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")
        db.rollback()