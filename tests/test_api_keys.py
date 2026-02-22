"""
Tests for API key authentication and management.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.crud.api_key import create_api_key, get_api_key_by_key, deactivate_api_key
from app.models.api_key import APIKeyRole


@pytest.mark.asyncio
async def test_create_api_key(db):
    """Test creating an API key"""
    api_key = await create_api_key(
        db=db,
        name="Test Key",
        role=APIKeyRole.USER,
        description="Test description",
    )
    
    assert api_key.id is not None
    assert api_key.name == "Test Key"
    assert api_key.role == APIKeyRole.USER.value
    assert api_key.is_active is True
    assert len(api_key.key) > 32  # Should be a secure random key


@pytest.mark.asyncio
async def test_get_api_key_by_key(db):
    """Test retrieving API key by key string"""
    # Create a key
    created_key = await create_api_key(
        db=db,
        name="Test Key",
        role=APIKeyRole.USER,
    )
    
    # Retrieve it
    retrieved_key = await get_api_key_by_key(db, created_key.key)
    
    assert retrieved_key is not None
    assert retrieved_key.id == created_key.id
    assert retrieved_key.key == created_key.key


@pytest.mark.asyncio
async def test_api_key_expiration(db):
    """Test API key expiration"""
    # Create expired key
    api_key = await create_api_key(
        db=db,
        name="Expired Key",
        role=APIKeyRole.USER,
        expires_in_days=-1,  # Already expired
    )
    
    assert api_key.is_expired() is True
    assert api_key.is_valid() is False
    
    # Create valid key
    valid_key = await create_api_key(
        db=db,
        name="Valid Key",
        role=APIKeyRole.USER,
        expires_in_days=30,
    )
    
    assert valid_key.is_expired() is False
    assert valid_key.is_valid() is True


@pytest.mark.asyncio
async def test_deactivate_api_key(db):
    """Test deactivating an API key"""
    # Create a key
    api_key = await create_api_key(
        db=db,
        name="Test Key",
        role=APIKeyRole.USER,
    )
    
    assert api_key.is_active is True
    
    # Deactivate it
    success = await deactivate_api_key(db, api_key.id)
    assert success is True
    
    # Verify it's deactivated
    retrieved_key = await get_api_key_by_key(db, api_key.key)
    assert retrieved_key.is_active is False
    assert retrieved_key.is_valid() is False


@pytest.mark.asyncio
async def test_admin_endpoint_requires_auth(client: AsyncClient):
    """Test that admin endpoints require authentication"""
    response = await client.get("/api/v1/admin/cache/stats")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_with_invalid_key(client: AsyncClient):
    """Test admin endpoint with invalid API key"""
    response = await client.get(
        "/api/v1/admin/cache/stats",
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_with_user_key(client: AsyncClient, db):
    """Test that user role cannot access admin endpoints"""
    # Create user key
    user_key = await create_api_key(
        db=db,
        name="User Key",
        role=APIKeyRole.USER,
    )
    
    response = await client.get(
        "/api/v1/admin/cache/stats",
        headers={"X-API-Key": user_key.key}
    )
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_admin_endpoint_with_admin_key(client: AsyncClient, db):
    """Test admin endpoint with valid admin key"""
    # Create admin key
    admin_key = await create_api_key(
        db=db,
        name="Admin Key",
        role=APIKeyRole.ADMIN,
    )
    
    response = await client.get(
        "/api/v1/admin/cache/stats",
        headers={"X-API-Key": admin_key.key}
    )
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data or "misses" in data


@pytest.mark.asyncio
async def test_create_api_key_endpoint(client: AsyncClient, db):
    """Test creating API key via endpoint"""
    # Create admin key first
    admin_key = await create_api_key(
        db=db,
        name="Admin Key",
        role=APIKeyRole.ADMIN,
    )
    
    # Create new key via API
    response = await client.post(
        "/api/v1/admin/api-keys",
        headers={"X-API-Key": admin_key.key},
        json={
            "name": "New App Key",
            "role": "user",
            "description": "Test app",
            "rate_limit_requests": 200,
            "rate_limit_period": 60,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New App Key"
    assert data["role"] == "user"
    assert "key" in data  # Key should be returned once


@pytest.mark.asyncio
async def test_list_api_keys_endpoint(client: AsyncClient, db):
    """Test listing API keys via endpoint"""
    # Create admin key
    admin_key = await create_api_key(
        db=db,
        name="Admin Key",
        role=APIKeyRole.ADMIN,
    )
    
    # Create some test keys
    await create_api_key(db=db, name="Key 1", role=APIKeyRole.USER)
    await create_api_key(db=db, name="Key 2", role=APIKeyRole.USER)
    
    # List keys
    response = await client.get(
        "/api/v1/admin/api-keys",
        headers={"X-API-Key": admin_key.key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # At least our 3 keys


@pytest.mark.asyncio
async def test_api_key_stats_endpoint(client: AsyncClient, db):
    """Test API key statistics endpoint"""
    # Create admin key
    admin_key = await create_api_key(
        db=db,
        name="Admin Key",
        role=APIKeyRole.ADMIN,
    )
    
    # Create test keys
    await create_api_key(db=db, name="User 1", role=APIKeyRole.USER)
    await create_api_key(db=db, name="User 2", role=APIKeyRole.USER)
    await create_api_key(db=db, name="ReadOnly", role=APIKeyRole.READONLY)
    
    # Get stats
    response = await client.get(
        "/api/v1/admin/api-keys/stats",
        headers={"X-API-Key": admin_key.key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_keys" in data
    assert "active_keys" in data
    assert "by_role" in data
    assert data["total_keys"] >= 4


@pytest.mark.asyncio
async def test_deactivate_api_key_endpoint(client: AsyncClient, db):
    """Test deactivating API key via endpoint"""
    # Create admin key
    admin_key = await create_api_key(
        db=db,
        name="Admin Key",
        role=APIKeyRole.ADMIN,
    )
    
    # Create key to deactivate
    target_key = await create_api_key(
        db=db,
        name="To Deactivate",
        role=APIKeyRole.USER,
    )
    
    # Deactivate it
    response = await client.delete(
        f"/api/v1/admin/api-keys/{target_key.id}",
        headers={"X-API-Key": admin_key.key}
    )
    
    assert response.status_code == 200
    
    # Verify it's deactivated
    retrieved = await get_api_key_by_key(db, target_key.key)
    assert retrieved.is_active is False


@pytest.mark.asyncio
async def test_expired_key_rejected(client: AsyncClient, db):
    """Test that expired keys are rejected"""
    # Create expired admin key
    expired_key = await create_api_key(
        db=db,
        name="Expired Admin",
        role=APIKeyRole.ADMIN,
        expires_in_days=-1,
    )
    
    # Try to use it
    response = await client.get(
        "/api/v1/admin/cache/stats",
        headers={"X-API-Key": expired_key.key}
    )
    
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_inactive_key_rejected(client: AsyncClient, db):
    """Test that inactive keys are rejected"""
    # Create and deactivate key
    api_key = await create_api_key(
        db=db,
        name="Admin Key",
        role=APIKeyRole.ADMIN,
    )
    await deactivate_api_key(db, api_key.id)
    
    # Try to use it
    response = await client.get(
        "/api/v1/admin/cache/stats",
        headers={"X-API-Key": api_key.key}
    )
    
    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()
