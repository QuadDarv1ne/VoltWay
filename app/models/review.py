"""
Review and Rating models for station feedback.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    station_id = Column(Integer, ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Rating (1-5 stars)
    rating = Column(Integer, nullable=False)
    
    # Review content
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Optional: specific aspect ratings
    cleanliness_rating = Column(Integer, nullable=True)  # 1-5
    safety_rating = Column(Integer, nullable=True)  # 1-5
    accessibility_rating = Column(Integer, nullable=True)  # 1-5
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    is_verified = Column(Integer, default=0)  # 1 = verified visit
    
    # Moderation
    is_approved = Column(Integer, default=1)  # 0 = pending, 1 = approved, -1 = rejected
    is_hidden = Column(Integer, default=0)  # Soft delete
    hidden_reason = Column(String(200), nullable=True)
    
    # Helpfulness tracking
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    # Relationships
    station = relationship("Station", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    photos = relationship("ReviewPhoto", back_populates="review", cascade="all, delete-orphan")
    votes = relationship("ReviewVote", back_populates="review", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_review_station_rating", "station_id", "rating"),
        Index("idx_review_created", "created_at"),
        Index("idx_review_approved", "is_approved", "is_hidden"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_rating_range"),
        CheckConstraint("cleanliness_rating IS NULL OR (cleanliness_rating >= 1 AND cleanliness_rating <= 5)", name="chk_cleanliness_rating"),
        CheckConstraint("safety_rating IS NULL OR (safety_rating >= 1 AND safety_rating <= 5)", name="chk_safety_rating"),
        CheckConstraint("accessibility_rating IS NULL OR (accessibility_rating >= 1 AND accessibility_rating <= 5)", name="chk_accessibility_rating"),
    )
    
    def __repr__(self):
        return f"<Review(id={self.id}, station_id={self.station_id}, rating={self.rating})>"


class ReviewPhoto(Base):
    __tablename__ = "review_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    caption = Column(String(200), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_primary = Column(Integer, default=0)
    
    # Relationships
    review = relationship("Review", back_populates="photos")
    
    def __repr__(self):
        return f"<ReviewPhoto(id={self.id}, review_id={self.review_id})>"


class ReviewVote(Base):
    __tablename__ = "review_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    vote_type = Column(Integer, nullable=False)  # 1 = helpful, -1 = not helpful
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    review = relationship("Review", back_populates="votes")
    
    # Unique constraint to prevent duplicate votes
    __table_args__ = (
        Index("idx_vote_review_user", "review_id", "user_id", unique=True),
    )
    
    def __repr__(self):
        return f"<ReviewVote(id={self.id}, review_id={self.review_id}, type={self.vote_type})>"
