"""
Analytics and Export API endpoints.
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.models.station import Station
from app.models.review import Review
from app.models.reservation import Reservation
from app.utils.logging import log_performance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_async_db),
):
    """Get main dashboard statistics"""
    start_time = datetime.utcnow()
    
    # Total stations
    stations_query = select(func.count()).select_from(Station)
    stations_result = await db.execute(stations_query)
    total_stations = stations_result.scalar() or 0
    
    # Stations by status
    status_counts = {}
    for status in ["available", "occupied", "maintenance", "unknown"]:
        count_query = select(func.count()).where(Station.status == status)
        count_result = await db.execute(count_query.select())
        status_counts[status] = count_result.scalar() or 0
    
    # Total reviews
    reviews_query = select(func.count()).select_from(Review)
    reviews_result = await db.execute(reviews_query)
    total_reviews = reviews_result.scalar() or 0
    
    # Average rating
    avg_rating_query = select(func.avg(Review.rating)).where(
        and_(Review.is_approved == 1, Review.is_hidden == 0)
    )
    avg_result = await db.execute(avg_rating_query)
    avg_rating = float(avg_result.scalar() or 0)
    
    # Reservations stats
    total_reservations_query = select(func.count()).select_from(Reservation)
    total_res_result = await db.execute(total_reservations_query)
    total_reservations = total_res_result.scalar() or 0
    
    # Active reservations
    active_query = select(func.count()).where(Reservation.status == "active")
    active_result = await db.execute(active_query.select())
    active_reservations = active_result.scalar() or 0
    
    # Revenue (current month)
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_query = select(func.sum(Reservation.actual_cost)).where(
        and_(
            Reservation.payment_status == "paid",
            Reservation.created_at >= month_start,
        )
    )
    revenue_result = await db.execute(revenue_query)
    monthly_revenue = float(revenue_result.scalar() or 0)
    
    log_performance(
        start_time,
        "analytics_dashboard",
        total_stations=total_stations,
        total_reviews=total_reviews,
    )
    
    return {
        "stations": {
            "total": total_stations,
            "by_status": status_counts,
        },
        "reviews": {
            "total": total_reviews,
            "average_rating": round(avg_rating, 2),
        },
        "reservations": {
            "total": total_reservations,
            "active": active_reservations,
        },
        "revenue": {
            "monthly": round(monthly_revenue, 2),
            "currency": "RUB",
        },
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/stations/trends")
async def get_station_trends(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db),
):
    """Get station trends over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Stations created per day
    query = select(
        extract('year', Station.created_at).label('year'),
        extract('month', Station.created_at).label('month'),
        extract('day', Station.created_at).label('day'),
        func.count().label('count'),
    ).where(
        Station.created_at >= start_date
    ).group_by(
        extract('year', Station.created_at),
        extract('month', Station.created_at),
        extract('day', Station.created_at),
    ).order_by(
        'year', 'month', 'day'
    )
    
    result = await db.execute(query)
    trends = [
        {
            "date": f"{int(row.year):04d}-{int(row.month):02d}-{int(row.day):02d}",
            "count": row.count,
        }
        for row in result.all()
    ]
    
    return {
        "period_days": days,
        "data": trends,
    }


