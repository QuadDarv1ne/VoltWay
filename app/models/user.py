from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    favorites = relationship(
        "Favorite", back_populates="user", cascade="all, delete-orphan"
    )

    # Composite indexes for optimized queries
    __table_args__ = (
        # Index for active users lookup
        Index("idx_users_active", "is_active"),
        # Index for admin users lookup
        Index("idx_users_admin", "is_admin"),
        # Composite index for active users by creation date (common query pattern)
        Index("idx_users_active_created", "is_active", "created_at"),
    )
