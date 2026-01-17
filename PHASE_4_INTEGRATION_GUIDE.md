# VoltWay Phase 4 - Integration Guide

## Overview

This guide explains how to integrate all Phase 4 improvements into your VoltWay application.

## Files Added in Phase 4

```
app/utils/
├── advanced_logging.py      # Structured JSON logging with rotation
├── metrics.py               # Prometheus metrics and monitoring
├── caching.py              # Function-level caching decorators
├── batch_ops.py            # Bulk database operations
├── memory_optimization.py   # Memory pool and lazy loading
├── background_tasks.py      # Job queue and task scheduling
├── openapi_docs.py         # Enhanced API documentation

app/middleware/
├── __init__.py
└── logging.py              # Request/response middleware

PHASE_4_IMPROVEMENTS.md     # Detailed improvements documentation
```

## Step-by-Step Integration

### 1. Update requirements.txt

Add new dependencies:
```bash
prometheus-client==0.18.0
psutil==5.9.6
```

Install with:
```bash
pip install -r requirements.txt
```

### 2. Initialize Logging in main.py

```python
from app.utils.advanced_logging import setup_logging

# At module level
logger = setup_logging(__name__)

# Configure in startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    # Initialize other components
```

### 3. Add Middleware

```python
from app.middleware.logging import RequestLoggingMiddleware, PerformanceMiddleware

# Add middleware (BEFORE other middleware like CORS)
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RequestLoggingMiddleware)
```

### 4. Integrate Metrics

```python
from app.utils.metrics import get_metrics
from fastapi.responses import Response

@app.get("/metrics", tags=["monitoring"])
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_metrics(), media_type="text/plain")
```

### 5. Use Caching in Endpoints

```python
from app.utils.caching import redis_cache, memory_cache

@app.get("/api/v1/stations")
@redis_cache(ttl=3600)  # Cache for 1 hour
@memory_cache(ttl=300)  # Also cache in memory for 5 minutes
async def get_stations(skip: int = 0, limit: int = 100):
    # Your endpoint logic
    return stations
```

### 6. Use Batch Operations

```python
from app.utils.batch_ops import BatchOperations

@app.post("/api/v1/stations/bulk")
async def bulk_create_stations(stations: List[StationCreate]):
    async with BatchOperations(db, Station, batch_size=500) as ops:
        for station_data in stations:
            station = Station(**station_data.dict())
            await ops.add(station)
    return {"created": len(stations)}
```

### 7. Initialize Background Tasks

```python
from app.utils.background_tasks import (
    JobQueue, TaskScheduler, refresh_cache, 
    sync_external_data, cleanup_old_jobs
)

# Global instances
job_queue = JobQueue(max_workers=5)
task_scheduler = TaskScheduler()

@app.on_event("startup")
async def startup_background_tasks():
    # Start job queue
    await job_queue.start()
    
    # Add scheduled tasks
    task_scheduler.add_task(refresh_cache, interval_seconds=3600)
    task_scheduler.add_task(sync_external_data, interval_seconds=1800)
    task_scheduler.add_task(cleanup_old_jobs, interval_seconds=86400)
    
    # Start scheduler
    await task_scheduler.start()

@app.on_event("shutdown")
async def shutdown_background_tasks():
    await job_queue.stop()
    await task_scheduler.stop()
```

### 8. Submit Background Jobs

```python
@app.post("/api/v1/export/data")
async def export_data_async():
    """Async export in background"""
    job_id = await job_queue.submit(
        export_large_dataset,
        name="export_data",
        format="csv"
    )
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/v1/export/status/{job_id}")
async def get_export_status(job_id: str):
    """Check export status"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404)
    return {
        "id": job.id,
        "status": job.status,
        "result": job.result if job.status == JobStatus.COMPLETED else None
    }
```

### 9. Use Memory Optimization

```python
from app.utils.memory_optimization import (
    LazyLoader, MemoryPool, StreamingProcessor, BulkInsertBuffer
)

# Lazy loading
lazy_config = LazyLoader(lambda: load_heavy_config())

# Memory pool for frequent objects
dict_pool = MemoryPool(lambda: {}, max_size=100)

# Streaming large datasets
async def process_large_dataset():
    async for item in StreamingProcessor.stream_process(
        large_list, chunk_size=1000
    ):
        # Process one item at a time
        await process_item(item)

# Bulk insert with buffering
async with BulkInsertBuffer(db_session, Station, batch_size=1000) as buffer:
    for station_data in stations:
        await buffer.add(Station(**station_data))
```

