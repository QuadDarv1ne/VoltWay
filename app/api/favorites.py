from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.crud import favorite as crud_favorite
from app.database import get_db
from app.models.user import User
from app.schemas.favorite import FavoriteResponse, FavoriteWithStationResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/{station_id}", response_model=FavoriteResponse)
async def add_favorite_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a station to user's favorites"""
    try:
        favorite = crud_favorite.add_favorite(db, current_user.id, station_id)
        return FavoriteResponse(
            id=favorite.id,
            user_id=favorite.user_id,
            station_id=favorite.station_id,
            created_at=favorite.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{station_id}")
async def remove_favorite_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a station from user's favorites"""
    success = crud_favorite.remove_favorite(db, current_user.id, station_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Station removed from favorites"}


@router.get("/", response_model=list[FavoriteWithStationResponse])
async def get_my_favorites(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all favorite stations for current user.

    Uses optimized query with selectinload to prevent N+1 queries
    when accessing station data.
    """
    favorites = crud_favorite.get_user_favorites_with_stations(
        db, current_user.id, skip, limit
    )
    return [
        FavoriteWithStationResponse(
            id=fav.id,
            user_id=fav.user_id,
            station_id=fav.station_id,
            created_at=fav.created_at,
            station=fav.station,
        )
        for fav in favorites
    ]


@router.get("/check/{station_id}")
async def check_is_favorite(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a station is in user's favorites"""
    is_fav = crud_favorite.is_favorite(db, current_user.id, station_id)
    return {"is_favorite": is_fav}


@router.get("/count/{station_id}")
async def get_favorite_count(station_id: int, db: Session = Depends(get_db)):
    """Get the number of users who favorited a station"""
    count = crud_favorite.get_favorite_count(db, station_id)
    return {"favorite_count": count}
