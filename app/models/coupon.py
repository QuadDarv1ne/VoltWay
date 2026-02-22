"""
Coupons and Promotional Codes system.

Provides discount functionality for reservations.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.models import Base


class DiscountType(str, Enum):
    """Discount types"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    FREE_MINUTES = "free_minutes"


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Discount details
    discount_type = Column(String(20), nullable=False, default=DiscountType.PERCENTAGE.value)
    discount_value = Column(Float, nullable=False)  # Percentage or fixed amount
    max_discount = Column(Float, nullable=True)  # Maximum discount for percentage type
    
    # Usage limits
    max_uses = Column(Integer, nullable=True)  # Total uses across all users
    max_uses_per_user = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    
    # Validity period
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    # Restrictions
    min_reservation_cost = Column(Float, nullable=True)  # Minimum cost to apply coupon
    applicable_connector_types = Column(String(200), nullable=True)  # Comma-separated list
    
    # Status
    is_active = Column(Integer, default=1)
    
    # Metadata
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    redemptions = relationship("CouponRedemption", back_populates="coupon", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_coupon_code_active", "code", "is_active"),
        CheckConstraint("discount_value >= 0", name="chk_discount_value"),
        CheckConstraint("max_uses IS NULL OR max_uses > 0", name="chk_max_uses"),
    )
    
    def __repr__(self):
        return f"<Coupon(code='{self.code}', discount={self.discount_value}{self.discount_type})>"
    
    def is_valid(self) -> bool:
        """Check if coupon is currently valid"""
        if not self.is_active:
            return False
        
        now = datetime.utcnow()
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        
        return True
    
    def calculate_discount(self, reservation_cost: float, duration_minutes: int) -> float:
        """
        Calculate discount amount for a reservation.
        
        Args:
            reservation_cost: Original reservation cost
            duration_minutes: Reservation duration in minutes
            
        Returns:
            Discount amount
        """
        if not self.is_valid():
            return 0.0
        
        # Check minimum cost requirement
        if self.min_reservation_cost and reservation_cost < self.min_reservation_cost:
            return 0.0
        
        discount = 0.0
        
        if self.discount_type == DiscountType.PERCENTAGE.value:
            discount = reservation_cost * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
        elif self.discount_type == DiscountType.FIXED.value:
            discount = min(self.discount_value, reservation_cost)
        elif self.discount_type == DiscountType.FREE_MINUTES.value:
            # Calculate value of free minutes
            minute_rate = reservation_cost / duration_minutes if duration_minutes > 0 else 0
            discount = self.discount_value * minute_rate
        
        return round(discount, 2)


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True)
    
    # Discount applied
    discount_amount = Column(Float, nullable=False)
    final_cost = Column(Float, nullable=False)
    
    # Timestamp
    redeemed_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    coupon = relationship("Coupon", back_populates="redemptions")
    
    __table_args__ = (
        Index("idx_redemption_user_coupon", "user_id", "coupon_id", unique=True),
        Index("idx_redemption_reservation", "reservation_id"),
    )
    
    def __repr__(self):
        return f"<CouponRedemption(coupon_id={self.coupon_id}, user_id={self.user_id})>"
