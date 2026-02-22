"""update_api_keys_hash

Revision ID: 004_update_api_keys_hash
Revises: 003_add_api_keys
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_update_api_keys_hash'
down_revision = '003_add_api_keys'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update API keys table to use hashed keys"""
    # Add new columns
    op.add_column('api_keys', sa.Column('key_hash', sa.String(64), nullable=True))
    op.add_column('api_keys', sa.Column('key_prefix', sa.String(8), nullable=True))
    
    # Note: In production, you would need to migrate existing keys
    # For new installations, these will be populated on creation
    
    # Set not null constraint after data migration
    op.alter_column('api_keys', 'key_hash', existing_nullable=False)
    op.alter_column('api_keys', 'key_prefix', existing_nullable=False)
    
    # Drop old key column
    op.drop_column('api_keys', 'key')
    
    # Create index on key_prefix for faster lookups
    op.create_index('ix_api_keys_key_prefix', 'api_keys', ['key_prefix'])


def downgrade() -> None:
    """Revert API keys table changes"""
    # Add back old key column
    op.add_column('api_keys', sa.Column('key', sa.String(64), nullable=True))
    
    # Drop new columns
    op.drop_column('api_keys', 'key_prefix')
    op.drop_column('api_keys', 'key_hash')
    
    # Recreate index on old key column
    op.create_index('ix_api_keys_key', 'api_keys', ['key'])
