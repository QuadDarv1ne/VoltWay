import logging
from typing import Optional

import httpx
from aiolimiter import AsyncLimiter

from app.core.config import settings
from app.services.circuit_breaker import (
    CircuitBreakerOpenError,
    api_ninjas_breaker,
    open_charge_map_breaker,
)
from app.utils import logging as log_util
from app.utils.retry import async_retry

logger = log_util.get_logger(__name__)

# Rate limiters for external APIs (requests per minute)
# Open Charge Map free tier: 100 requests/hour = ~1.67/min
OPEN_CHARGE_MAP_LIMITER = AsyncLimiter(max_rate=1.5, time_period=60)
# API-Ninjas free tier: 50 requests/hour = ~0.83/min
API_NINJAS_LIMITER = AsyncLimiter(max_rate=0.8, time_period=60)

# Request timeout in seconds
REQUEST_TIMEOUT = 10.0

# Shared HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client with connection pooling"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=REQUEST_TIMEOUT,
                connect=5.0,
                read=REQUEST_TIMEOUT,
                write=5.0,
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0,
            ),
            # Add retry configuration
            transport=httpx.AsyncHTTPTransport(retries=3),
        )
    return _http_client


async def close_http_client():
    """Close shared HTTP client"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


@async_retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(httpx.HTTPError,))
async def _fetch_from_open_charge_map_api(lat: float, lon: float, radius: int) -> list:
    """Internal function with retry logic"""
    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json",
        "latitude": lat,
        "longitude": lon,
        "distance": radius,
        "distanceunit": "KM",
        "key": settings.open_charge_map_api_key,
        "maxresults": 100,
    }

    client = get_http_client()
    # Use timeout parameter directly
    response = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


async def fetch_stations_from_open_charge_map(lat: float, lon: float, radius: int = 10):
    """
    Получение данных о зарядных станциях из Open Charge Map API.

    Features:
    - Circuit breaker protection
    - Automatic retries with exponential backoff
    - Connection pooling
    - Rate limiting
    - Explicit timeouts
    """
    if not settings.open_charge_map_api_key:
        logger.warning("Open Charge Map API key not configured")
        return []

    try:
        # Use rate limiter to respect API limits
        async with OPEN_CHARGE_MAP_LIMITER:
            # Use circuit breaker to prevent cascading failures
            data = await open_charge_map_breaker.call(
                _fetch_from_open_charge_map_api, lat, lon, radius
            )

        # Преобразование данных в наш формат
        stations = []
        for item in data:
            station = {
                "title": item.get("AddressInfo", {}).get(
                    "Unknown Station", "Unknown Station"
                ),
                "address": (
                    f"{item.get('AddressInfo', {}).get('AddressLine1', '')}, "
                    f"{item.get('AddressInfo', {}).get('Town', '')}"
                ),
                "latitude": item.get("AddressInfo", {}).get("Latitude"),
                "longitude": item.get("AddressInfo", {}).get("Longitude"),
                "connector_type": get_connector_type(item.get("Connections", [])),
                "power_kw": get_max_power(item.get("Connections", [])),
                "status": map_status(item.get("StatusInfo", {})),
                "price": None,
                "hours": item.get("AddressInfo", {}).get("AccessComments"),
            }
            if station["latitude"] and station["longitude"]:
                stations.append(station)

        logger.info(f"Fetched {len(stations)} stations from Open Charge Map")
        return stations

    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open for Open Charge Map: {e}")
        return []
    except httpx.TimeoutException as e:
        logger.error(f"Timeout fetching from Open Charge Map: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching from Open Charge Map: {e}")
        return []


def get_connector_type(connections):
    """Определение типа разъема из списка подключений"""
    types = []
    for conn in connections:
        conn_type = conn.get("ConnectionType", {}).get("Title")
        if conn_type:
            if "CCS" in conn_type:
                types.append("CCS")
            elif "CHAdeMO" in conn_type:
                types.append("CHAdeMO")
            elif "Type 2" in conn_type or "Mennekes" in conn_type:
                types.append("Type 2")
    return ", ".join(set(types)) if types else "Unknown"


def get_max_power(connections):
    """Получение максимальной мощности из подключений"""
    powers = [conn.get("PowerKW", 0) for conn in connections if conn.get("PowerKW")]
    return max(powers) if powers else 0


def map_status(status_info: dict) -> str:
    """
    Map external API status to our internal status.

    Args:
        status_info: Status info from Open Charge Map API

    Returns:
        One of: available, occupied, maintenance, unknown
    """
    if not status_info:
        return "unknown"

    status_id = status_info.get("IsOperational", True)
    is_available = status_info.get("IsAvailable", True)

    if not status_id:
        return "maintenance"
    elif is_available:
        return "available"
    else:
        return "occupied"


@async_retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(httpx.HTTPError,))
async def _fetch_from_api_ninjas(query: str) -> list:
    """Internal function with retry logic"""
    url = "https://api.api-ninjas.com/v1/evcharger"
    params = {"city": query}
    headers = {"X-Api-Key": settings.api_ninjas_key}

    client = get_http_client()
    response = await client.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


async def fetch_ev_charger_info(query: str):
    """
    Получение информации о зарядных станциях через API-Ninjas.

    Features:
    - Circuit breaker protection
    - Automatic retries with exponential backoff
    - Connection pooling
    - Rate limiting
    - Explicit timeouts
    """
    if not settings.api_ninjas_key:
        logger.warning("API-Ninjas key not configured")
        return []

    try:
        # Use rate limiter
        async with API_NINJAS_LIMITER:
            # Use circuit breaker
            data = await api_ninjas_breaker.call(_fetch_from_api_ninjas, query)

        logger.info(f"Fetched {len(data)} results from API-Ninjas")
        return data

    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open for API-Ninjas: {e}")
        return []
    except httpx.TimeoutException as e:
        logger.error(f"Timeout fetching from API-Ninjas: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching from API-Ninjas: {e}")
        return []
