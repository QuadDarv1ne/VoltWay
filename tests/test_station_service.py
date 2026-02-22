"""
Tests for Station Service layer.

Tests business logic with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.station import StationService, station_service
from app.models.station import Station


class TestStationService:
    """Test StationService business logic"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return StationService()

    @pytest.fixture
    def mock_station_data(self):
        """Sample station data for testing"""
        return {
            "title": "Test Station",
            "address": "123 Test St",
            "latitude": 55.7558,
            "longitude": 37.6173,
            "connector_type": "CCS",
            "power_kw": 50.0,
            "status": "available",
            "price": None,
            "hours": "24/7",
        }

    @pytest.mark.asyncio
    async def test_update_stations_from_api_success(
        self, service, mock_station_data, db_session
    ):
        """Test successful station update from API"""
        with patch(
            "app.services.station.fetch_stations_from_open_charge_map",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = [mock_station_data]

            with patch.object(
                service.repository, "upsert_stations", new_callable=AsyncMock
            ) as mock_upsert:
                mock_upsert.return_value = {
                    "added": 1,
                    "updated": 0,
                    "total": 1,
                }

                with patch("app.services.station.cache"):
                    result = await service.update_stations_from_api(
                        lat=55.7558,
                        lon=37.6173,
                        radius=10,
                    )

                    assert result["total"] == 1
                    assert result["added"] == 1
                    mock_fetch.assert_called_once()
                    mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_stations_from_api_no_data(
        self, service, db_session
    ):
        """Test update when API returns no data"""
        with patch(
            "app.services.station.fetch_stations_from_open_charge_map",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = []

            result = await service.update_stations_from_api(
                lat=55.7558,
                lon=37.6173,
                radius=10,
            )

            assert result["total"] == 0
            assert result["added"] == 0
            assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_update_stations_from_api_error(
        self, service, db_session
    ):
        """Test update when API call fails"""
        with patch(
            "app.services.station.fetch_stations_from_open_charge_map",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            result = await service.update_stations_from_api(
                lat=55.7558,
                lon=37.6173,
                radius=10,
            )

            assert "error" in result
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_station_with_details(
        self, service, db_session, mock_station_data
    ):
        """Test getting station with relationships loaded"""
        # Create test station
        station = Station(**mock_station_data)
        db_session.add(station)
        await db_session.commit()

        with patch(
            "sqlalchemy.orm.selectinload",
            return_value=MagicMock(),
        ):
            result = await service.get_station_with_details(
                db_session, station.id
            )

            assert result is not None
            assert result.id == station.id

    @pytest.mark.asyncio
    async def test_get_stations_count(self, service, db_session, mock_station_data):
        """Test counting stations"""
        # Create test stations
        for i in range(3):
            data = mock_station_data.copy()
            data["latitude"] = 55.7558 + i * 0.001
            station = Station(**data)
            db_session.add(station)

        await db_session.commit()

        count = await service.get_stations_count(db_session)
        assert count >= 3

    @pytest.mark.asyncio
    async def test_get_available_stations_with_location(
        self, service, db_session, mock_station_data
    ):
        """Test getting available stations with location filter"""
        # Create test station
        station = Station(**mock_station_data)
        db_session.add(station)
        await db_session.commit()

        result = await service.get_available_stations(
            db_session,
            latitude=55.7558,
            longitude=37.6173,
            radius_km=5.0,
        )

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_available_stations_no_location(
        self, service, db_session, mock_station_data
    ):
        """Test getting available stations without location filter"""
        # Create test station
        station = Station(**mock_station_data)
        db_session.add(station)
        await db_session.commit()

        result = await service.get_available_stations(db_session)

        assert len(result) >= 1


class TestStationServiceBatchProcessing:
    """Test batch processing in station service"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return StationService()

    @pytest.mark.asyncio
    async def test_batch_upsert_performance(self, service, db_session):
        """Test that batch upsert is efficient"""
        import time

        # Create 50 test stations
        stations_data = []
        for i in range(50):
            stations_data.append({
                "title": f"Station {i}",
                "address": f"Address {i}",
                "latitude": 55.7558 + i * 0.001,
                "longitude": 37.6173 + i * 0.001,
                "connector_type": "CCS",
                "power_kw": 50.0,
                "status": "available",
            })

        start_time = time.time()

        result = await service.repository.upsert_stations(
            db=db_session,
            stations_data=stations_data,
            batch_size=20,
        )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds for 50 stations)
        assert elapsed < 5.0
        assert result["total"] == 50
