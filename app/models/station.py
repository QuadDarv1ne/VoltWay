from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.sql import func

from . import Base


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    connector_type = Column(String(50), nullable=False)  # CCS, CHAdeMO, Type 2
    power_kw = Column(Float, nullable=False)
    status = Column(
        String(20), nullable=False
    )  # available, occupied, maintenance, unknown
    price = Column(Float, nullable=True)
    hours = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add check constraints
    __table_args__ = (
        Index(
            "idx_station_location", "latitude", "longitude"
        ),  # Index for location-based queries
        Index(
            "idx_station_connector", "connector_type"
        ),  # Index for connector type filtering
        Index("idx_station_status", "status"),  # Index for status filtering
        Index("idx_station_power", "power_kw"),  # Index for power filtering
    )
