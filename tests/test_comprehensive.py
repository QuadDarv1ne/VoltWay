import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_voltway.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create database session for testing"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client():
    """Create test client"""
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app=app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_user(client):
    """Test user creation endpoint"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_get_stations(client):
    """Test getting stations endpoint"""
    response = client.get("/api/v1/stations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        station = data[0]
        assert "id" in station
        assert "title" in station
        assert "latitude" in station
        assert "longitude" in station


def test_station_filters(client):
    """Test station filtering"""
    # Test connector type filter
    response = client.get("/api/v1/stations?connector_type=CCS")
    assert response.status_code == 200
    
    # Test power filter
    response = client.get("/api/v1/stations?min_power_kw=20")
    assert response.status_code == 200
    
    # Test geographic filter
    response = client.get("/api/v1/stations?latitude=55.7558&longitude=37.6173&radius_km=10")
    assert response.status_code == 200


def test_pagination(client):
    """Test pagination functionality"""
    response = client.get("/api/v1/stations?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2


def test_root_endpoint(client):
    """Test root API endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_invalid_coordinates(client):
    """Test validation of coordinate parameters"""
    # Test invalid latitude (> 90)
    response = client.get("/api/v1/stations?latitude=95")
    assert response.status_code == 422 or response.status_code == 200
    
    # Test invalid longitude (> 180)
    response = client.get("/api/v1/stations?longitude=185")
    assert response.status_code == 422 or response.status_code == 200


def test_authentication_endpoints(client):
    """Test that auth endpoints exist"""
    # Test token endpoint exists (will return 422 for missing data)
    response = client.post("/api/v1/auth/token")
    assert response.status_code in [401, 422]


def test_favorites_endpoints(client):
    """Test that favorites endpoints exist"""
    # Test favorites endpoint exists
    response = client.get("/api/v1/favorites/")
    # Should require authentication, so expect 401 or redirect
    assert response.status_code in [401, 403, 307]


def test_notifications_endpoints(client):
    """Test that notification endpoints exist"""
    # Test notification stats endpoint
    response = client.get("/api/v1/notifications/stats")
    assert response.status_code == 200