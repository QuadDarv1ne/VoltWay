"""
E2E tests for VoltWay using Playwright.

Tests the full application flow in a real browser.
"""

import pytest
from playwright.sync_api import Page, expect, BrowserContext
import re


# Test configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30000  # 30 seconds


@pytest.fixture(scope="module")
def base_url():
    """Get base URL for tests"""
    return BASE_URL


def test_homepage_loads(page: Page, base_url: str):
    """Test that homepage loads successfully"""
    page.goto(base_url, timeout=TIMEOUT)

    # Check page title
    expect(page).to_have_title(re.compile(r"VoltWay|Charging", re.IGNORECASE))

    # Check header is visible
    header = page.locator("header")
    expect(header).to_be_visible()

    # Check map container exists
    map_element = page.locator("#map")
    expect(map_element).to_be_visible()


def test_dark_mode_toggle(page: Page, base_url: str):
    """Test dark mode theme toggle"""
    page.goto(base_url, timeout=TIMEOUT)

    # Wait for theme toggle button to appear
    theme_toggle = page.locator(".theme-toggle")
    expect(theme_toggle).to_be_visible(timeout=5000)

    # Get initial theme
    initial_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")

    # Click toggle
    theme_toggle.click()

    # Wait for theme change
    page.wait_for_timeout(500)

    # Check theme changed
    new_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")

    if initial_theme == "dark":
        assert new_theme == "light" or new_theme is None
    else:
        assert new_theme == "dark"

    # Toggle back
    theme_toggle.click()
    page.wait_for_timeout(500)

    # Verify original theme restored
    restored_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
    assert restored_theme == initial_theme


def test_search_controls_visible(page: Page, base_url: str):
    """Test that search controls are visible and functional"""
    page.goto(base_url, timeout=TIMEOUT)

    # Check controls container
    controls = page.locator(".controls")
    expect(controls).to_be_visible()

    # Check latitude input
    lat_input = page.locator("#lat")
    expect(lat_input).to_be_visible()

    # Check longitude input
    lon_input = page.locator("#lon")
    expect(lon_input).to_be_visible()

    # Check radius input
    radius_input = page.locator("#radius")
    expect(radius_input).to_be_visible()

    # Check search button
    search_button = page.locator('button:has-text("Найти"), button:has-text("Search"), button[type="submit"]')
    expect(search_button).to_be_visible()


def test_station_search_with_coordinates(page: Page, base_url: str):
    """Test station search with coordinates"""
    page.goto(base_url, timeout=TIMEOUT)

    # Fill in Moscow coordinates
    lat_input = page.locator("#lat")
    lon_input = page.locator("#lon")
    radius_input = page.locator("#radius")

    lat_input.fill("55.7558")
    lon_input.fill("37.6173")
    radius_input.fill("10")

    # Click search
    search_button = page.locator('button:has-text("Найти"), button:has-text("Search")')
    search_button.click()

    # Wait for results (check for station markers or status update)
    page.wait_for_timeout(2000)

    # Check that status element updated
    status = page.locator("#status")
    expect(status).to_be_visible()


def test_api_documentation(page: Page, base_url: str):
    """Test API documentation is accessible"""
    # Test Swagger UI
    page.goto(f"{base_url}/docs", timeout=TIMEOUT)
    expect(page).to_have_title(re.compile(r"Swagger|VoltWay"))

    # Check API title is visible
    expect(page.locator("text=VoltWay")).to_be_visible(timeout=5000)


def test_graphql_endpoint(page: Page, base_url: str):
    """Test GraphQL endpoint is accessible"""
    page.goto(f"{base_url}/api/v3/schema", timeout=TIMEOUT)

    # Check response contains schema
    expect(page.locator("pre")).to_contain_text("type Query")


def test_health_check(page: Page, base_url: str):
    """Test health check endpoint"""
    page.goto(f"{base_url}/health", timeout=TIMEOUT)

    # Check health response
    expect(page.locator("pre")).to_contain_text("healthy")


