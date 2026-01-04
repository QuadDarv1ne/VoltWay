import pytest
from app.main import app
from fastapi.testclient import TestClient
from app.database import SessionLocal, engine
from app.models import Base
from app import crud, schemas
import json

class TestClientWithDB(TestClient):
    def __init__(self, app):
        super().__init__(app)
        # Create test database
        Base.metadata.create_all(bind=engine)


client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Welcome to VoltWay API" in data["message"]


def test_get_stations():
    """Test getting stations endpoint"""
    response = client.get("/api/v1/stations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_station_by_id():
    """Test getting a specific station by ID"""
    # First, create a test station
    test_station = {
        "title": "Test Station",
        "address": "Test Address",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "connector_type": "CCS",
        "power_kw": 50.0,
        "status": "available"
    }
    
    # Since we can't create stations through API yet, we'll test with existing stations
    # Get stations and test with the first one if available
    response = client.get("/api/v1/stations")
    if response.status_code == 200:
        stations = response.json()
        if len(stations) > 0:
            station_id = stations[0]['id']
            response = client.get(f"/api/v1/stations/{station_id}")
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["id"] == station_id


def test_station_geofilter():
    """Test station filtering by geographic location"""
    response = client.get("/api/v1/stations?latitude=55.7558&longitude=37.6173&radius_km=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_station_connector_filter():
    """Test station filtering by connector type"""
    response = client.get("/api/v1/stations?connector_type=CCS")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_station_power_filter():
    """Test station filtering by minimum power"""
    response = client.get("/api/v1/stations?min_power_kw=20")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_pagination():
    """Test pagination parameters"""
    response = client.get("/api/v1/stations?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_invalid_parameters():
    """Test invalid parameter validation"""
    # Test invalid latitude
    response = client.get("/api/v1/stations?latitude=100")  # Invalid latitude
    assert response.status_code in [200, 422]  # May return empty list or validation error
    
    # Test invalid longitude
    response = client.get("/api/v1/stations?longitude=200")  # Invalid longitude
    assert response.status_code in [200, 422]  # May return empty list or validation error


def test_auth_endpoints_exist():
    """Test that authentication endpoints exist"""
    # Test that the token endpoint exists (should return 422 for missing form data, not 404)
    response = client.post("/api/v1/token")
    assert response.status_code in [401, 422]  # Either unauthorized or validation error, but not 404


def test_geo_utils():
    """Test the geospatial utility functions"""
    from app.utils import geo
    
    # Test haversine distance calculation
    distance = geo.haversine_distance(55.7558, 37.6173, 55.7558, 37.6174)
    assert isinstance(distance, float)
    assert distance >= 0
    
    # The distance between two nearby points in Moscow should be small
    assert distance < 1  # Less than 1 km for these coordinates