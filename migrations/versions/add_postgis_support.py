"""Add PostGIS support and geospatial indexes

Revision ID: add_postgis_support
Revises: 
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_postgis_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable PostGIS extension and add geospatial columns"""
    # Enable PostGIS extension (PostgreSQL only)
    # This will be skipped for SQLite
    try:
        op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    except Exception:
        # SQLite doesn't support extensions, skip silently
        pass

    # Add geometry column to stations table
    op.add_column('stations', sa.Column('location', sa.String(255), nullable=True))
    
    # Create index for location-based queries
    op.create_index('idx_station_location_geom', 'stations', ['latitude', 'longitude'])
    
    # Create composite index for common query patterns
    op.create_index(
        'idx_station_location_status',
        'stations',
        ['latitude', 'longitude', 'status']
    )


def downgrade() -> None:
    """Remove PostGIS support"""
    op.drop_index('idx_station_location_status', table_name='stations')
    op.drop_index('idx_station_location_geom', table_name='stations')
    op.drop_column('stations', 'location')
    
    try:
        op.execute('DROP EXTENSION IF EXISTS postgis')
    except Exception:
        pass
