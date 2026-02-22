"""add_coupons_system

Revision ID: 009_add_coupons_system
Revises: 008_add_reservations_system
Create Date: 2026-02-22

Add coupons and promotional codes system.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_add_coupons_system'
down_revision = '008_add_reservations_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create coupons and coupon_redemptions tables"""
    # Create coupons table
    op.create_table(
        'coupons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('discount_type', sa.String(length=20), nullable=False, default='percentage'),
        sa.Column('discount_value', sa.Float(), nullable=False),
        sa.Column('max_discount', sa.Float(), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('max_uses_per_user', sa.Integer(), nullable=True, default=1),
        sa.Column('used_count', sa.Integer(), nullable=True, default=0),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('min_reservation_cost', sa.Float(), nullable=True),
        sa.Column('applicable_connector_types', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, default=1),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('discount_value >= 0', name='chk_discount_value'),
        sa.CheckConstraint('max_uses IS NULL OR max_uses > 0', name='chk_max_uses'),
    )
    
    op.create_index('idx_coupons_code', 'coupons', ['code'])
    op.create_index('idx_coupons_code_active', 'coupons', ['code', 'is_active'])
    
    # Create coupon_redemptions table
    op.create_table(
        'coupon_redemptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coupon_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reservation_id', sa.Integer(), nullable=True),
        sa.Column('discount_amount', sa.Float(), nullable=False),
        sa.Column('final_cost', sa.Float(), nullable=False),
        sa.Column('redeemed_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    op.create_index('idx_coupon_redemptions_coupon', 'coupon_redemptions', ['coupon_id'])
    op.create_index('idx_coupon_redemptions_user', 'coupon_redemptions', ['user_id'])
    op.create_index('idx_coupon_redemptions_user_coupon', 'coupon_redemptions', ['user_id', 'coupon_id'], unique=True)
    op.create_index('idx_coupon_redemptions_reservation', 'coupon_redemptions', ['reservation_id'])
    
    # Add coupon to reservations table
    op.add_column('reservations', sa.Column('coupon_id', sa.Integer(), nullable=True))
    op.add_column('reservations', sa.Column('discount_amount', sa.Float(), nullable=True, default=0))
    op.create_foreign_key(
        'fk_reservations_coupon',
        'reservations', 'coupons',
        ['coupon_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_reservations_coupon', 'reservations', ['coupon_id'])


def downgrade() -> None:
    """Drop coupons tables"""
    # Drop foreign key and columns from reservations
    op.drop_constraint('fk_reservations_coupon', 'reservations', type_='foreignkey')
    op.drop_index('idx_reservations_coupon', table_name='reservations')
    op.drop_column('reservations', 'discount_amount')
    op.drop_column('reservations', 'coupon_id')
    
    # Drop indexes
    op.drop_index('idx_coupon_redemptions_reservation', table_name='coupon_redemptions')
    op.drop_index('idx_coupon_redemptions_user_coupon', table_name='coupon_redemptions')
    op.drop_index('idx_coupon_redemptions_user', table_name='coupon_redemptions')
    op.drop_index('idx_coupon_redemptions_coupon', table_name='coupon_redemptions')
    
    # Drop tables
    op.drop_table('coupon_redemptions')
    
    op.drop_index('idx_coupons_code_active', table_name='coupons')
    op.drop_index('idx_coupons_code', table_name='coupons')
    op.drop_table('coupons')
