"""
Reviews and Ratings API endpoints.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.models.review import Review, ReviewPhoto, ReviewVote
from app.models.station import Station
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    Review,
    ReviewWithUser,
    ReviewListResponse,
    ReviewStats,
    ReviewPhotoCreate,
    ReviewPhoto,
    ReviewVoteCreate,
)
from app.core.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/station/{station_id}", response_model=ReviewListResponse)
async def get_station_reviews(
    station_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    sort_by: str = Query("created_at", regex="^(created_at|rating|helpful)$"),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get all reviews for a station with pagination.
    
    - **station_id**: ID of the station
    - **page**: Page number (1-indexed)
    - **page_size**: Items per page (1-50)
    - **sort_by**: Sort field (created_at, rating, helpful)
    - **min_rating**: Filter by minimum rating
    """
    # Calculate offset
    skip = (page - 1) * page_size
    
    # Build query - only approved and visible reviews
    query = select(Review).where(
        and_(
            Review.station_id == station_id,
            Review.is_approved == 1,
            Review.is_hidden == 0,
        )
    )
    
    # Apply rating filter
    if min_rating:
        query = query.where(Review.rating >= min_rating)
    
    # Get total count
    count_query = select(func.count()).select_from(Review).where(
        and_(
            Review.station_id == station_id,
            Review.is_approved == 1,
            Review.is_hidden == 0,
        )
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    if sort_by == "rating":
        query = query.order_by(Review.rating.desc())
    elif sort_by == "helpful":
        query = query.order_by((Review.helpful_count - Review.not_helpful_count).desc())
    else:
        query = query.order_by(Review.created_at.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(page_size)
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    # Get average rating
    avg_query = select(func.avg(Review.rating)).where(
        and_(
            Review.station_id == station_id,
            Review.is_approved == 1,
            Review.is_hidden == 0,
        )
    )
    avg_result = await db.execute(avg_query)
    average_rating = float(avg_result.scalar() or 0)
    
    return ReviewListResponse(
        items=[Review.model_validate(r) for r in reviews],
        total=total,
        average_rating=round(average_rating, 2),
        page=page,
        page_size=page_size,
        has_next=skip + page_size < total,
        has_prev=page > 1,
    )


@router.post("/station/{station_id}", response_model=Review, status_code=status.HTTP_201_CREATED)
async def create_review(
    station_id: int,
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    # TODO: Add user authentication
    # user: User = Depends(get_current_user),
):
    """
    Create a new review for a station.
    
    - **station_id**: ID of the station to review
    - **rating**: Rating from 1 to 5
    - **title**: Optional review title
    - **comment**: Review text
    """
    # Verify station exists
    station_result = await db.execute(select(Station).where(Station.id == station_id))
    station = station_result.scalar_one_or_none()
    
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    # Check for duplicate review (if user authentication is enabled)
    # if user:
    #     existing = await db.execute(
    #         select(Review).where(
    #             Review.station_id == station_id,
    #             Review.user_id == user.id
    #         )
    #     )
    #     if existing.scalar_one_or_none():
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="You have already reviewed this station"
    #         )
    
    # Create review
    review = Review(
        station_id=station_id,
        # user_id=user.id if user else None,
        **review_data.model_dump(exclude={'station_id', 'is_verified'}),
        is_verified=1 if review_data.is_verified else 0,
    )
    
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    logger.info(f"Review created for station {station_id}")
    
    return review


@router.get("/{review_id}", response_model=ReviewWithUser)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific review by ID"""
    result = await db.execute(
        select(Review).where(
            and_(
                Review.id == review_id,
                Review.is_approved == 1,
                Review.is_hidden == 0,
            )
        )
    )
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    
    return review


@router.put("/{review_id}", response_model=Review)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: AsyncSession = Depends(get_async_db),
    # TODO: Add user authentication and ownership check
):
    """
    Update an existing review.
    
    Only the review author or admin can update.
    """
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    
    # Update fields
    update_data = review_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    review.updated_at = func.now()
    
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_async_db),
    # TODO: Add user authentication and ownership check
):
    """
    Delete a review (soft delete).
    
    Only the review author or admin can delete.
    """
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    
    # Soft delete
    review.is_hidden = 1
    await db.commit()
    
    logger.info(f"Review {review_id} deleted")


@router.post("/{review_id}/photos", response_model=ReviewPhoto, status_code=status.HTTP_201_CREATED)
async def add_review_photo(
    review_id: int,
    photo_data: ReviewPhotoCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Add a photo to a review"""
    # Verify review exists
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    
    photo = ReviewPhoto(**photo_data.model_dump())
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    
    return photo


@router.post("/{review_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote_review(
    review_id: int,
    vote_data: ReviewVoteCreate,
    db: AsyncSession = Depends(get_async_db),
    # TODO: Add user authentication
):
    """
    Vote on a review (helpful/not helpful).
    
    - **vote_type**: 1 for helpful, -1 for not helpful
    """
    # Verify review exists
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    
    # Check for existing vote
    # if user:
    #     existing = await db.execute(
    #         select(ReviewVote).where(
    #             ReviewVote.review_id == review_id,
    #             ReviewVote.user_id == user.id
    #         )
    #     )
    #     if existing.scalar_one_or_none():
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="You have already voted on this review"
    #         )
    
    # Create vote
    vote = ReviewVote(
        review_id=review_id,
        # user_id=user.id if user else None,
        vote_type=vote_data.vote_type,
    )
    db.add(vote)
    
    # Update vote counts
    if vote_data.vote_type == 1:
        review.helpful_count += 1
    else:
        review.not_helpful_count += 1
    
    await db.commit()
    
    logger.info(f"Vote added to review {review_id}")


@router.get("/station/{station_id}/stats", response_model=ReviewStats)
async def get_review_stats(
    station_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get review statistics for a station"""
    # Total reviews
    total_query = select(func.count()).where(
        and_(
            Review.station_id == station_id,
            Review.is_approved == 1,
            Review.is_hidden == 0,
        )
    )
    total_result = await db.execute(total_query.select())
    total = total_result.scalar() or 0
    
    # Average rating
    avg_query = select(func.avg(Review.rating)).where(
        and_(
            Review.station_id == station_id,
            Review.is_approved == 1,
            Review.is_hidden == 0,
        )
    )
    avg_result = await db.execute(avg_query)
    average_rating = float(avg_result.scalar() or 0)
    
    # Rating distribution
    distribution = {}
    for rating in range(1, 6):
        count_query = select(func.count()).where(
            and_(
                Review.station_id == station_id,
                Review.rating == rating,
                Review.is_approved == 1,
                Review.is_hidden == 0,
            )
        )
        count_result = await db.execute(count_query.select())
        distribution[rating] = count_result.scalar() or 0
    
    # Recommended percentage (4-5 stars)
    recommended_query = select(func.count()).where(
        and_(
            Review.station_id == station_id,
            Review.rating >= 4,
            Review.is_approved == 1,
            Review.is_hidden == 0,
        )
    )
    recommended_result = await db.execute(recommended_query.select())
    recommended = recommended_result.scalar() or 0
    
    recommended_percentage = (recommended / total * 100) if total > 0 else 0
    
    return ReviewStats(
        total_reviews=total,
        average_rating=round(average_rating, 2),
        rating_distribution=distribution,
        recommended_percentage=round(recommended_percentage, 1),
    )
