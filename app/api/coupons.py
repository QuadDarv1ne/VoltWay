"""
Coupons API endpoints.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.models.coupon import Coupon, CouponRedemption, DiscountType
from app.models.reservation import Reservation
from app.core.dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.get("/", response_model=List[dict])
async def get_all_coupons(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    # admin: APIKey = Depends(require_admin),
):
    """Get all coupons (admin only)"""
    query = select(Coupon)
    
    if is_active is not None:
        query = query.where(Coupon.is_active == int(is_active))
    
    query = query.order_by(Coupon.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    coupons = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "code": c.code,
            "discount_type": c.discount_type,
            "discount_value": c.discount_value,
            "max_discount": c.max_discount,
            "used_count": c.used_count,
            "max_uses": c.max_uses,
            "is_active": bool(c.is_active),
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
        }
        for c in coupons
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_coupon(
    code: str = Query(..., min_length=3, max_length=50),
    discount_type: DiscountType = Query(DiscountType.PERCENTAGE),
    discount_value: float = Query(..., gt=0),
    max_discount: Optional[float] = Query(None, gt=0),
    max_uses: Optional[int] = Query(None, gt=0),
    max_uses_per_user: int = Query(1, gt=0),
    valid_until: Optional[datetime] = Query(None),
    min_reservation_cost: Optional[float] = Query(None, gt=0),
    description: Optional[str] = Query(None, max_length=500),
    db: AsyncSession = Depends(get_async_db),
    # admin: APIKey = Depends(require_admin),
):
    """Create a new coupon (admin only)"""
    # Check if code already exists
    existing = await db.execute(select(Coupon).where(Coupon.code == code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code already exists",
        )
    
    coupon = Coupon(
        code=code.upper(),
        discount_type=discount_type.value,
        discount_value=discount_value,
        max_discount=max_discount,
        max_uses=max_uses,
        max_uses_per_user=max_uses_per_user,
        valid_until=valid_until,
        min_reservation_cost=min_reservation_cost,
        description=description,
        is_active=1,
    )
    
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    
    logger.info(f"Coupon created: {code}")
    
    return {
        "id": coupon.id,
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "message": f"Coupon {code} created successfully",
    }


@router.post("/validate")
async def validate_coupon(
    code: str,
    reservation_cost: float,
    duration_minutes: int = Query(60, gt=0),
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Validate coupon and calculate discount"""
    coupon_result = await db.execute(
        select(Coupon).where(
            and_(
                Coupon.code == code.upper(),
                Coupon.is_active == 1,
            )
        )
    )
    coupon = coupon_result.scalar_one_or_none()
    
    if not coupon:
        return {
            "valid": False,
            "error": "Coupon not found",
        }
    
    if not coupon.is_valid():
        return {
            "valid": False,
            "error": "Coupon is not valid",
        }
    
    # Check user-specific usage
    if user_id and coupon.max_uses_per_user:
        user_usage = await db.execute(
            select(func.count()).where(
                and_(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.user_id == user_id,
                )
            )
        )
        usage_count = user_usage.scalar() or 0
        if usage_count >= coupon.max_uses_per_user:
            return {
                "valid": False,
                "error": "Coupon usage limit per user exceeded",
            }
    
    # Calculate discount
    discount = coupon.calculate_discount(reservation_cost, duration_minutes)
    
    return {
        "valid": True,
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_amount": discount,
        "original_cost": reservation_cost,
        "final_cost": round(reservation_cost - discount, 2),
    }


@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_async_db),
    # admin: APIKey = Depends(require_admin),
):
    """Delete/deactivate a coupon (admin only)"""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        )
    
    # Soft delete
    coupon.is_active = 0
    await db.commit()
    
    logger.info(f"Coupon deactivated: {coupon_id}")


@router.get("/stats/{coupon_id}")
async def get_coupon_stats(
    coupon_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get coupon usage statistics"""
    coupon_result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = coupon_result.scalar_one_or_none()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        )
    
    # Total redemptions
    total_query = select(func.count()).where(CouponRedemption.coupon_id == coupon_id)
    total_result = await db.execute(total_query.select())
    total_redemptions = total_result.scalar() or 0
    
    # Total discount given
    discount_query = select(func.sum(CouponRedemption.discount_amount)).where(
        CouponRedemption.coupon_id == coupon_id
    )
    discount_result = await db.execute(discount_query)
    total_discount = float(discount_result.scalar() or 0)
    
    # Revenue generated
    revenue_query = select(func.sum(CouponRedemption.final_cost)).where(
        CouponRedemption.coupon_id == coupon_id
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = float(revenue_result.scalar() or 0)
    
    # Unique users
    users_query = select(func.count(func.distinct(CouponRedemption.user_id))).where(
        CouponRedemption.coupon_id == coupon_id
    )
    users_result = await db.execute(users_query.select())
    unique_users = users_result.scalar() or 0
    
    return {
        "coupon_code": coupon.code,
        "total_redemptions": total_redemptions,
        "total_discount_given": round(total_discount, 2),
        "total_revenue": round(total_revenue, 2),
        "unique_users": unique_users,
        "max_uses": coupon.max_uses,
        "remaining_uses": (coupon.max_uses - coupon.used_count) if coupon.max_uses else None,
        "roi": round((total_revenue / total_discount * 100) if total_discount > 0 else 0, 2),
    }
