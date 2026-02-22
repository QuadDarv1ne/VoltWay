"""
Pydantic schemas for API keys.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.api_key import APIKeyRole


class APIKeyCreate(BaseModel):
    """Schema for creating an API key"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    role: APIKeyRole = APIKeyRole.USER
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_period: int = Field(default=60, ge=1, le=3600)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class APIKeyResponse(BaseModel):
    """Schema for API key response (includes the key only once)"""
    id: int
    key: str
    name: str
    description: Optional[str]
    role: str
    rate_limit_requests: int
    rate_limit_period: int
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class APIKeyInfo(BaseModel):
    """Schema for API key info (without the actual key)"""
    id: int
    name: str
    description: Optional[str]
    role: str
    is_active: bool
    rate_limit_requests: int
    rate_limit_period: int
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class APIKeyStats(BaseModel):
    """Schema for API key usage statistics"""
    total_keys: int
    active_keys: int
    expired_keys: int
    by_role: dict[str, int]
