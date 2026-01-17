"""
OpenAPI documentation enhancement for VoltWay API.

Provides comprehensive API documentation with examples, error handling,
and detailed descriptions for all endpoints.
"""

from fastapi import FastAPI, APIRouter
from fastapi.openapi.utils import get_openapi
from typing import Any, Dict


def enhance_openapi_documentation(app: FastAPI) -> Dict[str, Any]:
    """
    Enhance OpenAPI documentation with detailed information.

    Args:
        app: FastAPI application instance

    Returns:
        Enhanced OpenAPI schema
    """

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="VoltWay API",
            version="2.0.0",
            description="""
## VoltWay API Documentation

VoltWay is a real-time electric vehicle charging station finder and manager.

### Features:
- 🗺️ Find nearby charging stations
- 📍 Real-time location tracking
- ⭐ Save favorite stations
- 🔔 Get notifications for new stations
- 📊 Advanced analytics and monitoring
- 🔐 Secure authentication

### Base URLs:
- Production: https://api.voltway.com/api
- Staging: https://staging-api.voltway.com/api
- Local: http://localhost:8000/api

### Authentication:
All endpoints except `/auth/login` and `/auth/register` require JWT token.

Include token in header: `Authorization: Bearer <token>`

### Response Format:
All responses follow consistent JSON format:
```json
{
    "data": {...},
    "meta": {
        "timestamp": "2024-01-06T00:00:00Z",
        "version": "1.0.0"
    }
}
```

### Error Handling:
Standard HTTP status codes are used:
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Rate Limited
- 500: Server Error

### Rate Limiting:
- 100 requests per minute per IP
- 1000 requests per hour per user
- 10MB payload size limit

### Monitoring:
- Health check: `GET /health`
- Metrics: `GET /metrics` (Prometheus format)
- Status: `GET /api/v1/health`

### Versioning:
The API supports multiple versions:
- `/api/v1/*` - Stable version (recommended)
- `/api/v2/*` - Latest features (may change)

### Support:
- Documentation: https://docs.voltway.com
- Issues: https://github.com/quaddarv1ne/voltway/issues
- Email: support@voltway.com
        """,
            routes=app.routes,
        )

        # Add tag descriptions
        openapi_schema["tags"] = [
            {
                "name": "stations",
                "description": "Electric charging station management and discovery",
            },
            {
                "name": "favorites",
                "description": "User favorite stations management",
            },
            {
                "name": "auth",
                "description": "Authentication and authorization endpoints",
            },
            {
                "name": "notifications",
                "description": "Push notification management",
            },
            {
                "name": "monitoring",
                "description": "Health checks and metrics monitoring",
            },
            {
                "name": "analytics",
                "description": "Usage analytics and statistics",
            },
        ]

        # Add components/schemas with examples
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}

        # Enhanced schema with examples
        openapi_schema["components"]["schemas"].update(
            {
                "Station": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "name": {"type": "string", "example": "Downtown Charging Hub"},
                        "latitude": {"type": "number", "example": 40.7128},
                        "longitude": {"type": "number", "example": -74.0060},
                        "address": {"type": "string", "example": "123 Main St, NYC"},
                        "available_chargers": {"type": "integer", "example": 5},
                        "total_chargers": {"type": "integer", "example": 10},
                        "last_updated": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-01-06T10:30:00Z",
                        },
                    },
                    "required": [
                        "id",
                        "name",
                        "latitude",
                        "longitude",
                    ],
                },
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "username": {"type": "string", "example": "john_doe"},
                        "email": {"type": "string", "format": "email", "example": "john@example.com"},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-01-01T00:00:00Z",
                        },
                    },
                    "required": ["id", "username", "email"],
                },
                "Favorite": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "user_id": {"type": "integer", "example": 1},
                        "station_id": {"type": "integer", "example": 1},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-01-06T00:00:00Z",
                        },
                    },
                    "required": ["id", "user_id", "station_id"],
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "example": "Resource not found"},
                        "detail": {"type": "string", "example": "Station with id 999 does not exist"},
                        "code": {"type": "string", "example": "STATION_NOT_FOUND"},
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                        },
                    },
                    "required": ["error", "code"],
                },
            }
        )

        # Add security schemes
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "securitySchemes" not in openapi_schema["components"]:
            openapi_schema["components"]["securitySchemes"] = {}

        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained from /api/auth/login",
            }
        }

        # Add server information
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Local development",
            },
            {
                "url": "https://staging-api.voltway.com",
                "description": "Staging environment",
            },
            {
                "url": "https://api.voltway.com",
                "description": "Production environment",
            },
        ]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app.openapi()


