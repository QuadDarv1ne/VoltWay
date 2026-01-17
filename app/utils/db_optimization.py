"""Database optimization utilities and indices"""

from sqlalchemy import Index
from app.models.station import Station
from app.models.user import User
from app.models.favorite import Favorite


def create_indices(engine):
    """Create database indices for better query performance"""
    
    # Station indices
    indices = [
        Index('idx_station_latitude', Station.latitude),
        Index('idx_station_longitude', Station.longitude),
        Index('idx_station_connector', Station.connector_type),
        Index('idx_station_power', Station.power_kw),
        Index('idx_station_geo', Station.latitude, Station.longitude),  # Compound index
        
        # User indices
        Index('idx_user_email', User.email, unique=True),
        Index('idx_user_created', User.created_at),
        
        # Favorite indices
        Index('idx_favorite_user', Favorite.user_id),
        Index('idx_favorite_station', Favorite.station_id),
        Index('idx_favorite_user_station', Favorite.user_id, Favorite.station_id, unique=True),
    ]
    
    for index in indices:
        index.create(engine, checkfirst=True)
    
    return len(indices)


# Query optimization recommendations
QUERY_OPTIMIZATION_TIPS = """
Query Optimization Guide:

1. Use select() instead of query() (SQLAlchemy 2.0 style):
   OLD: db.query(Station).filter(...).all()
   NEW: await db.execute(select(Station).where(...))

2. Use appropriate indices:
   - Latitude/Longitude for geo searches
   - Connector type for filtering
   - User ID for favorites lookup

3. Avoid N+1 queries:
   - Use joinedload() for relationships
   - Use selectinload() for async queries
   - Batch operations when possible

4. Use pagination:
   - Always use skip/limit
   - Index on created_at for time-based queries

5. Monitor query performance:
   - Use EXPLAIN plans
   - Log slow queries (> 100ms)
   - Profile with py-spy or similar
"""


EXPLAIN_QUERIES = """
PostgreSQL EXPLAIN Examples:

1. Geo-spatial search with indices:
   EXPLAIN ANALYZE
   SELECT * FROM station
   WHERE latitude BETWEEN ? AND ?
     AND longitude BETWEEN ? AND ?
   ORDER BY distance;

2. Common filter query:
   EXPLAIN ANALYZE
   SELECT * FROM station
   WHERE connector_type LIKE ?
     AND power_kw >= ?
   LIMIT 100;

3. User favorites with JOIN:
   EXPLAIN ANALYZE
   SELECT s.* FROM station s
   INNER JOIN favorite f ON s.id = f.station_id
   WHERE f.user_id = ?
   ORDER BY f.created_at DESC;
"""
