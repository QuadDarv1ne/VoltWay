from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app import crud, models, schemas
from app.database import get_db

router = APIRouter()

@router.get("/stations", response_model=List[schemas.Station])
def read_stations(
    skip: int = 0,
    limit: int = 100,
    latitude: Optional[float] = Query(None, description="Широта центра поиска"),
    longitude: Optional[float] = Query(None, description="Долгота центра поиска"),
    radius_km: Optional[float] = Query(None, description="Радиус поиска в км"),
    connector_type: Optional[str] = Query(None, description="Тип разъема"),
    min_power_kw: Optional[float] = Query(None, description="Минимальная мощность"),
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
    if latitude and longitude and radius_km:
        # Примерный фильтр по bounding box
        lat_min = latitude - (radius_km / 111.0)  # ~111 км на градус широты
        lat_max = latitude + (radius_km / 111.0)
        lon_min = longitude - (radius_km / (111.0 * abs(latitude)))  # Коррекция для долготы
        lon_max = longitude + (radius_km / (111.0 * abs(latitude)))
        query = query.filter(
            models.Station.latitude.between(lat_min, lat_max),
            models.Station.longitude.between(lon_min, lon_max)
        )

    stations = query.offset(skip).limit(limit).all()
    return stations

@router.get("/stations/{station_id}", response_model=schemas.Station)
def read_station(station_id: int, db: Session = Depends(get_db)):
    db_station = crud.get_station(db, station_id=station_id)
    if db_station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return db_station

@router.post("/stations/update_cache")
async def update_cache(
    background_tasks: BackgroundTasks,
    latitude: float = Query(55.7558, description="Широта центра"),
    longitude: float = Query(37.6173, description="Долгота центра"),
    radius: int = Query(50, description="Радиус в км"),
    db: Session = Depends(get_db)
):
    """Обновление кэша данными из внешних API"""
    background_tasks.add_task(update_stations_from_api, latitude, longitude, radius, db)
    return {"message": "Cache update started in background"}

async def update_stations_from_api(lat: float, lon: float, radius: int, db: Session):
    """Фоновая задача для обновления станций из API"""
    from app.services.external_api import fetch_stations_from_open_charge_map
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Starting cache update for lat={lat}, lon={lon}, radius={radius}")
        stations_data = await fetch_stations_from_open_charge_map(lat, lon, radius)

        for data in stations_data:
            # Проверка существования станции
            existing = db.query(models.Station).filter(
                models.Station.latitude == data["latitude"],
                models.Station.longitude == data["longitude"]
            ).first()

            if not existing:
                station = models.Station(**data)
                db.add(station)

        db.commit()
        logger.info(f"Cache updated with {len(stations_data)} stations")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")
        db.rollback()