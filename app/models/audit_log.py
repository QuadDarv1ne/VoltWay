"""
Audit Log model for security tracking.

Records all security-relevant actions for compliance and forensics.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
    func,
)

from app.models import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # User information
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(100), nullable=True)

    # Action details
    action = Column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    resource_type = Column(String(50), nullable=False, index=True)  # station, user, api_key
    resource_id = Column(Integer, nullable=True)

    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = Column(String(500), nullable=True)

    # Additional details (JSON as text)
    details = Column(Text, nullable=True)

    # Status
    status_code = Column(Integer, nullable=True)
    is_success = Column(Integer, default=1)  # 1 = success, 0 = failure

    # Indexes for common queries
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_timestamp_action", "timestamp", "action"),
        Index("idx_audit_ip", "ip_address"),
    )

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"resource={self.resource_type}:{self.resource_id}, "
            f"timestamp={self.timestamp})>"
        )
