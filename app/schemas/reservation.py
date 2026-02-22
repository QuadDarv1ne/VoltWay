"""
Pydantic schemas for reservations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReservationBase(BaseModel):
    """Base reservation schema"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int = Field(..., gt=0, le=480)  # Max 8 hours
    slot_number: Optional[int] = None
    connector_type: Optional[str] = None
    user_notes: Optional[str] = None


class ReservationCreate(ReservationBase):
    """Schema for creating a reservation"""
    station_id: int


class ReservationUpdate(BaseModel):
    """Schema for updating a reservation"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    user_notes: Optional[str] = None


class ReservationSlotBase(BaseModel):
    """Base slot schema"""
    slot_number: int
    connector_type: str
    max_power_kw: Optional[float] = None
    is_active: bool = True


class ReservationSlotCreate(ReservationSlotBase):
    """Schema for creating a slot"""
    station_id: int


class ReservationSlot(ReservationSlotBase):
    """Reservation slot schema"""
    id: int
    station_id: int
    
    model_config = {"from_attributes": True}


class Reservation(ReservationBase):
    """Full reservation schema"""
    id: int
    station_id: int
    user_id: int
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    currency: str
    payment_id: Optional[str] = None
    payment_status: str
    payment_method: Optional[str] = None
    status: str
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    
    model_config = {"from_attributes": True}


class ReservationWithStation(Reservation):
    """Reservation with station details"""
    station_title: str
    station_address: str


class ReservationAvailability(BaseModel):
    """Availability check result"""
    is_available: bool
    available_slots: list[ReservationSlot] = []
    conflicting_reservations: int = 0
    message: str


class ReservationStats(BaseModel):
    """Reservation statistics"""
    total_reservations: int
    active_reservations: int
    completed_reservations: int
    cancelled_reservations: int
    no_show_reservations: int
    total_revenue: float
    avg_duration_minutes: float


class ReservationCancel(BaseModel):
    """Schema for cancellation"""
    reason: Optional[str] = None
    cancelled_by: str = "user"
