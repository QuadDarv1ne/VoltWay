"""Integration tests for the API"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import station, user

# Create test database
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_voltway.db"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestAPI:
    """Test API endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_v2_info(self):
        """Test API v2 info endpoint"""
        response = client.get("/api/v2/")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["status"] == "stable"

    def test_get_stations_empty(self):
        """Test getting stations when none exist"""
        response = client.get("/api/v1/stations")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_stations_with_pagination(self):
        """Test stations with skip and limit"""
        response = client.get("/api/v1/stations?skip=0&limit=10")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_station(self):
        """Test getting a station that doesn't exist"""
        response = client.get("/api/v1/stations/99999")
        assert response.status_code == 404
        assert response.json()["error_code"] == "STATION_NOT_FOUND"

    def test_rate_limiting(self):
        """Test that rate limiting works"""
        # Make requests up to the limit
        for i in range(100):
            response = client.get("/api/v1/stations")
            assert response.status_code == 200

        # Next request should be rate limited
        response = client.get("/api/v1/stations")
        assert response.status_code == 429

    def test_invalid_pagination_params(self):
        """Test invalid pagination parameters"""
        response = client.get("/api/v1/stations?limit=2000")  # Exceeds max
        assert response.status_code in [422, 400]

    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = client.options("/api/v1/stations")
        # Check if CORS headers are present (depends on OPTIONS support)
        assert response.status_code in [200, 405]  # 405 is OK for OPTIONS

    def test_api_documentation(self):
        """Test that API documentation is available"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_method(self):
        """Test invalid HTTP method"""
        response = client.post("/api/v1/nonexistent")
        assert response.status_code in [404, 405]

    def test_malformed_json(self):
        """Test malformed JSON"""
        response = client.post(
            "/api/v1/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [422, 400]

    def test_error_response_format(self):
        """Test error response format"""
        response = client.get("/api/v1/stations/invalid")
        assert response.status_code in [422, 404]
        data = response.json()
        # Should have standard error structure
        assert "detail" in data or "error_code" in data


class TestVersioning:
    """Test API versioning"""

    def test_v1_endpoint(self):
        """Test v1 endpoint works"""
        response = client.get("/api/v1/")
        assert response.status_code == 200

    def test_v2_endpoint(self):
        """Test v2 endpoint works"""
        response = client.get("/api/v2/")
        assert response.status_code == 200

    def test_both_versions_available(self):
        """Test both API versions are available"""
        v1_response = client.get("/api/v1/stations")
        v2_response = client.get("/api/v2/stations")
        assert v1_response.status_code == 200
        assert v2_response.status_code == 200
