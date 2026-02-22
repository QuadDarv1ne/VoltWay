"""
Tests for external API integration with mocking.

These tests use pytest-mock and respx to mock HTTP requests,
ensuring tests don't make real API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx


class TestOpenChargeMapAPI:
    """Tests for Open Charge Map API integration."""

    @pytest.mark.asyncio
    async def test_fetch_stations_success(self):
        """Test successful fetch from Open Charge Map."""
        from app.services.external_api import fetch_stations_from_open_charge_map

        # Mock response data
        mock_response = {
            "id": 12345,
            "AddressInfo": {
                "Title": "Test Station",
                "AddressLine1": "123 Test Street",
                "Town": "Moscow",
                "Latitude": 55.7558,
                "Longitude": 37.6173,
            },
            "Connections": [{"ConnectionType": {"Title": "CCS"}, "PowerKW": 50}],
        }

        # Mock httpx.AsyncClient
        with patch("app.services.external_api.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = [mock_response]
            mock_response_obj.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response_obj

            async with mock_client:
                pass

            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Call function
            stations = await fetch_stations_from_open_charge_map(55.7558, 37.6173, 10)

            # Verify
            assert len(stations) == 1
            assert stations[0]["title"] == "Test Station"
            assert stations[0]["latitude"] == 55.7558
            assert stations[0]["connector_type"] == "CCS"
            assert stations[0]["power_kw"] == 50

    @pytest.mark.asyncio
    async def test_fetch_stations_no_api_key(self):
        """Test fetch when API key is not configured."""
        from app.services.external_api import fetch_stations_from_open_charge_map
        from app.core.config import settings

        # Temporarily remove API key
        original_key = settings.open_charge_map_api_key
        settings.open_charge_map_api_key = None

        try:
            stations = await fetch_stations_from_open_charge_map(55.7558, 37.6173, 10)
            assert stations == []
        finally:
            settings.open_charge_map_api_key = original_key

    @pytest.mark.asyncio
    async def test_fetch_stations_http_error(self):
        """Test fetch when HTTP request fails."""
        from app.services.external_api import fetch_stations_from_open_charge_map

        with patch("app.services.external_api.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.HTTPError("Connection error")

            mock_client_class.return_value.__aenter__.return_value = mock_client

            stations = await fetch_stations_from_open_charge_map(55.7558, 37.6173, 10)
            assert stations == []

    @pytest.mark.asyncio
    async def test_get_connector_type_multiple(self):
        """Test connector type extraction from multiple connections."""
        from app.services.external_api import get_connector_type

        connections = [
            {"ConnectionType": {"Title": "CCS Type 2"}, "PowerKW": 50},
            {"ConnectionType": {"Title": "CHAdeMO"}, "PowerKW": 62.5},
            {"ConnectionType": {"Title": "Type 2"}, "PowerKW": 22},
        ]

        result = get_connector_type(connections)

        # Should contain all three types
        assert "CCS" in result
        assert "CHAdeMO" in result
        assert "Type 2" in result

    @pytest.mark.asyncio
    async def test_get_connector_type_unknown(self):
        """Test connector type when type is unknown."""
        from app.services.external_api import get_connector_type

        connections = [
            {"ConnectionType": {"Title": "Unknown Type"}, "PowerKW": 10},
        ]

        result = get_connector_type(connections)
        # Function returns first found type or "Unknown" if not in our mapping
        assert "Unknown" in result or result == "Unknown Type"

    @pytest.mark.asyncio
    async def test_get_max_power(self):
        """Test max power extraction from multiple connections."""
        from app.services.external_api import get_max_power

        connections = [
            {"ConnectionType": {"Title": "CCS"}, "PowerKW": 50},
            {"ConnectionType": {"Title": "CHAdeMO"}, "PowerKW": 62.5},
            {"ConnectionType": {"Title": "Type 2"}, "PowerKW": 22},
        ]

        result = get_max_power(connections)
        assert result == 62.5

    @pytest.mark.asyncio
    async def test_get_max_power_no_power(self):
        """Test max power when no power info available."""
        from app.services.external_api import get_max_power

        connections = [
            {"ConnectionType": {"Title": "CCS"}},
            {"ConnectionType": {"Title": "CHAdeMO"}},
        ]

        result = get_max_power(connections)
        assert result == 0


class TestAPINinjasAPI:
    """Tests for API-Ninjas integration."""

    @pytest.mark.asyncio
    async def test_fetch_ev_charger_success(self):
        """Test successful fetch from API-Ninjas."""
        from app.services.external_api import fetch_ev_charger_info

        mock_response = [
            {
                "name": "Test Charger",
                "address": "123 Test St",
                "city": "Moscow",
                "latitude": 55.7558,
                "longitude": 37.6173,
            }
        ]

        with patch("app.services.external_api.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response_obj

            mock_client_class.return_value.__aenter__.return_value = mock_client

            stations = await fetch_ev_charger_info("Moscow")

            assert len(stations) == 1
            assert stations[0]["name"] == "Test Charger"

    @pytest.mark.asyncio
    async def test_fetch_ev_charger_no_api_key(self):
        """Test fetch when API-Ninjas key is not configured."""
        from app.services.external_api import fetch_ev_charger_info
        from app.core.config import settings

        original_key = settings.api_ninjas_key
        settings.api_ninjas_key = None

        try:
            stations = await fetch_ev_charger_info("Moscow")
            assert stations == []
        finally:
            settings.api_ninjas_key = original_key

    @pytest.mark.asyncio
    async def test_fetch_ev_charger_timeout(self):
        """Test fetch when request times out."""
        from app.services.external_api import fetch_ev_charger_info

        with patch("app.services.external_api.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ReadTimeout("Request timeout")

            mock_client_class.return_value.__aenter__.return_value = mock_client

            stations = await fetch_ev_charger_info("Moscow")
            assert stations == []


class TestExternalAPIIntegration:
    """Integration tests for external API service."""

    @pytest.mark.asyncio
    async def test_multiple_api_calls_rate_limiting(self):
        """Test that multiple API calls handle rate limiting gracefully."""
        from app.services.external_api import fetch_stations_from_open_charge_map

        # Simulate rate limit response
        with patch("app.services.external_api.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limit exceeded",
                request=MagicMock(),
                response=MagicMock(status_code=429),
            )
            mock_client.get.return_value = mock_response_obj

            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Should return empty list, not raise exception
            stations = await fetch_stations_from_open_charge_map(55.7558, 37.6173, 10)
            assert stations == []
