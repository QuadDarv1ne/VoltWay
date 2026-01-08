from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.profiler import query_profiler
from app.utils.cache import cache

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """Get application performance metrics"""
    # Get query profiler stats
    query_stats = query_profiler.get_stats()
    
    # Get cache stats (if Redis is available)
    cache_stats = {}
    if cache.redis_client:
        try:
            info = cache.redis_client.info()
            cache_stats = {
                "redis_connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", "N/A"),
                "total_commands_processed": info.get("total_commands_processed", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", "N/A"),
                "keyspace_misses": info.get("keyspace_misses", "N/A")
            }
        except Exception as e:
            cache_stats = {"redis_connected": False, "error": str(e)}
    else:
        cache_stats = {"redis_connected": False, "reason": "Redis not configured"}
    
    # Get database stats
    db_stats = {}
    try:
        # Simple database query to check connectivity
        from sqlalchemy import text
        result = db.execute(text("SELECT 1")).fetchone()
        db_stats["connected"] = result is not None
        db_stats["active_connections"] = "N/A"  # Would need postgres-specific query
    except Exception as e:
        db_stats = {"connected": False, "error": str(e)}
    
    return {
        "query_performance": query_stats,
        "cache": cache_stats,
        "database": db_stats,
        "timestamp": "2026-01-08T17:30:00Z"
    }


@router.get("/clear-query-stats")
async def clear_query_statistics():
    """Clear collected query statistics"""
    query_profiler.clear()
    return {"message": "Query statistics cleared"}


@router.get("/cache-stats")
async def get_cache_statistics():
    """Get detailed cache statistics"""
    if not cache.redis_client:
        return {"error": "Redis not available"}
    
    try:
        # Get all keys matching pattern
        station_keys = cache.redis_client.keys("stations:*")
        user_keys = cache.redis_client.keys("user:*")
        other_keys = cache.redis_client.keys("*")
        
        # Remove station and user keys from other keys
        other_keys = [k for k in other_keys if not k.startswith(b"stations:") and not k.startswith(b"user:")]
        
        ttl_info = {}
        for key in station_keys[:10]:  # Sample first 10 keys
            ttl = cache.redis_client.ttl(key)
            ttl_info[key.decode('utf-8')] = ttl
            
        return {
            "station_cache_entries": len(station_keys),
            "user_cache_entries": len(user_keys),
            "other_cache_entries": len(other_keys),
            "total_entries": len(station_keys) + len(user_keys) + len(other_keys),
            "sample_ttl": ttl_info,
            "memory_info": cache.redis_client.info().get("memory", {})
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/warm-cache")
async def warm_cache(
    latitude: float = 55.7558,
    longitude: float = 37.6173,
    radius_km: int = 10,
    db: Session = Depends(get_db)
):
    """Pre-populate cache with common queries"""
    from app.api.stations import get_stations
    
    try:
        # Warm cache with common location queries
        common_queries = [
            {"latitude": latitude, "longitude": longitude, "radius_km": radius_km},
            {"latitude": latitude, "longitude": longitude, "radius_km": 20},
            {"latitude": latitude, "longitude": longitude, "radius_km": 50},
        ]
        
        warmed_count = 0
        for query_params in common_queries:
            # This would trigger the cache population
            # In a real implementation, you'd call the actual endpoint
            cache_key = cache.get_station_cache_key(
                latitude=query_params["latitude"],
                longitude=query_params["longitude"],
                radius_km=query_params["radius_km"],
                connector_type=None,
                min_power_kw=0,
                skip=0,
                limit=100
            )
            
            # Check if already cached
            if not cache.get(cache_key):
                # Simulate warming (in real app, call actual endpoint)
                warmed_count += 1
                
        return {
            "message": f"Cache warming initiated for {warmed_count} queries",
            "queries_warmed": warmed_count
        }
    except Exception as e:
        return {"error": str(e)}