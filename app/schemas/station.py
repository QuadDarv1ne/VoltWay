from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, ConfigDict


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

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("Широта должна быть в диапазоне от -90 до 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("Долгота должна быть в диапазоне от -180 до 180")
        return v

    @field_validator("power_kw")
    @classmethod
    def validate_power_kw(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Мощность должна быть положительной")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ["available", "occupied", "maintenance", "unknown"]
        if v not in valid_statuses:
            raise ValueError(f"Статус должен быть одним из: {valid_statuses}")
        return v


class StationCreate(StationBase):
    pass


class Station(StationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_updated: datetime
