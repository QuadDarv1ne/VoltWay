"""
Reservations API endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.models.reservation import Reservation, ReservationSlot
from app.models.station import Station
from app.schemas.reservation import (
    ReservationCreate,
    ReservationUpdate,
    Reservation,
    ReservationWithStation,
    ReservationAvailability,
    ReservationStats,
    ReservationCancel,
    ReservationSlotCreate,
    ReservationSlot,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("/station/{station_id}", response_model=List[Reservation])
async def get_station_reservations(
    station_id: int,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    date: Optional[datetime] = Query(None, description="Filter by date"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get all reservations for a station"""
    query = select(Reservation).where(Reservation.station_id == station_id)
    
    if status_filter:
        query = query.where(Reservation.status == status_filter)
    
    if date:
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.where(
            and_(
                Reservation.start_time >= start_of_day,
                Reservation.start_time <= end_of_day,
            )
        )
    
    query = query.order_by(Reservation.start_time.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/my", response_model=List[ReservationWithStation])
async def get_my_reservations(
    status_filter: Optional[str] = Query(None),
    upcoming_only: bool = False,
    db: AsyncSession = Depends(get_async_db),
    # TODO: Add user authentication
    # user: User = Depends(get_current_user),
):
    """Get current user's reservations"""
    user_id = 1  # Placeholder until auth is implemented
    
    query = select(Reservation, Station).join(Station).where(
        Reservation.user_id == user_id
    )
    
    if status_filter:
        query = query.where(Reservation.status == status_filter)
    
    if upcoming_only:
        now = datetime.utcnow()
        query = query.where(Reservation.start_time >= now)
    
    query = query.order_by(Reservation.start_time.desc())
    result = await db.execute(query)
    
    reservations = []
    for row in result.all():
        res, station = row
        reservations.append(
            ReservationWithStation(
                **res.__dict__,
                station_title=station.title,
                station_address=station.address,
            )
        )
    
    return reservations


@router.post("/", response_model=Reservation, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    reservation_data: ReservationCreate,
    db: AsyncSession = Depends(get_async_db),
    # TODO: Add user authentication
    # user: User = Depends(get_current_user),
):
    """
    Create a new reservation.
    
    - **station_id**: ID of the station to book
    - **start_time**: Start time of reservation
    - **end_time**: End time of reservation
    - **duration_minutes**: Duration in minutes (max 480)
    """
    user_id = 1  # Placeholder until auth is implemented
    
    # Verify station exists
    station_result = await db.execute(select(Station).where(Station.id == reservation_data.station_id))
    station = station_result.scalar_one_or_none()
    
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    # Check for conflicts
    conflict_query = select(func.count()).where(
        and_(
            Reservation.station_id == reservation_data.station_id,
            Reservation.status.notin_(["cancelled", "no_show"]),
            or_(
                and_(
                    Reservation.start_time <= reservation_data.end_time,
                    Reservation.end_time >= reservation_data.start_time,
                ),
            ),
        )
    )
    conflict_result = await db.execute(conflict_query.select())
    conflicts = conflict_result.scalar() or 0
    
    if conflicts > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot is not available",
        )
    
    # Calculate estimated cost (placeholder logic)
    estimated_cost = reservation_data.duration_minutes * 5.0  # 5 RUB per minute
    
    # Create reservation
    reservation = Reservation(
        user_id=user_id,
        estimated_cost=estimated_cost,
        **reservation_data.model_dump(),
    )
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    logger.info(f"Reservation created for station {reservation_data.station_id}")
    
    return reservation


