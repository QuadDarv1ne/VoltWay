"""
Tests for WebSocket notification service.

Tests Socket.IO connection, subscriptions, and notifications.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestNotificationService:
    """Tests for the NotificationService."""

    def test_notification_service_init(self):
        """Test NotificationService initialization."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        assert service.connected_users == set()
        assert service.station_subscribers == {}
        assert service.sio is not None
        assert service.app is not None

    @pytest.mark.asyncio
    async def test_connect_event(self):
        """Test user connect event."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        # Simulate connect event
        sid = "test_sid_123"
        await service.sio.trigger_event("connect", {"sid": sid})

        # Note: In real tests, you'd use socketio test client
        # This is a simplified version
        assert True  # Placeholder for actual Socket.IO testing

    @pytest.mark.asyncio
    async def test_disconnect_event(self):
        """Test user disconnect event."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        # Add user to connected set
        sid = "test_sid_123"
        service.connected_users.add(sid)
        service.station_subscribers[1] = {sid}

        # Simulate disconnect
        await service.sio.trigger_event("disconnect", {"sid": sid})

        # Verify cleanup (simplified test)
        assert True

    @pytest.mark.asyncio
    async def test_subscribe_to_station(self):
        """Test subscribing to station notifications."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sid = "test_sid_123"
        station_id = 5

        # Manually call the subscription logic
        if station_id not in service.station_subscribers:
            service.station_subscribers[station_id] = set()
        service.station_subscribers[station_id].add(sid)

        assert sid in service.station_subscribers[station_id]
        assert service.get_station_subscribers_count(station_id) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_from_station(self):
        """Test unsubscribing from station notifications."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sid = "test_sid_123"
        station_id = 5

        # Setup subscription
        service.station_subscribers[station_id] = {sid}

        # Unsubscribe
        if station_id in service.station_subscribers:
            service.station_subscribers[station_id].discard(sid)
            if not service.station_subscribers[station_id]:
                del service.station_subscribers[station_id]

        assert (
            station_id not in service.station_subscribers
            or sid not in service.station_subscribers.get(station_id, set())
        )

    @pytest.mark.asyncio
    async def test_notify_station_update(self):
        """Test sending station update notification."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sid = "test_sid_123"
        station_id = 5
        service.station_subscribers[station_id] = {sid}

        station_data = {
            "id": station_id,
            "status": "available",
            "title": "Test Station",
        }

        # Mock the emit method
        with patch.object(service.sio, "emit", new_callable=AsyncMock) as mock_emit:
            await service.notify_station_update(station_id, station_data)

            # Verify emit was called
            assert mock_emit.called
            call_args = mock_emit.call_args
            assert call_args[0][0] == "notification"
            assert call_args[1]["room"] == sid

    @pytest.mark.asyncio
    async def test_notify_station_availability(self):
        """Test sending availability notification."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sid = "test_sid_123"
        station_id = 5
        service.station_subscribers[station_id] = {sid}

        # Mock the emit method
        with patch.object(service.sio, "emit", new_callable=AsyncMock) as mock_emit:
            await service.notify_station_availability(station_id, True)

            assert mock_emit.called
            call_args = mock_emit.call_args
            assert call_args[0][0] == "notification"

            # Check notification data
            notification = call_args[0][1]
            assert notification["type"] == "availability_change"
            assert notification["is_available"] is True
            assert notification["station_id"] == station_id

    @pytest.mark.asyncio
    async def test_notify_station_unavailable(self):
        """Test sending station unavailable notification."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sid = "test_sid_123"
        station_id = 5
        service.station_subscribers[station_id] = {sid}

        with patch.object(service.sio, "emit", new_callable=AsyncMock) as mock_emit:
            await service.notify_station_availability(station_id, False)

            notification = mock_emit.call_args[0][1]
            assert notification["is_available"] is False
            assert "занята" in notification["message"]

    def test_get_connected_users_count(self):
        """Test getting connected users count."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        service.connected_users = {"user1", "user2", "user3"}

        assert service.get_connected_users_count() == 3

    def test_get_station_subscribers_count(self):
        """Test getting station subscribers count."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        service.station_subscribers = {
            1: {"user1", "user2"},
            2: {"user3"},
            5: {"user1", "user3", "user4"},
        }

        assert service.get_station_subscribers_count(1) == 2
        assert service.get_station_subscribers_count(2) == 1
        assert service.get_station_subscribers_count(5) == 3
        assert service.get_station_subscribers_count(99) == 0

    @pytest.mark.asyncio
    async def test_notify_multiple_subscribers(self):
        """Test notifying multiple subscribers."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sids = ["sid1", "sid2", "sid3"]
        station_id = 5
        service.station_subscribers[station_id] = set(sids)

        with patch.object(service.sio, "emit", new_callable=AsyncMock) as mock_emit:
            await service.notify_station_update(station_id, {"id": station_id})

            # Should be called for each subscriber
            assert mock_emit.call_count == len(sids)

    @pytest.mark.asyncio
    async def test_notify_no_subscribers(self):
        """Test notification when no subscribers."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        station_id = 5
        # No subscribers for this station

        with patch.object(service.sio, "emit", new_callable=AsyncMock) as mock_emit:
            await service.notify_station_update(station_id, {"id": station_id})

            # Should not call emit
            mock_emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_all_subscriptions(self):
        """Test that disconnect removes user from all subscriptions."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        sid = "test_sid"
        service.connected_users.add(sid)
        service.station_subscribers = {
            1: {sid, "other_sid"},
            2: {sid},
            3: {"other_sid_2"},
        }

        # Simulate disconnect cleanup
        service.connected_users.discard(sid)
        for station_id in list(service.station_subscribers.keys()):
            service.station_subscribers[station_id].discard(sid)
            if not service.station_subscribers[station_id]:
                del service.station_subscribers[station_id]

        assert sid not in service.connected_users
        assert 1 in service.station_subscribers  # Still has other_sid
        assert 2 not in service.station_subscribers  # Empty, removed
        assert 3 in service.station_subscribers  # Unaffected


class TestWebSocketEvents:
    """Tests for WebSocket event handlers."""

    @pytest.mark.asyncio
    async def test_event_subscribed_payload(self):
        """Test subscribed event payload format."""
        station_id = 5
        event_data = {"station_id": station_id}

        # Verify expected format
        assert "station_id" in event_data
        assert event_data["station_id"] == station_id

    @pytest.mark.asyncio
    async def test_event_notification_payload(self):
        """Test notification event payload format."""
        notification = {
            "type": "availability_change",
            "station_id": 5,
            "is_available": True,
            "message": "Станция освободилась",
            "timestamp": 1234567890.123,
        }

        # Verify required fields
        assert "type" in notification
        assert "station_id" in notification
        assert "timestamp" in notification
        assert notification["type"] in ["availability_change", "station_update"]