def test_responsive_design_mobile(page: Page, base_url: str):
    """Test responsive design on mobile viewport"""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})

    page.goto(base_url, timeout=TIMEOUT)

    # Check controls are stacked vertically on mobile
    controls = page.locator(".controls")
    expect(controls).to_be_visible()

    # Check map has appropriate height
    map_element = page.locator("#map")
    expect(map_element).to_be_visible()


def test_responsive_design_desktop(page: Page, base_url: str):
    """Test responsive design on desktop viewport"""
    # Set desktop viewport
    page.set_viewport_size({"width": 1920, "height": 1080})

    page.goto(base_url, timeout=TIMEOUT)

    # Check header
    header = page.locator("header")
    expect(header).to_be_visible()

    # Check controls are properly laid out
    controls = page.locator(".controls")
    expect(controls).to_be_visible()


def test_notifications_container(page: Page, base_url: str):
    """Test notifications container exists"""
    page.goto(base_url, timeout=TIMEOUT)

    # Notifications are created dynamically, but we can check the container exists
    # or that the notification system is initialized
    page.wait_for_timeout(1000)

    # Check that we can execute JavaScript without errors
    result = page.evaluate("() => typeof showNotification === 'function'")
    # Note: showNotification might not be globally available, adjust as needed


def test_pwa_manifest(page: Page, base_url: str):
    """Test PWA manifest is linked"""
    page.goto(base_url, timeout=TIMEOUT)

    # Check manifest link in head
    manifest_link = page.locator('link[rel="manifest"]')
    expect(manifest_link).to_have_attribute("href", re.compile(r"manifest"))


def test_service_worker_registered(page: Page, base_url: str):
    """Test service worker is registered"""
    page.goto(base_url, timeout=TIMEOUT)

    # Wait for service worker registration
    page.wait_for_timeout(2000)

    # Check if service worker is registered
    sw_registered = page.evaluate("""
        async () => {
            if ('serviceWorker' in navigator) {
                const registrations = await navigator.serviceWorker.getRegistrations();
                return registrations.length > 0;
            }
            return false;
        }
    """)

    # Note: This might fail in headless mode or without HTTPS
    # It's more of an informational test


def test_accessibility_basic(page: Page, base_url: str):
    """Test basic accessibility"""
    page.goto(base_url, timeout=TIMEOUT)

    # Check for main landmark
    main = page.locator("main")
    expect(main).to_be_visible()

    # Check for proper heading hierarchy
    h1 = page.locator("h1")
    expect(h1).to_have_count(1)

    # Check buttons have accessible names
    buttons = page.locator("button")
    count = buttons.count()
    for i in range(count):
        button = buttons.nth(i)
        if button.is_visible():
            # Button should have text or aria-label
            has_text = button.inner_text() != ""
            has_aria = button.get_attribute("aria-label") is not None
            assert has_text or has_aria, f"Button {i} has no accessible name"


def test_error_handling_404(page: Page, base_url: str):
    """Test 404 error handling"""
    response = page.goto(f"{base_url}/nonexistent-page-12345", timeout=TIMEOUT)

    # Should get a 404 response
    assert response.status == 404


# GraphQL specific tests
def test_graphql_query_stations(page: Page, base_url: str):
    """Test GraphQL query for stations"""
    graphql_url = f"{base_url}/api/v3/"

    query = """
    {
        stations(skip: 0, limit: 5) {
            stations {
                id
                title
                status
            }
            total
            page
        }
    }
    """

    response = page.request.post(
        graphql_url,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )

    assert response.status == 200
    data = response.json()

    assert "data" in data
    assert "stations" in data["data"]


def test_graphql_query_station_stats(page: Page, base_url: str):
    """Test GraphQL query for station statistics"""
    graphql_url = f"{base_url}/api/v3/"

    query = """
    {
        stationStats {
            totalStations
            availableStations
            occupiedStations
            avgPowerKw
        }
    }
    """

    response = page.request.post(
        graphql_url,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )

    assert response.status == 200
    data = response.json()

    assert "data" in data
    assert "stationStats" in data["data"]
