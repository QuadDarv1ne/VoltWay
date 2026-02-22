"""
GraphQL types for VoltWay API v3.

Defines Strawberry types for stations, users, and other entities.
"""

import strawberry
from datetime import datetime
from typing import List, Optional
from enum import Enum


@strawberry.enum
class StationStatus(Enum):
    """Station status enum"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


@strawberry.type
class Station:
    """Charging station type"""
    id: int
    title: str
    address: str
    latitude: float
    longitude: float
    connector_type: str
    power_kw: float
    status: StationStatus
    price: Optional[float] = None
    hours: Optional[str] = None
    last_updated: datetime
    distance_km: Optional[float] = None

    @strawberry.field
    def is_favorite(self, info: strawberry.Info) -> bool:
        """Check if station is in user's favorites"""
        # Implementation would check user's favorites
        return False


@strawberry.type
class StationConnection:
    """Paginated station connection"""
    stations: List[Station]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


@strawberry.type
class ConnectorType:
    """Connector type statistics"""
    name: str
    count: int
    avg_power_kw: float


@strawberry.type
class StationStats:
    """Station statistics"""
    total_stations: int
    available_stations: int
    occupied_stations: int
    maintenance_stations: int
    unknown_stations: int
    avg_power_kw: float
    connector_types: List[ConnectorType]


@strawberry.type
class User:
    """User type"""
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@strawberry.type
class FavoriteStation:
    """Favorite station"""
    id: int
    user_id: int
    station: Station
    created_at: datetime
    notes: Optional[str] = None


@strawberry.type
class SearchResult:
    """Search result with stations and metadata"""
    stations: List[Station]
    total: int
    query: str
    search_type: str  # "fulltext" or "geospatial"


@strawberry.input
class StationFilter:
    """Input filter for station queries"""
    connector_type: Optional[str] = None
    min_power_kw: Optional[float] = None
    max_power_kw: Optional[float] = None
    status: Optional[StationStatus] = None
    has_price: Optional[bool] = None


@strawberry.input
class LocationInput:
    """Location input for geospatial queries"""
    latitude: float
    longitude: float
    radius_km: float = 10.0


@strawberry.input
class CreateStationInput:
    """Input for creating a station"""
    title: str
    address: str
    latitude: float
    longitude: float
    connector_type: str
    power_kw: float
    status: StationStatus = StationStatus.UNKNOWN
    price: Optional[float] = None
    hours: Optional[str] = None


@strawberry.input
class UpdateStationInput:
    """Input for updating a station"""
    title: Optional[str] = None
    address: Optional[str] = None
    connector_type: Optional[str] = None
    power_kw: Optional[float] = None
    status: Optional[StationStatus] = None
    price: Optional[float] = None
    hours: Optional[str] = None


@strawberry.type
class Message:
    """Generic message response"""
    success: bool
    message: str


@strawberry.type
class AuditLog:
    """Audit log entry"""
    id: int
    timestamp: datetime
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
