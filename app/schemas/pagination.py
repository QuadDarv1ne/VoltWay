"""
Paginated response schemas for API endpoints.

Provides standardized pagination metadata across all list endpoints.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationInfo(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., description="Current page number (0-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")

    @classmethod
    def create(
        cls,
        *,
        skip: int,
        limit: int,
        total: int,
    ) -> "PaginationInfo":
        """
        Create pagination info from query parameters.

        Args:
            skip: Number of items skipped (page * page_size)
            limit: Page size (items per page)
            total: Total number of items

        Returns:
            PaginationInfo instance
        """
        page = skip // limit if limit > 0 else 0
        page_size = limit
        total_pages = (total + limit - 1) // limit if limit > 0 else 0

        has_next = skip + limit < total
        has_prev = skip > 0

        return cls(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            next_page=page + 1 if has_next else None,
            prev_page=page - 1 if has_prev else None,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Usage:
        @router.get("/items", response_model=PaginatedResponse[ItemSchema])
        async def get_items():
            items = [...]
            total = 100
            return PaginatedResponse(
                items=items,
                pagination=PaginationInfo.create(skip=0, limit=20, total=total)
            )
    """

    items: List[T] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "pagination": {
                    "page": 0,
                    "page_size": 20,
                    "total_items": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False,
                    "next_page": 1,
                    "prev_page": None,
                },
            }
        }
    }


class ListResponse(BaseModel, Generic[T]):
    """Simple list response (backward compatibility)"""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")


class StatsResponse(BaseModel):
    """Statistics response for dashboard"""

    total_stations: int = Field(..., description="Total stations")
    available_stations: int = Field(..., description="Available stations")
    occupied_stations: int = Field(..., description="Occupied stations")
    maintenance_stations: int = Field(..., description="Maintenance stations")
    unknown_stations: int = Field(..., description="Unknown status stations")
    avg_power_kw: float = Field(..., description="Average power in kW")
    connector_types: Dict[str, int] = Field(
        ..., description="Count by connector type"
    )


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    service: str = Field(..., description="Service name")
    checks: Optional[Dict[str, Any]] = Field(None, description="Detailed health checks")
