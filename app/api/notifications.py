from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.notifications import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/test/{station_id}")
async def send_test_notification(
    station_id: int,
    message: str = "Тестовое уведомление",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a test notification for a station (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    notification_data = {
        "message": message,
        "station_id": station_id,
        "type": "test"
    }
    
    await notification_service.notify_station_update(station_id, notification_data)
    return {"message": "Test notification sent"}


@router.get("/stats")
async def get_notification_stats():
    """Get notification service statistics"""
    return {
        "connected_users": notification_service.get_connected_users_count(),
        "subscriptions": {
            station_id: notification_service.get_station_subscribers_count(station_id)
            for station_id in notification_service.station_subscribers.keys()
        }
    }


@router.post("/trigger/{station_id}")
async def trigger_station_notification(
    station_id: int,
    is_available: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger availability change notification for a station"""
    await notification_service.notify_station_availability(station_id, is_available)
    return {"message": f"Availability notification triggered for station {station_id}"}