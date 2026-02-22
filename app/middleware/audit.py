"""
Audit logging middleware.

Logs all security-relevant requests to the audit_logs table.
"""

import json
import logging
from datetime import datetime
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import AsyncSessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


# Actions to audit
AUDIT_ACTIONS = {
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "UPDATE",
    "DELETE": "DELETE",
    "POST /auth": "AUTH",
    "DELETE /api-keys": "API_KEY_REVOKE",
    "POST /api-keys": "API_KEY_CREATE",
}

# Resource types to audit
AUDIT_RESOURCES = {
    "/stations": "station",
    "/users": "user",
    "/api-keys": "api_key",
    "/auth": "authentication",
    "/favorites": "favorite",
}


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log security-relevant actions"""

    def __init__(
        self,
        app,
        # Paths to exclude from audit logging
        exclude_paths: Optional[list] = None,
        # Only audit these HTTP methods
        audit_methods: Optional[list] = None,
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/ws",
        ]
        self.audit_methods = audit_methods or ["POST", "PUT", "PATCH", "DELETE"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log audit entry for security-relevant requests"""
        # Check if request should be audited
        should_audit = self._should_audit_request(request)

        if not should_audit:
            return await call_next(request)

        # Capture request start time
        start_time = datetime.utcnow()

        # Extract request information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method

        # Try to get user info from state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)
        api_key_id = getattr(request.state, "api_key_id", None)

        # Determine action and resource type
        action = self._determine_action(method, path)
        resource_type = self._determine_resource_type(path)

        # Process request
        response = await call_next(request)

        # Log audit entry (fire and forget)
        try:
            async with AsyncSessionLocal() as db:
                audit_log = AuditLog(
                    timestamp=start_time,
                    user_id=user_id or api_key_id,
                    username=username,
                    action=action,
                    resource_type=resource_type,
                    ip_address=client_ip,
                    user_agent=user_agent[:500],
                    request_method=method,
                    request_path=path,
                    status_code=response.status_code,
                    is_success=1 if response.status_code < 400 else 0,
                )

                # Try to extract resource ID from path
                resource_id = self._extract_resource_id(path)
                if resource_id:
                    audit_log.resource_id = resource_id

                db.add(audit_log)
                await db.commit()

        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"Audit logging failed: {e}")

        return response

    def _should_audit_request(self, request: Request) -> bool:
        """Check if request should be audited"""
        path = request.url.path
        method = request.method

        # Skip excluded paths
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False

        # Only audit specific methods
        if method not in self.audit_methods:
            return False

        return True

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _determine_action(self, method: str, path: str) -> str:
        """Determine audit action from request"""
        # Check for specific path patterns
        for pattern, action in AUDIT_ACTIONS.items():
            if pattern.startswith("/"):
                if path.startswith(pattern):
                    return action
            else:
                if method == pattern:
                    return action

        # Default to method-based action
        return AUDIT_ACTIONS.get(method, method)

    def _determine_resource_type(self, path: str) -> str:
        """Determine resource type from path"""
        for path_pattern, resource_type in AUDIT_RESOURCES.items():
            if path.startswith(f"/api{path_pattern}") or path.startswith(path_pattern):
                return resource_type

        return "unknown"

    def _extract_resource_id(self, path: str) -> Optional[int]:
        """Extract resource ID from path"""
        # Try to find numeric ID in path
        parts = path.split("/")
        for part in parts:
            if part.isdigit():
                return int(part)
        return None


def create_audit_middleware(
    exclude_paths: Optional[list] = None,
    audit_methods: Optional[list] = None,
) -> AuditLoggingMiddleware:
    """
    Factory function to create audit logging middleware.

    Args:
        exclude_paths: Additional paths to exclude from auditing
        audit_methods: HTTP methods to audit

    Returns:
        AuditLoggingMiddleware instance
    """
    return AuditLoggingMiddleware(
        app=None,  # Will be set by FastAPI
        exclude_paths=exclude_paths,
        audit_methods=audit_methods,
    )
