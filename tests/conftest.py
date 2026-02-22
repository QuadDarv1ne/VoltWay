"""Test configuration and fixtures"""

import os
import sys

# Set testing environment BEFORE any app imports
os.environ["TESTING"] = "true"
os.environ["HTTPS_REDIRECT"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Now import app modules
from app.database import Base, get_db

# Import main app AFTER setting env vars
from app.main import app as fastapi_app

# Test database configuration - using in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create database session for testing"""
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=test_engine)
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables after each test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # Disable rate limiting in tests
    if hasattr(fastapi_app.state, "limiter") and fastapi_app.state.limiter:
        fastapi_app.state.limiter._default_limits = []

    with TestClient(app=fastapi_app, follow_redirects=False) as c:
        yield c

    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client):
    """Client with proper database setup for auth tests"""
    yield client