def create_endpoint_documentation(
    summary: str,
    description: str,
    tags: list[str],
    examples: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create standardized endpoint documentation.

    Args:
        summary: Brief endpoint summary
        description: Detailed endpoint description
        tags: OpenAPI tags
        examples: Request/response examples

    Returns:
        Documentation dictionary
    """
    return {
        "summary": summary,
        "description": description,
        "tags": tags,
        "examples": examples,
    }


# Endpoint documentation examples

STATION_EXAMPLES = {
    "example": {
        "value": {
            "id": 1,
            "name": "Downtown Charging Hub",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St, New York, NY",
            "available_chargers": 5,
            "total_chargers": 10,
            "last_updated": "2024-01-06T10:30:00Z",
            "distance_km": 2.5,
            "amenities": ["WiFi", "Restroom", "Cafe"],
        }
    }
}

USER_EXAMPLES = {
    "example": {
        "value": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "profile": {
                "first_name": "John",
                "last_name": "Doe",
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-06T10:00:00Z",
        }
    }
}

ERROR_EXAMPLES = {
    "not_found": {
        "value": {
            "error": "Not Found",
            "detail": "Station with id 999 does not exist",
            "code": "STATION_NOT_FOUND",
            "timestamp": "2024-01-06T10:00:00Z",
        }
    },
    "unauthorized": {
        "value": {
            "error": "Unauthorized",
            "detail": "Missing or invalid authentication token",
            "code": "UNAUTHORIZED",
            "timestamp": "2024-01-06T10:00:00Z",
        }
    },
    "rate_limited": {
        "value": {
            "error": "Too Many Requests",
            "detail": "Rate limit exceeded: 100 requests per minute",
            "code": "RATE_LIMITED",
            "timestamp": "2024-01-06T10:00:00Z",
            "retry_after": 60,
        }
    },
}

# Endpoint documentation templates

STATION_LIST_DOCS = create_endpoint_documentation(
    summary="Get nearby charging stations",
    description="""
    Retrieve a list of electric charging stations near the given coordinates.

    ### Parameters:
    - **latitude**: Your current latitude (-90 to 90)
    - **longitude**: Your current longitude (-180 to 180)
    - **radius_km**: Search radius in kilometers (default: 10, max: 100)
    - **available_only**: Show only stations with available chargers
    - **sort_by**: Sort results by 'distance' or 'available' (default: 'distance')

    ### Response:
    Returns an array of stations sorted by relevance.

    ### Errors:
    - 400: Invalid coordinates or parameters
    - 429: Rate limited
    - 500: Server error
    """,
    tags=["stations"],
    examples=STATION_EXAMPLES,
)

STATION_DETAIL_DOCS = create_endpoint_documentation(
    summary="Get station details",
    description="""
    Retrieve detailed information about a specific charging station.

    ### Response:
    Includes full station details, real-time charger availability,
    recent reviews, and operating hours.

    ### Errors:
    - 404: Station not found
    - 500: Server error
    """,
    tags=["stations"],
    examples=STATION_EXAMPLES,
)

FAVORITES_LIST_DOCS = create_endpoint_documentation(
    summary="Get user favorite stations",
    description="""
    Retrieve list of stations saved as favorites by the authenticated user.

    ### Authentication: Required (Bearer token)

    ### Response:
    Array of stations marked as favorites with additional metadata.

    ### Errors:
    - 401: Unauthorized (missing/invalid token)
    - 500: Server error
    """,
    tags=["favorites"],
    examples=STATION_EXAMPLES,
)

__all__ = [
    "enhance_openapi_documentation",
    "create_endpoint_documentation",
    "STATION_EXAMPLES",
    "USER_EXAMPLES",
    "ERROR_EXAMPLES",
    "STATION_LIST_DOCS",
    "STATION_DETAIL_DOCS",
    "FAVORITES_LIST_DOCS",
]
