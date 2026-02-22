"""add performance indexes

Revision ID: 002
Revises: 001_initial_migrate
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial_migrate'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common queries"""
    
    # Composite index for geospatial queries
    op.create_index(
        'idx_station_location',
        'stations',
        ['latitude', 'longitude'],
        unique=False
    )
    
    # Index for location + status filtering
    op.create_index(
        'idx_station_location_status',
        'stations',
        ['latitude', 'longitude', 'status'],
        unique=False
    )
    
    # Index for connector type filtering
    op.create_index(
        'idx_station_connector',
        'stations',
        ['connector_type'],
        unique=False
    )
    
    # Index for power filtering
    op.create_index(
        'idx_station_power',
        'stations',
        ['power_kw'],
        unique=False
    )
    
    # Composite index for common filter combination
    op.create_index(
        'idx_station_connector_status',
        'stations',
        ['connector_type', 'status'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes"""
    op.drop_index('idx_station_connector_status', table_name='stations')
    op.drop_index('idx_station_power', table_name='stations')
    op.drop_index('idx_station_connector', table_name='stations')
    op.drop_index('idx_station_location_status', table_name='stations')
    op.drop_index('idx_station_location', table_name='stations')
