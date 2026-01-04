import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import crud
from app.database import SessionLocal
from app.utils.auth import get_password_hash
from app.models.user import User


client = TestClient(app)


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": get_password_hash("testpassword"),
        "is_active": True,
        "is_admin": False
    }
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    yield user
    
    # Cleanup
    db_session.delete(user)
    db_session.commit()


def test_user_registration():
    """Test user registration endpoint"""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword",
        "is_active": True,
        "is_admin": False
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "id" in data


def test_user_login():
    """Test user login endpoint"""
    # First create a user to login with
    user_data = {
        "username": "loginuser",
        "email": "login@example.com",
        "password": "loginpassword",
        "is_active": True,
        "is_admin": False
    }
    
    # Create the user
    register_response = client.post("/api/v1/users/", json=user_data)
    assert register_response.status_code == 200
    
    # Now try to login
    login_data = {
        "username": "loginuser",
        "password": "loginpassword"
    }
    
    response = client.post(
        "/api/v1/token",
        data=login_data  # OAuth2PasswordRequestForm expects form data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_invalid_login():
    """Test login with invalid credentials"""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    
    response = client.post(
        "/api/v1/token",
        data=login_data
    )
    
    assert response.status_code == 401


def test_get_current_user():
    """Test getting current user info with valid token"""
    # First get a token by logging in
    user_data = {
        "username": "currentuser",
        "email": "current@example.com",
        "password": "currentpassword",
        "is_active": True,
        "is_admin": False
    }
    
    # Create the user
    register_response = client.post("/api/v1/users/", json=user_data)
    assert register_response.status_code == 200
    
    # Login to get token
    login_data = {
        "username": "currentuser",
        "password": "currentpassword"
    }
    
    login_response = client.post(
        "/api/v1/token",
        data=login_data
    )
    
    assert login_response.status_code == 200
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Use token to get user info
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["username"] == "currentuser"
    assert user_info["email"] == "current@example.com"


def test_get_current_user_without_token():
    """Test getting current user info without token"""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_duplicate_username_registration():
    """Test that registering with duplicate username fails"""
    user_data = {
        "username": "duplicateuser",
        "email": "dup1@example.com",
        "password": "password123",
        "is_active": True,
        "is_admin": False
    }
    
    # Register first user
    response1 = client.post("/api/v1/users/", json=user_data)
    assert response1.status_code == 200
    
    # Try to register with same username
    user_data2 = {
        "username": "duplicateuser",  # Same username
        "email": "dup2@example.com",  # Different email
        "password": "password",
        "is_active": True,
        "is_admin": False
    }
    
    response2 = client.post("/api/v1/users/", json=user_data2)
    assert response2.status_code == 400


def test_duplicate_email_registration():
    """Test that registering with duplicate email fails"""
    user_data = {
        "username": "uniqueuser1",
        "email": "same@example.com",
        "password": "password123",
        "is_active": True,
        "is_admin": False
    }
    
    # Register first user
    response1 = client.post("/api/v1/users/", json=user_data)
    assert response1.status_code == 200
    
    # Try to register with same email
    user_data2 = {
        "username": "uniqueuser2",  # Different username
        "email": "same@example.com",  # Same email
        "password": "password",
        "is_active": True,
        "is_admin": False
    }
    
    response2 = client.post("/api/v1/users/", json=user_data2)
    assert response2.status_code == 400