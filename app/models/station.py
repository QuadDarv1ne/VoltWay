from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    connector_type = Column(String(50), nullable=False)  # CCS, CHAdeMO, Type 2
    power_kw = Column(Float, nullable=False)
    status = Column(
        String(20), nullable=False
    )  # available, occupied, maintenance, unknown
    price = Column(Float, nullable=True)
    hours = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    favorited_by = relationship(
        "Favorite", back_populates="station", cascade="all, delete-orphan"
    )

    # Composite indexes for optimized queries
    __table_args__ = (
        # Location-based queries (geospatial search)
        Index("idx_station_location", "latitude", "longitude"),
        # Combined index for location + status filtering
        Index("idx_station_location_status", "latitude", "longitude", "status"),
        # Connector type filtering
        Index("idx_station_connector", "connector_type"),
        # Status filtering
        Index("idx_station_status", "status"),
        # Power filtering
        Index("idx_station_power", "power_kw"),
        # Combined index for connector + status (common filter combination)
        Index("idx_station_connector_status", "connector_type", "status"),
        # Check constraints for data validation
        CheckConstraint("power_kw > 0", name="chk_power_positive"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="chk_latitude_range"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="chk_longitude_range"
        ),
        CheckConstraint(
            "status IN ('available', 'occupied', 'maintenance', 'unknown')",
            name="chk_status_valid",
        ),
    )

    def distance_to(self, lat: float, lon: float) -> float:
        """
        Calculate distance from this station to a point.

        Args:
            lat: Latitude of target point
            lon: Longitude of target point

        Returns:
            Distance in kilometers
        """
        from app.utils.geo import haversine_distance
        return haversine_distance(self.latitude, self.longitude, lat, lon)
