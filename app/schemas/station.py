from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StationBase(BaseModel):
    title: str
    address: str
    latitude: float
    longitude: float
    connector_type: str
    power_kw: float
    status: str
    price: Optional[float] = None
    hours: Optional[str] = None

class StationCreate(StationBase):
    pass

class Station(StationBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True