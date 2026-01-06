from sqlalchemy.orm import Session

from app.models.station import Station
from app.schemas.station import StationCreate


def get_stations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Station).offset(skip).limit(limit).all()


def get_station(db: Session, station_id: int):
    return db.query(Station).filter(Station.id == station_id).first()


def create_station(db: Session, station: StationCreate):
    db_station = Station(**station.dict())
    db.add(db_station)
    db.commit()
    db.refresh(db_station)
    return db_station
