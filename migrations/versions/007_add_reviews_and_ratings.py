"""add_reviews_and_ratings

Revision ID: 007_add_reviews_and_ratings
Revises: 006_add_audit_logs_table
Create Date: 2026-02-22

Add reviews and ratings system for stations.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_reviews_and_ratings'
down_revision = '006_add_audit_logs_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create reviews, review_photos, and review_votes tables"""
    # Add rating columns to stations table
    op.add_column(
        'stations',
        sa.Column('avg_rating', sa.Float(), nullable=True)
    )
    op.add_column(
        'stations',
        sa.Column('review_count', sa.Integer(), nullable=False, server_default='0')
    )

    # Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('cleanliness_rating', sa.Integer(), nullable=True),
        sa.Column('safety_rating', sa.Integer(), nullable=True),
        sa.Column('accessibility_rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_verified', sa.Integer(), nullable=True, default=0),
        sa.Column('is_approved', sa.Integer(), nullable=True, default=1),
        sa.Column('is_hidden', sa.Integer(), nullable=True, default=0),
        sa.Column('hidden_reason', sa.String(length=200), nullable=True),
        sa.Column('helpful_count', sa.Integer(), nullable=True, default=0),
        sa.Column('not_helpful_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='chk_rating_range'),
    )

    # Create indexes for reviews
    op.create_index('ix_reviews_station_id', 'reviews', ['station_id'])
    op.create_index('ix_reviews_user_id', 'reviews', ['user_id'])
    op.create_index('ix_reviews_created_at', 'reviews', ['created_at'])
    op.create_index('ix_reviews_station_rating', 'reviews', ['station_id', 'rating'])
    op.create_index('ix_reviews_approved', 'reviews', ['is_approved', 'is_hidden'])

    # Create review_photos table
    op.create_table(
        'review_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('caption', sa.String(length=200), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('is_primary', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_review_photos_review_id', 'review_photos', ['review_id'])

    # Create review_votes table
    op.create_table(
        'review_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('vote_type', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_review_votes_review_id', 'review_votes', ['review_id'])
    op.create_index('ix_review_votes_review_user', 'review_votes', ['review_id', 'user_id'], unique=True)

    # Create trigger function to update station ratings
    op.execute("""
        CREATE OR REPLACE FUNCTION update_station_rating()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
                UPDATE stations
                SET avg_rating = (
                        SELECT COALESCE(AVG(rating), 0)
                        FROM reviews
                        WHERE station_id = NEW.station_id
                        AND is_approved = 1
                        AND is_hidden = 0
                    ),
                    review_count = (
                        SELECT COUNT(*)
                        FROM reviews
                        WHERE station_id = NEW.station_id
                        AND is_approved = 1
                        AND is_hidden = 0
                    )
                WHERE id = NEW.station_id;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE stations
                SET avg_rating = (
                        SELECT COALESCE(AVG(rating), 0)
                        FROM reviews
                        WHERE station_id = OLD.station_id
                        AND is_approved = 1
                        AND is_hidden = 0
                    ),
                    review_count = (
                        SELECT COUNT(*)
                        FROM reviews
                        WHERE station_id = OLD.station_id
                        AND is_approved = 1
                        AND is_hidden = 0
                    )
                WHERE id = OLD.station_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER trg_review_insert
        AFTER INSERT ON reviews
        FOR EACH ROW EXECUTE FUNCTION update_station_rating();
    """)

    op.execute("""
        CREATE TRIGGER trg_review_update
        AFTER UPDATE ON reviews
        FOR EACH ROW EXECUTE FUNCTION update_station_rating();
    """)

    op.execute("""
        CREATE TRIGGER trg_review_delete
        AFTER DELETE ON reviews
        FOR EACH ROW EXECUTE FUNCTION update_station_rating();
    """)


def downgrade() -> None:
    """Drop reviews tables and related objects"""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_review_delete ON reviews")
    op.execute("DROP TRIGGER IF EXISTS trg_review_update ON reviews")
    op.execute("DROP TRIGGER IF EXISTS trg_review_insert ON reviews")
    op.execute("DROP FUNCTION IF EXISTS update_station_rating()")

    # Drop tables
    op.drop_index('ix_review_votes_review_user', table_name='review_votes')
    op.drop_index('ix_review_votes_review_id', table_name='review_votes')
    op.drop_table('review_votes')

    op.drop_index('ix_review_photos_review_id', table_name='review_photos')
    op.drop_table('review_photos')

    op.drop_index('ix_reviews_approved', table_name='reviews')
    op.drop_index('ix_reviews_station_rating', table_name='reviews')
    op.drop_index('ix_reviews_created_at', table_name='reviews')
    op.drop_index('ix_reviews_user_id', table_name='reviews')
    op.drop_index('ix_reviews_station_id', table_name='reviews')
    op.drop_table('reviews')

    # Drop columns from stations
    op.drop_column('stations', 'review_count')
    op.drop_column('stations', 'avg_rating')
