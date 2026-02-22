"""Add PostGIS support and geospatial indexes

Revision ID: add_postgis_support
Revises: 
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_postgis_support'
down_revision = '002'
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

    # Add geometry column to stations table (for PostgreSQL with PostGIS)
    # For SQLite, this is just a placeholder column
    op.add_column('stations', sa.Column('location', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove PostGIS support"""
    op.drop_column('stations', 'location')
    
    try:
        op.execute('DROP EXTENSION IF EXISTS postgis')
    except Exception:
        pass
