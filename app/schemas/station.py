from pydantic import BaseModel, validator
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
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('Широта должна быть в диапазоне от -90 до 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('Долгота должна быть в диапазоне от -180 до 180')
        return v
    
    @validator('power_kw')
    def validate_power_kw(cls, v):
        if v <= 0:
            raise ValueError('Мощность должна быть положительной')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['available', 'occupied', 'maintenance', 'unknown']
        if v not in valid_statuses:
            raise ValueError(f'Статус должен быть одним из: {valid_statuses}')
        return v

class StationCreate(StationBase):
    pass

class Station(StationBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True