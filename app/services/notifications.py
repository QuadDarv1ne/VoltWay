import asyncio
import json
from typing import Dict, Set

import socketio
from fastapi import FastAPI

from app.crud import station as crud_station
from app.database import get_db
from app.models.station import Station


class NotificationService:
    def __init__(self):
        self.sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
        self.app = socketio.ASGIApp(self.sio)
        self.connected_users: Set[str] = set()
        self.station_subscribers: Dict[int, Set[str]] = {}

    async def initialize_sockets(self, fastapi_app: FastAPI):
        """Initialize Socket.IO with FastAPI app"""

        @self.sio.event
        async def connect(sid, environ):
            print(f"User connected: {sid}")
            self.connected_users.add(sid)

        @self.sio.event
        async def disconnect(sid):
            print(f"User disconnected: {sid}")
            self.connected_users.discard(sid)
            # Remove user from all subscriptions
            for station_id in list(self.station_subscribers.keys()):
                self.station_subscribers[station_id].discard(sid)
                if not self.station_subscribers[station_id]:
                    del self.station_subscribers[station_id]

        @self.sio.event
        async def subscribe_to_station(sid, data):
            """Subscribe to notifications for a specific station"""
            station_id = data.get("station_id")
            if station_id:
                if station_id not in self.station_subscribers:
                    self.station_subscribers[station_id] = set()
                self.station_subscribers[station_id].add(sid)
                await self.sio.emit("subscribed", {"station_id": station_id}, room=sid)

        @self.sio.event
        async def unsubscribe_from_station(sid, data):
            """Unsubscribe from notifications for a specific station"""
            station_id = data.get("station_id")
            if station_id and station_id in self.station_subscribers:
                self.station_subscribers[station_id].discard(sid)
                if not self.station_subscribers[station_id]:
                    del self.station_subscribers[station_id]
                await self.sio.emit(
                    "unsubscribed", {"station_id": station_id}, room=sid
                )

    async def notify_station_update(self, station_id: int, station_data: dict):
        """Send notification when station status changes"""
        if station_id in self.station_subscribers:
            notification = {
                "type": "station_update",
                "station_id": station_id,
                "data": station_data,
                "timestamp": asyncio.get_event_loop().time(),
            }

            # Send to all subscribers of this station
            for sid in self.station_subscribers[station_id]:
                await self.sio.emit("notification", notification, room=sid)

    async def notify_station_availability(self, station_id: int, is_available: bool):
        """Send notification when station availability changes"""
        notification = {
            "type": "availability_change",
            "station_id": station_id,
            "is_available": is_available,
            "message": f"Станция {'освободилась' if is_available else 'занята'}",
            "timestamp": asyncio.get_event_loop().time(),
        }

        if station_id in self.station_subscribers:
            for sid in self.station_subscribers[station_id]:
                await self.sio.emit("notification", notification, room=sid)

    def get_connected_users_count(self) -> int:
        """Get number of currently connected users"""
        return len(self.connected_users)

    def get_station_subscribers_count(self, station_id: int) -> int:
        """Get number of subscribers for a specific station"""
        return len(self.station_subscribers.get(station_id, set()))


# Global notification service instance
notification_service = NotificationService()
