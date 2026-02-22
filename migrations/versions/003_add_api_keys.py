"""add api keys table

Revision ID: 003
Revises: add_postgis_support
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = 'add_postgis_support'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add API keys table"""
    
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('rate_limit_requests', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('rate_limit_period', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # Create indexes
    op.create_index('ix_api_keys_id', 'api_keys', ['id'], unique=False)
    op.create_index('ix_api_keys_key', 'api_keys', ['key'], unique=True)
    op.create_index('idx_api_keys_active', 'api_keys', ['is_active'])
    op.create_index('idx_api_keys_role', 'api_keys', ['role'])


def downgrade() -> None:
    """Remove API keys table"""
    op.drop_index('idx_api_keys_role', table_name='api_keys')
    op.drop_index('idx_api_keys_active', table_name='api_keys')
    op.drop_index('ix_api_keys_key', table_name='api_keys')
    op.drop_index('ix_api_keys_id', table_name='api_keys')
    op.drop_table('api_keys')
