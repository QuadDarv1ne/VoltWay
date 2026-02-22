"""
Pytest configuration for E2E tests with Playwright.
"""

import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def browser(browser: Browser):
    """Use the browser fixture from pytest-playwright"""
    yield browser


@pytest.fixture(scope="function")
def context(context: BrowserContext):
    """Use the context fixture from pytest-playwright"""
    yield context


@pytest.fixture(scope="function")
def page(page: Page):
    """Use the page fixture from pytest-playwright"""
    yield page


# Optional: Custom fixtures for test data
@pytest.fixture
def test_coordinates():
    """Test coordinates for Moscow"""
    return {
        "latitude": 55.7558,
        "longitude": 37.6173,
        "radius_km": 10,
    }


@pytest.fixture
def test_station_data():
    """Sample station data for testing"""
    return {
        "title": "Test Charging Station",
        "address": "Test Street, 123",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "connector_type": "CCS",
        "power_kw": 50.0,
        "status": "available",
    }
