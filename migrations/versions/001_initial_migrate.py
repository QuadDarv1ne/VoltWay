"""Create initial tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    op.create_index('idx_users_active', 'users', ['is_active'])
    op.create_index('idx_users_admin', 'users', ['is_admin'])
    op.create_index('idx_users_active_created', 'users', ['is_active', 'created_at'])

    # Create stations table
    op.create_table(
        'stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('connector_type', sa.String(length=50), nullable=False),
        sa.Column('power_kw', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('hours', sa.Text(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('power_kw > 0', name='chk_power_positive'),
        sa.CheckConstraint('latitude >= -90 AND latitude <= 90', name='chk_latitude_range'),
        sa.CheckConstraint('longitude >= -180 AND longitude <= 180', name='chk_longitude_range'),
        sa.CheckConstraint("status IN ('available', 'occupied', 'maintenance', 'unknown')", name='chk_status_valid')
    )
    op.create_index(op.f('ix_stations_id'), 'stations', ['id'], unique=False)
    op.create_index(op.f('ix_stations_title'), 'stations', ['title'], unique=False)
    op.create_index('idx_station_location', 'stations', ['latitude', 'longitude'])
    op.create_index('idx_station_location_status', 'stations', ['latitude', 'longitude', 'status'])
    op.create_index('idx_station_connector', 'stations', ['connector_type'])
    op.create_index('idx_station_status', 'stations', ['status'])
    op.create_index('idx_station_power', 'stations', ['power_kw'])
    op.create_index('idx_station_connector_status', 'stations', ['connector_type', 'status'])

    # Create favorites table
    op.create_table(
        'favorites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'station_id', name='unique_user_station_favorite')
    )
    op.create_index(op.f('ix_favorites_id'), 'favorites', ['id'], unique=False)
    op.create_index('idx_favorites_user_id', 'favorites', ['user_id'])
    op.create_index('idx_favorites_station_id', 'favorites', ['station_id'])
    op.create_index('idx_favorites_user_station', 'favorites', ['user_id', 'station_id'])
    op.create_index('idx_favorites_station_count', 'favorites', ['station_id'])


def downgrade() -> None:
    op.drop_table('favorites')
    op.drop_table('stations')
    op.drop_table('users')
