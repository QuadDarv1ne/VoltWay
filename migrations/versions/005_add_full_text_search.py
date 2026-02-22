"""add_full_text_search

Revision ID: 005_add_full_text_search
Revises: 004_update_api_keys_hash
Create Date: 2026-02-22

Add PostgreSQL full-text search support for stations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '005_add_full_text_search'
down_revision = '004_update_api_keys_hash'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add full-text search columns and indexes"""
    # Add search_vector column for full-text search
    op.add_column(
        'stations',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR(),
            nullable=True,
            comment='Full-text search vector'
        )
    )

    # Add search_query column for storing last search query
    op.add_column(
        'stations',
        sa.Column(
            'search_query',
            postgresql.TSQUERY(),
            nullable=True,
            comment='Stored search query'
        )
    )

    # Create GIN index for fast full-text search
    op.create_index(
        'idx_station_search_vector',
        'stations',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    # Create trigger function for automatic search_vector update
    op.execute("""
        CREATE OR REPLACE FUNCTION stations_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('russian', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(NEW.address, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(NEW.connector_type, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to update search_vector on insert/update
    op.execute("""
        CREATE TRIGGER stations_search_vector_trigger
        BEFORE INSERT OR UPDATE ON stations
        FOR EACH ROW
        EXECUTE FUNCTION stations_search_vector_update();
    """)

    # Populate search_vector for existing records
    op.execute("""
        UPDATE stations SET
            search_vector =
                setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(address, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(connector_type, '')), 'C');
    """)

    # Make search_vector not null after population
    op.alter_column('stations', 'search_vector', nullable=False)


def downgrade() -> None:
    """Remove full-text search columns and indexes"""
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS stations_search_vector_trigger ON stations")
    op.execute("DROP FUNCTION IF EXISTS stations_search_vector_update()")

    # Drop index
    op.drop_index('idx_station_search_vector', table_name='stations')

    # Drop columns
    op.drop_column('stations', 'search_query')
    op.drop_column('stations', 'search_vector')
