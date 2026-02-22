"""
Reservation model for station booking system.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models import Base


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    station_id = Column(Integer, ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Reservation details
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Slot information
    slot_number = Column(Integer, nullable=True)  # If station has multiple charging slots
    connector_type = Column(String(50), nullable=True)
    
    # Pricing
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    currency = Column(String(3), default="RUB")
    
    # Payment
    payment_id = Column(String(100), nullable=True)
    payment_status = Column(String(20), default="pending")  # pending, paid, refunded, failed
    payment_method = Column(String(50), nullable=True)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)
    # pending, confirmed, active, completed, cancelled, no_show
    
    # Cancellation
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(String(20), nullable=True)  # user, admin, system
    
    # Check-in/Check-out
    checked_in_at = Column(DateTime, nullable=True)
    checked_out_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Notes
    user_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Relationships
    station = relationship("Station", back_populates="reservations")
    user = relationship("User", back_populates="reservations")
    
    # Indexes
    __table_args__ = (
        Index("idx_reservation_station_time", "station_id", "start_time"),
        Index("idx_reservation_user_time", "user_id", "start_time"),
        Index("idx_reservation_status", "status"),
        Index("idx_reservation_payment", "payment_status"),
        CheckConstraint(
            "end_time > start_time",
            name="chk_reservation_time_range"
        ),
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 480",
            name="chk_reservation_duration"
        ),  # Max 8 hours
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="chk_reservation_cost"
        ),
    )
    
    def __repr__(self):
        return (
            f"<Reservation(id={self.id}, station_id={self.station_id}, "
            f"start={self.start_time}, status={self.status})>"
        )
    
    def is_active(self) -> bool:
        """Check if reservation is currently active"""
        now = datetime.utcnow()
        return (
            self.status == "active" or
            (self.status == "confirmed" and self.start_time <= now <= self.end_time)
        )
    
    def can_cancel(self) -> bool:
        """Check if reservation can be cancelled"""
        if self.status not in ["pending", "confirmed"]:
            return False
        
        # Can cancel up to 1 hour before start time
        now = datetime.utcnow()
        hours_before = (self.start_time - now).total_seconds() / 3600
        return hours_before >= 1


class ReservationSlot(Base):
    """
    Charging slots at a station.
    Some stations may have multiple charging points.
    """
    __tablename__ = "reservation_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    slot_number = Column(Integer, nullable=False)
    connector_type = Column(String(50), nullable=False)
    max_power_kw = Column(Float, nullable=True)
    is_active = Column(Integer, default=1)
    
    # Relationships
    station = relationship("Station", backref="charging_slots")
    
    __table_args__ = (
        Index("idx_slot_station", "station_id", "slot_number", unique=True),
    )
    
    def __repr__(self):
        return f"<ReservationSlot(station_id={self.station_id}, slot={self.slot_number})>"
