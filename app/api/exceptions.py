"""Custom exceptions for VoltWay API"""

from typing import Any, Optional


class VoltWayException(Exception):
    """Base exception for all VoltWay errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class StationNotFoundError(VoltWayException):
    """Raised when a station is not found"""

    def __init__(self, station_id: int):
        super().__init__(
            message=f"Station with id {station_id} not found",
            error_code="STATION_NOT_FOUND",
            status_code=404,
            details={"station_id": station_id},
        )


class InvalidFilterError(VoltWayException):
    """Raised when filters are invalid"""

    def __init__(self, message: str, invalid_filters: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INVALID_FILTER",
            status_code=400,
            details={"invalid_filters": invalid_filters or {}},
        )


class ExternalAPIError(VoltWayException):
    """Raised when external API call fails"""

    def __init__(self, api_name: str, reason: str):
        super().__init__(
            message=f"Failed to call {api_name}: {reason}",
            error_code="EXTERNAL_API_ERROR",
            status_code=502,
            details={"api_name": api_name, "reason": reason},
        )


class CacheError(VoltWayException):
    """Raised when cache operation fails"""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Cache {operation} failed: {reason}",
            error_code="CACHE_ERROR",
            status_code=500,
            details={"operation": operation, "reason": reason},
        )


class DatabaseError(VoltWayException):
    """Raised when database operation fails"""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database {operation} failed: {reason}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation, "reason": reason},
        )


class AuthenticationError(VoltWayException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(VoltWayException):
    """Raised when user is not authorized to perform action"""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class RateLimitError(VoltWayException):
    """Raised when rate limit is exceeded"""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after},
        )


class ValidationError(VoltWayException):
    """Raised when data validation fails"""

    def __init__(self, message: str, fields: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"fields": fields or {}},
        )
