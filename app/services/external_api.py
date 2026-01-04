import httpx
from app.core.config import settings
from app.utils import logging as log_util
import logging

logger = log_util.get_logger(__name__)

async def fetch_stations_from_open_charge_map(lat: float, lon: float, radius: int = 10):
    """
    Получение данных о зарядных станциях из Open Charge Map API
    """
    if not settings.open_charge_map_api_key:
        logger.warning("Open Charge Map API key not configured")
        return []

    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json",
        "latitude": lat,
        "longitude": lon,
        "distance": radius,
        "distanceunit": "KM",
        "key": settings.open_charge_map_api_key,
        "maxresults": 100
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Преобразование данных в наш формат
            stations = []
            for item in data:
                station = {
                    "title": item.get("AddressInfo", {}).get("Title", "Unknown Station"),
                    "address": f"{item.get('AddressInfo', {}).get('AddressLine1', '')}, {item.get('AddressInfo', {}).get('Town', '')}",
                    "latitude": item.get("AddressInfo", {}).get("Latitude"),
                    "longitude": item.get("AddressInfo", {}).get("Longitude"),
                    "connector_type": get_connector_type(item.get("Connections", [])),
                    "power_kw": get_max_power(item.get("Connections", [])),
                    "status": "unknown",  # Open Charge Map не всегда предоставляет статус
                    "price": None,
                    "hours": item.get("AddressInfo", {}).get("AccessComments")
                }
                if station["latitude"] and station["longitude"]:
                    stations.append(station)

            return stations
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

async def fetch_ev_charger_info(query: str):
    """
    Получение информации о зарядных станциях через API-Ninjas
    """
    if not settings.api_ninjas_key:
        logger.warning("API-Ninjas key not configured")
        return []

    url = "https://api.api-ninjas.com/v1/evcharger"
    params = {"city": query}
    headers = {"X-Api-Key": settings.api_ninjas_key}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching from API-Ninjas: {e}")
        return []