### 10. Enhance OpenAPI Documentation

```python
from app.utils.openapi_docs import enhance_openapi_documentation

# In main.py, after creating FastAPI instance
enhance_openapi_documentation(app)

# Add descriptions to endpoints
@app.get(
    "/api/v1/stations",
    summary="List charging stations",
    description="""
    Retrieve a list of electric charging stations near your location.
    
    Returns stations sorted by distance with real-time availability.
    """,
    tags=["stations"]
)
async def get_stations():
    pass
```

## Testing

### Test Metrics Endpoint

```bash
curl http://localhost:8000/metrics

# Output format:
# # HELP request_count Total HTTP requests
# # TYPE request_count counter
# request_count{method="GET",endpoint="/api/v1/stations"} 1234
```

### Test Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

### Test Background Jobs

```bash
# Submit job
curl -X POST http://localhost:8000/api/v1/export/data

# Check status
curl http://localhost:8000/api/v1/export/status/{job_id}
```

### Check Logs

```bash
# View JSON logs
tail -f logs/app.log | jq .

# Filter by level
tail -f logs/app.log | jq 'select(.level=="ERROR")'
```

## Configuration

### Environment Variables

```env
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=logs

# Metrics
METRICS_ENABLED=true
SLOW_REQUEST_THRESHOLD=1.0

# Caching
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Memory
MEMORY_THRESHOLD_MB=500
BATCH_SIZE=1000

# Background tasks
MAX_WORKERS=5
TASK_INTERVAL_REFRESH=3600
TASK_INTERVAL_SYNC=1800
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'voltway'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Create dashboard with panels for:
- Request rate and latency
- Error rate and types
- Database query performance
- Cache hit ratio
- Memory usage
- Active connections

### Log Aggregation

```bash
# For ELK Stack
# Filebeat configuration:
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /path/to/logs/app.log
    json.message_key: msg
    json.keys_under_root: true
```

## Performance Optimization Tips

1. **Caching Strategy**
   - Use `@memory_cache` for small, frequently accessed data
   - Use `@redis_cache` for large, shared data
   - Set appropriate TTL values

2. **Batch Operations**
   - Use for bulk inserts/updates (>100 items)
   - Adjust batch_size based on memory available
   - Monitor with Prometheus metrics

3. **Memory Management**
   - Enable MemoryMonitor for production
   - Use LazyLoader for expensive computations
   - Monitor with psutil-based memory tracking

4. **Background Tasks**
   - Offload heavy operations to job queue
   - Schedule maintenance tasks during off-peak hours
   - Monitor job queue stats regularly

## Troubleshooting

### High Memory Usage

```python
# Check memory usage
monitor = MemoryMonitor(threshold_mb=500)
monitor.log_memory_usage()

# Force garbage collection if needed
gc.collect()
```

### Slow Requests

Check `/metrics` endpoint for request_duration histogram:
```
request_duration_seconds_bucket{le="1.0"}
request_duration_seconds_bucket{le="5.0"}
request_duration_seconds_bucket{le="10.0"}
```

### Cache Not Working

Verify Redis connection:
```python
import redis
r = redis.from_url(REDIS_URL)
r.ping()  # Should return True
```

### Job Queue Backed Up

Monitor queue stats:
```python
queue_stats = job_queue.get_stats()
print(queue_stats)  # Check pending, running, failed
```

## Version Compatibility

- Python 3.8+
- FastAPI 0.95.2+
- SQLAlchemy 2.0.23+
- PostgreSQL/SQLite

## Next Steps

After integration:
1. Deploy to staging environment
2. Monitor metrics and logs for 24-48 hours
3. Tune cache TTL values based on hit rates
4. Adjust batch sizes based on performance
5. Set up alerting for errors and anomalies

## Support

For issues or questions:
- Check logs in `logs/app.log` (JSON format)
- Review metrics at `/metrics` endpoint
- Check job queue status and completed jobs
- Refer to inline documentation in source files

