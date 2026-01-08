from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.models.station import Station
from app.models.user import User


def add_favorite(db: Session, user_id: int, station_id: int) -> Favorite:
    """Add a station to user's favorites"""
    # Check if user and station exist
    user = db.query(User).filter(User.id == user_id).first()
    station = db.query(Station).filter(Station.id == station_id).first()
    
    if not user:
        raise ValueError("User not found")
    if not station:
        raise ValueError("Station not found")
    
    # Check if already favorited
    existing = db.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.station_id == station_id
    ).first()
    
    if existing:
        return existing
    
    favorite = Favorite(user_id=user_id, station_id=station_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def remove_favorite(db: Session, user_id: int, station_id: int) -> bool:
    """Remove a station from user's favorites"""
    favorite = db.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.station_id == station_id
    ).first()
    
    if favorite:
        db.delete(favorite)
        db.commit()
        return True
    return False


def get_user_favorites(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get all favorite stations for a user"""
    return db.query(Favorite).filter(Favorite.user_id == user_id).offset(skip).limit(limit).all()


def is_favorite(db: Session, user_id: int, station_id: int) -> bool:
    """Check if a station is in user's favorites"""
    return db.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.station_id == station_id
    ).first() is not None


def get_favorite_count(db: Session, station_id: int) -> int:
    """Get the number of users who favorited a station"""
    return db.query(Favorite).filter(Favorite.station_id == station_id).count()