@router.get("/availability/{station_id}", response_model=ReservationAvailability)
async def check_availability(
    station_id: int,
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    db: AsyncSession = Depends(get_async_db),
):
    """Check if a time slot is available"""
    # Check for conflicts
    conflict_query = select(func.count()).where(
        and_(
            Reservation.station_id == station_id,
            Reservation.status.notin_(["cancelled", "no_show"]),
            or_(
                and_(
                    Reservation.start_time <= end_time,
                    Reservation.end_time >= start_time,
                ),
            ),
        )
    )
    conflict_result = await db.execute(conflict_query.select())
    conflicts = conflict_result.scalar() or 0
    
    # Get available slots
    slots_query = select(ReservationSlot).where(
        and_(
            ReservationSlot.station_id == station_id,
            ReservationSlot.is_active == 1,
        )
    )
    slots_result = await db.execute(slots_query)
    slots = slots_result.scalars().all()
    
    is_available = conflicts == 0
    
    return ReservationAvailability(
        is_available=is_available,
        available_slots=[ReservationSlot.model_validate(s) for s in slots] if is_available else [],
        conflicting_reservations=conflicts,
        message="Slot is available" if is_available else "Time slot is already booked",
    )


@router.get("/{reservation_id}", response_model=Reservation)
async def get_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific reservation by ID"""
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )
    
    return reservation


@router.put("/{reservation_id}", response_model=Reservation)
async def update_reservation(
    reservation_id: int,
    reservation_data: ReservationUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Update an existing reservation"""
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )
    
    # Check if can be modified
    if reservation.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify reservation in current status",
        )
    
    # Update fields
    update_data = reservation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reservation, field, value)
    
    # Recalculate cost if duration changed
    if reservation_data.duration_minutes:
        reservation.estimated_cost = reservation_data.duration_minutes * 5.0
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    return reservation


@router.post("/{reservation_id}/cancel", response_model=Reservation)
async def cancel_reservation(
    reservation_id: int,
    cancel_data: ReservationCancel,
    db: AsyncSession = Depends(get_async_db),
):
    """Cancel a reservation"""
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )
    
    # Check if can be cancelled
    if not reservation.can_cancel():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel reservation at this time",
        )
    
    # Cancel
    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.utcnow()
    reservation.cancellation_reason = cancel_data.reason
    reservation.cancelled_by = cancel_data.cancelled_by
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    logger.info(f"Reservation {reservation_id} cancelled")
    
    return reservation


@router.post("/{reservation_id}/check-in", response_model=Reservation)
async def check_in(
    reservation_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Check in for a reservation"""
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )
    
    if reservation.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only check in confirmed reservations",
        )
    
    reservation.status = "active"
    reservation.checked_in_at = datetime.utcnow()
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    return reservation


@router.post("/{reservation_id}/check-out", response_model=Reservation)
async def check_out(
    reservation_id: int,
    actual_cost: Optional[float] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Check out from a reservation"""
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )
    
    reservation.status = "completed"
    reservation.checked_out_at = datetime.utcnow()
    
    if actual_cost:
        reservation.actual_cost = actual_cost
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    return reservation


@router.get("/station/{station_id}/stats", response_model=ReservationStats)
async def get_reservation_stats(
    station_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get reservation statistics for a station"""
    # Total
    total_query = select(func.count()).where(Reservation.station_id == station_id)
    total_result = await db.execute(total_query.select())
    total = total_result.scalar() or 0
    
    # By status
    status_counts = {}
    for s in ["active", "completed", "cancelled", "no_show", "pending", "confirmed"]:
        count_query = select(func.count()).where(
            and_(
                Reservation.station_id == station_id,
                Reservation.status == s,
            )
        )
        count_result = await db.execute(count_query.select())
        status_counts[s] = count_result.scalar() or 0
    
    # Revenue
    revenue_query = select(func.sum(Reservation.actual_cost)).where(
        and_(
            Reservation.station_id == station_id,
            Reservation.payment_status == "paid",
        )
    )
    revenue_result = await db.execute(revenue_query)
    revenue = float(revenue_result.scalar() or 0)
    
    # Average duration
    avg_duration_query = select(func.avg(Reservation.duration_minutes)).where(
        Reservation.station_id == station_id
    )
    avg_result = await db.execute(avg_duration_query)
    avg_duration = float(avg_result.scalar() or 0)
    
    return ReservationStats(
        total_reservations=total,
        active_reservations=status_counts.get("active", 0),
        completed_reservations=status_counts.get("completed", 0),
        cancelled_reservations=status_counts.get("cancelled", 0),
        no_show_reservations=status_counts.get("no_show", 0),
        total_revenue=revenue,
        avg_duration_minutes=round(avg_duration, 1),
    )
