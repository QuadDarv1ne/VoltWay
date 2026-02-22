"""add_reservations_system

Revision ID: 008_add_reservations_system
Revises: 007_add_reviews_and_ratings
Create Date: 2026-02-22

Add reservation/booking system for charging stations.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_reservations_system'
down_revision = '007_add_reviews_and_ratings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create reservations and reservation_slots tables"""
    # Create reservation_slots table first (for FK reference)
    op.create_table(
        'reservation_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('slot_number', sa.Integer(), nullable=False),
        sa.Column('connector_type', sa.String(length=50), nullable=False),
        sa.Column('max_power_kw', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, default=1),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    op.create_index('idx_slot_station', 'reservation_slots', ['station_id', 'slot_number'], unique=True)
    
    # Create reservations table
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('slot_number', sa.Integer(), nullable=True),
        sa.Column('connector_type', sa.String(length=50), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('actual_cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True, default='RUB'),
        sa.Column('payment_id', sa.String(length=100), nullable=True),
        sa.Column('payment_status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('cancelled_by', sa.String(length=20), nullable=True),
        sa.Column('checked_in_at', sa.DateTime(), nullable=True),
        sa.Column('checked_out_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('end_time > start_time', name='chk_reservation_time_range'),
        sa.CheckConstraint('duration_minutes > 0 AND duration_minutes <= 480', name='chk_reservation_duration'),
        sa.CheckConstraint('estimated_cost IS NULL OR estimated_cost >= 0', name='chk_reservation_cost'),
    )
    
    # Create indexes for reservations
    op.create_index('idx_reservations_station_id', 'reservations', ['station_id'])
    op.create_index('idx_reservations_user_id', 'reservations', ['user_id'])
    op.create_index('idx_reservations_station_time', 'reservations', ['station_id', 'start_time'])
    op.create_index('idx_reservations_user_time', 'reservations', ['user_id', 'start_time'])
    op.create_index('idx_reservations_status', 'reservations', ['status'])
    op.create_index('idx_reservations_payment', 'reservations', ['payment_status'])


def downgrade() -> None:
    """Drop reservations tables"""
    # Drop indexes
    op.drop_index('idx_reservations_payment', table_name='reservations')
    op.drop_index('idx_reservations_status', table_name='reservations')
    op.drop_index('idx_reservations_user_time', table_name='reservations')
    op.drop_index('idx_reservations_station_time', table_name='reservations')
    op.drop_index('idx_reservations_user_id', table_name='reservations')
    op.drop_index('idx_reservations_station_id', table_name='reservations')
    
    # Drop tables
    op.drop_table('reservations')
    
    op.drop_index('idx_slot_station', table_name='reservation_slots')
    op.drop_table('reservation_slots')
