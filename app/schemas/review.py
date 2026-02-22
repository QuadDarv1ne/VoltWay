"""
Pydantic schemas for reviews and ratings.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ReviewBase(BaseModel):
    """Base review schema"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    safety_rating: Optional[int] = Field(None, ge=1, le=5)
    accessibility_rating: Optional[int] = Field(None, ge=1, le=5)


class ReviewCreate(ReviewBase):
    """Schema for creating a review"""
    station_id: int
    is_verified: Optional[bool] = False


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    safety_rating: Optional[int] = Field(None, ge=1, le=5)
    accessibility_rating: Optional[int] = Field(None, ge=1, le=5)


class ReviewPhotoBase(BaseModel):
    """Base review photo schema"""
    photo_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = Field(None, max_length=200)


class ReviewPhotoCreate(ReviewPhotoBase):
    """Schema for creating a review photo"""
    review_id: int
    is_primary: Optional[bool] = False


class ReviewPhoto(ReviewPhotoBase):
    """Review photo schema"""
    id: int
    review_id: int
    uploaded_at: datetime
    
    model_config = {"from_attributes": True}


class ReviewVoteBase(BaseModel):
    """Base review vote schema"""
    vote_type: int  # 1 = helpful, -1 = not helpful


class ReviewVoteCreate(ReviewVoteBase):
    """Schema for creating a vote"""
    review_id: int


class Review(ReviewBase):
    """Full review schema"""
    id: int
    station_id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_verified: bool
    is_approved: bool
    is_hidden: bool
    helpful_count: int
    not_helpful_count: int
    photos: List[ReviewPhoto] = []
    
    model_config = {"from_attributes": True}


class ReviewWithUser(Review):
    """Review with user information"""
    username: Optional[str] = None


class ReviewStats(BaseModel):
    """Review statistics for a station"""
    total_reviews: int
    average_rating: float
    rating_distribution: dict  # {1: count, 2: count, ...}
    recommended_percentage: float  # Percentage of 4-5 star reviews


class ReviewListResponse(BaseModel):
    """Paginated review list response"""
    items: List[Review]
    total: int
    average_rating: float
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
