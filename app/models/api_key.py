"""
API Key model for authentication and authorization.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class APIKeyRole(str, Enum):
    """API key roles with different permissions"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class APIKey(Base):
    """API Key model for authentication"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    # Store hashed key for security
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    # First 8 chars of key for identification (not secret)
    key_prefix = Column(String(8), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default=APIKeyRole.USER.value)
    is_active = Column(Boolean, default=True, nullable=False)

    # Rate limiting
    rate_limit_requests = Column(Integer, default=100, nullable=False)
    rate_limit_period = Column(Integer, default=60, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<APIKey(name='{self.name}', role='{self.role}', prefix='{self.key_prefix}')>"

    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()