@router.get("/reviews/summary")
async def get_reviews_summary(
    station_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Get reviews summary"""
    # Base query
    base_filters = [Review.is_approved == 1, Review.is_hidden == 0]
    if station_id:
        base_filters.append(Review.station_id == station_id)
    
    # Total reviews
    total_query = select(func.count()).where(and_(*base_filters))
    total_result = await db.execute(total_query.select())
    total = total_result.scalar() or 0
    
    # Rating distribution
    distribution = {}
    for rating in range(1, 6):
        count_query = select(func.count()).where(
            and_(*base_filters, Review.rating == rating)
        )
        count_result = await db.execute(count_query.select())
        distribution[str(rating)] = count_result.scalar() or 0
    
    # Average by aspect
    aspects = ["cleanliness_rating", "safety_rating", "accessibility_rating"]
    aspect_averages = {}
    for aspect in aspects:
        avg_query = select(func.avg(getattr(Review, aspect))).where(
            and_(*base_filters, getattr(Review, aspect).isnot(None))
        )
        avg_result = await db.execute(avg_query)
        avg = avg_result.scalar()
        if avg:
            aspect_averages[aspect] = round(float(avg), 2)
    
    return {
        "total_reviews": total,
        "rating_distribution": distribution,
        "aspect_averages": aspect_averages,
    }


@router.get("/reservations/heatmap")
async def get_reservation_heatmap(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_async_db),
):
    """Get reservation activity heatmap by hour and day of week"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        extract('dow', Reservation.start_time).label('day_of_week'),  # 0=Sunday
        extract('hour', Reservation.start_time).label('hour'),
        func.count().label('count'),
    ).where(
        Reservation.start_time >= start_date,
        Reservation.status.notin_(["cancelled", "no_show"]),
    ).group_by(
        extract('dow', Reservation.start_time),
        extract('hour', Reservation.start_time),
    ).order_by(
        'day_of_week', 'hour'
    )
    
    result = await db.execute(query)
    
    heatmap = []
    for row in result.all():
        heatmap.append({
            "day_of_week": int(row.day_of_week),
            "hour": int(row.hour),
            "count": row.count,
        })
    
    return {
        "period_days": days,
        "heatmap": heatmap,
    }


@router.get("/export/stations")
async def export_stations(
    format: str = Query("json", regex="^(json|csv)$"),
    db: AsyncSession = Depends(get_async_db),
):
    """Export stations data"""
    start_time = datetime.utcnow()
    
    query = select(Station).order_by(Station.id)
    result = await db.execute(query)
    stations = result.scalars().all()
    
    if format == "json":
        data = [
            {
                "id": s.id,
                "title": s.title,
                "address": s.address,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "connector_type": s.connector_type,
                "power_kw": s.power_kw,
                "status": s.status,
                "price": s.price,
                "avg_rating": s.avg_rating,
                "review_count": s.review_count,
            }
            for s in stations
        ]
        content = json.dumps(data, indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = f"stations_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    else:  # CSV
        output = io.StringIO()
        fieldnames = [
            "id", "title", "address", "latitude", "longitude",
            "connector_type", "power_kw", "status", "price",
            "avg_rating", "review_count"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for s in stations:
            writer.writerow({
                "id": s.id,
                "title": s.title,
                "address": s.address,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "connector_type": s.connector_type,
                "power_kw": s.power_kw,
                "status": s.status,
                "price": s.price,
                "avg_rating": s.avg_rating,
                "review_count": s.review_count,
            })
        
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"stations_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    log_performance(start_time, "export_stations", format=format, count=len(stations))
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/export/reviews")
async def export_reviews(
    station_id: Optional[int] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    db: AsyncSession = Depends(get_async_db),
):
    """Export reviews data"""
    start_time = datetime.utcnow()
    
    query = select(Review).order_by(Review.created_at.desc())
    if station_id:
        query = query.where(Review.station_id == station_id)
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    if format == "json":
        data = [
            {
                "id": r.id,
                "station_id": r.station_id,
                "user_id": r.user_id,
                "rating": r.rating,
                "title": r.title,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
                "helpful_count": r.helpful_count,
            }
            for r in reviews
        ]
        content = json.dumps(data, indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = f"reviews_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    else:  # CSV
        output = io.StringIO()
        fieldnames = [
            "id", "station_id", "user_id", "rating", "title",
            "comment", "created_at", "helpful_count"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for r in reviews:
            writer.writerow({
                "id": r.id,
                "station_id": r.station_id,
                "user_id": r.user_id,
                "rating": r.rating,
                "title": r.title,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
                "helpful_count": r.helpful_count,
            })
        
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"reviews_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    log_performance(start_time, "export_reviews", format=format, count=len(reviews))
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
