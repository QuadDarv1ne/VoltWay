from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="favorites")
    station = relationship("Station", back_populates="favorited_by")

    # Ensure user can't favorite the same station twice + indexes for performance
    __table_args__ = (
        UniqueConstraint("user_id", "station_id", name="unique_user_station"),
        # Composite index for efficient user favorites lookup
        Index("idx_favorites_user_station", "user_id", "station_id"),
        # Index for counting favorites per station
        Index("idx_favorites_station_count", "station_id"),
    )
