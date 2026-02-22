from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.station import Station


class FavoriteBase(BaseModel):
    user_id: int
    station_id: int


class FavoriteCreate(FavoriteBase):
    pass


class FavoriteResponse(FavoriteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class FavoriteWithStationResponse(FavoriteBase):
    """Favorite response with full station data included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    station: Optional[Station] = None
