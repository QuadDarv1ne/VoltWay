"""add performance indexes

Revision ID: 002
Revises: 001_initial_migrate
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common queries"""
    
    # Note: Basic indexes already created in 001_initial migration
    # This migration is kept for future additional indexes if needed
    pass


def downgrade() -> None:
    """Remove performance indexes"""
    pass
