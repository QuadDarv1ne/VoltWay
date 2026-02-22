"""
Tests for External API with mocking.

Tests API integration with mocked HTTP responses.
"""

import pytest
from unittest.mock import patch, AsyncMock
import httpx

from app.services.external_api import (
    fetch_stations_from_open_charge_map,
    fetch_ev_charger_info,
    get_connector_type,
    get_max_power,
    map_status,
    OPEN_CHARGE_MAP_LIMITER,
    API_NINJAS_LIMITER,
)


class TestExternalAPIHelpers:
    """Test helper functions for external API"""

    def test_get_connector_type_empty(self):
        """Test connector type extraction with empty list"""
        result = get_connector_type([])
        assert result == "Unknown"

    def test_get_connector_type_ccs(self):
        """Test CCS connector detection"""
        connections = [
            {"ConnectionType": {"Title": "CCS Type 2"}}
        ]
        result = get_connector_type(connections)
        assert "CCS" in result

    def test_get_connector_type_multiple(self):
        """Test multiple connector types"""
        connections = [
            {"ConnectionType": {"Title": "CCS"}},
            {"ConnectionType": {"Title": "CHAdeMO"}},
            {"ConnectionType": {"Title": "Type 2"}},
        ]
        result = get_connector_type(connections)
        assert "CCS" in result
        assert "CHAdeMO" in result
        assert "Type 2" in result

    def test_get_max_power_empty(self):
        """Test max power with empty list"""
        result = get_max_power([])
        assert result == 0

    def test_get_max_power(self):
        """Test max power extraction"""
        connections = [
            {"PowerKW": 50},
            {"PowerKW": 150},
            {"PowerKW": 22},
        ]
        result = get_max_power(connections)
        assert result == 150

    def test_map_status_empty(self):
        """Test status mapping with empty dict"""
        result = map_status({})
        assert result == "unknown"

    def test_map_status_available(self):
        """Test available status mapping"""
        status_info = {
            "IsOperational": True,
            "IsAvailable": True,
        }
        result = map_status(status_info)
        assert result == "available"

    def test_map_status_occupied(self):
        """Test occupied status mapping"""
        status_info = {
            "IsOperational": True,
            "IsAvailable": False,
        }
        result = map_status(status_info)
        assert result == "occupied"

    def test_map_status_maintenance(self):
        """Test maintenance status mapping"""
        status_info = {
            "IsOperational": False,
        }
        result = map_status(status_info)
        assert result == "maintenance"


class TestOpenChargeMapAPI:
    """Test Open Charge Map API integration"""

    @pytest.fixture
    def mock_ocm_response(self):
        """Sample Open Charge Map API response"""
        return [
            {
                "AddressInfo": {
                    "Title": "Test Station",
                    "AddressLine1": "123 Test St",
                    "Town": "Moscow",
                    "Latitude": 55.7558,
                    "Longitude": 37.6173,
                    "AccessComments": "24/7",
                },
                "Connections": [
                    {
                        "ConnectionType": {"Title": "CCS Type 2"},
                        "PowerKW": 50,
                    }
                ],
                "StatusInfo": {
                    "IsOperational": True,
                    "IsAvailable": True,
                },
            }
        ]

    @pytest.mark.asyncio
    async def test_fetch_stations_success(
        self, mock_ocm_response, httpx_mock
    ):
        """Test successful fetch from Open Charge Map"""
        httpx_mock.add_response(
            url="https://api.openchargemap.io/v3/poi/",
            json=mock_ocm_response,
            method="GET",
        )

        with patch("app.services.external_api.settings") as mock_settings:
            mock_settings.open_charge_map_api_key = "test_key"
            # Disable rate limiter for tests
            with patch("app.services.external_api.OPEN_CHARGE_MAP_LIMITER"):
                result = await fetch_stations_from_open_charge_map(
                    lat=55.7558,
                    lon=37.6173,
                    radius=10,
                )

                assert len(result) == 1
                assert result[0]["title"] == "Test Station"
                assert result[0]["latitude"] == 55.7558

    @pytest.mark.asyncio
    async def test_fetch_stations_no_api_key(self):
        """Test fetch when API key is not configured"""
        with patch("app.services.external_api.settings") as mock_settings:
            mock_settings.open_charge_map_api_key = None

            result = await fetch_stations_from_open_charge_map(
                lat=55.7558,
                lon=37.6173,
                radius=10,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_fetch_stations_timeout(self):
        """Test fetch with timeout error"""
        with patch("app.services.external_api.settings") as mock_settings:
            mock_settings.open_charge_map_api_key = "test_key"

            with patch(
                "app.services.external_api.open_charge_map_breaker.call",
                new_callable=AsyncMock,
            ) as mock_call:
                mock_call.side_effect = httpx.TimeoutException("Timeout")

                result = await fetch_stations_from_open_charge_map(
                    lat=55.7558,
                    lon=37.6173,
                    radius=10,
                )

                assert result == []

    @pytest.mark.asyncio
    async def test_fetch_stations_circuit_breaker_open(self):
        """Test fetch when circuit breaker is open"""
        from app.services.circuit_breaker import CircuitBreakerOpenError

        with patch("app.services.external_api.settings") as mock_settings:
            mock_settings.open_charge_map_api_key = "test_key"

            with patch(
                "app.services.external_api.open_charge_map_breaker.call",
                new_callable=AsyncMock,
            ) as mock_call:
                mock_call.side_effect = CircuitBreakerOpenError(
                    "Circuit breaker is open"
                )

                result = await fetch_stations_from_open_charge_map(
                    lat=55.7558,
                    lon=37.6173,
                    radius=10,
                )

                assert result == []


class TestAPINinjasAPI:
    """Test API-Ninjas integration"""

    @pytest.fixture
    def mock_ninjas_response(self):
        """Sample API-Ninjas response"""
        return [
            {
                "name": "Test Charger",
                "address": "123 Test St",
                "city": "Moscow",
                "latitude": 55.7558,
                "longitude": 37.6173,
            }
        ]

    @pytest.mark.asyncio
    async def test_fetch_ev_charger_success(
        self, mock_ninjas_response, httpx_mock
    ):
        """Test successful fetch from API-Ninjas"""
        httpx_mock.add_response(
            url="https://api.api-ninjas.com/v1/evcharger",
            json=mock_ninjas_response,
            method="GET",
        )

        with patch("app.services.external_api.settings") as mock_settings:
            mock_settings.api_ninjas_key = "test_key"
            # Disable rate limiter for tests
            with patch("app.services.external_api.API_NINJAS_LIMITER"):
                result = await fetch_ev_charger_info(query="Moscow")

                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_fetch_ev_charger_no_api_key(self):
        """Test fetch when API key is not configured"""
        with patch("app.services.external_api.settings") as mock_settings:
            mock_settings.api_ninjas_key = None

            result = await fetch_ev_charger_info(query="Moscow")

            assert result == []


class TestRateLimiting:
    """Test rate limiting for external APIs"""

    @pytest.mark.asyncio
    async def test_open_charge_map_rate_limiter(self):
        """Test that rate limiter is configured"""
        assert OPEN_CHARGE_MAP_LIMITER.max_rate == 1.5
        assert OPEN_CHARGE_MAP_LIMITER.time_period == 60

    @pytest.mark.asyncio
    async def test_api_ninjas_rate_limiter(self):
        """Test that rate limiter is configured"""
        assert API_NINJAS_LIMITER.max_rate == 0.8
        assert API_NINJAS_LIMITER.time_period == 60
