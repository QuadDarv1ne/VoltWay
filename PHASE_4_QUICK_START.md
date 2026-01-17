# VoltWay Phase 4 - Step-by-Step Setup Guide

## Quick Start (5 minutes)

### Step 1: Install Dependencies
```bash
cd c:\Users\maksi\OneDrive\Documents\GitHub\VoltWay
pip install -r requirements.txt
```

### Step 2: Run Application
```bash
python -m uvicorn app.main:app --reload
```

### Step 3: Test Endpoints
```bash
# Test health check
curl http://localhost:8000/health

# Test metrics
curl http://localhost:8000/metrics

# Test API
curl http://localhost:8000/api/v1/health
```

---

## Complete Setup Guide

### Part 1: Initial Configuration (10 minutes)

#### 1.1 Install Python Dependencies
```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/Scripts/activate  # On Windows

# Install requirements
pip install -r requirements.txt
```

#### 1.2 Verify Installation
```bash
# Check FastAPI
python -c "import fastapi; print(fastapi.__version__)"

# Check Prometheus client
python -c "import prometheus_client; print('OK')"

# Check psutil
python -c "import psutil; print('OK')"
```

#### 1.3 Setup Environment
```bash
# Create .env file
cat > .env << EOF
LOG_LEVEL=INFO
LOG_FORMAT=json
METRICS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
MEMORY_THRESHOLD_MB=500
EOF
```

---

### Part 2: Start Application (5 minutes)

#### 2.1 Run Development Server
```bash
# Terminal 1: Start FastAPI
python -m uvicorn app.main:app --reload --port 8000
```

#### 2.2 Optional: Start Redis
```bash
# Terminal 2: Start Redis (if using caching)
redis-server
```

#### 2.3 Verify Running
```bash
# Terminal 3: Test endpoints
curl http://localhost:8000/health
```

---

### Part 3: Test Metrics & Monitoring (10 minutes)

#### 3.1 View Prometheus Metrics
```bash
curl http://localhost:8000/metrics

# Expected output:
# # HELP request_count Total HTTP requests
# # TYPE request_count counter
# ...
```

#### 3.2 Check Logs
```bash
# View JSON logs
tail -f logs/app.log

# Pretty print JSON logs
tail -f logs/app.log | python -m json.tool
```

#### 3.3 Test Caching
```bash
# First request (cache miss)
curl http://localhost:8000/api/v1/stations
# Check logs for cache_hit=false

# Second request (cache hit)
curl http://localhost:8000/api/v1/stations
# Check logs for cache_hit=true
```

---

### Part 4: Test Background Jobs (10 minutes)

#### 4.1 Submit Job
```bash
curl -X POST http://localhost:8000/api/v1/export/data \
  -H "Content-Type: application/json"

# Response:
# {"job_id": "550e8400-e29b-41d4-a716-446655440000", "status": "queued"}
```

#### 4.2 Check Job Status
```bash
curl http://localhost:8000/api/v1/export/status/550e8400-e29b-41d4-a716-446655440000

# Response:
# {"id": "...", "status": "running", "result": null}
```

#### 4.3 View Queue Stats
```bash
# Check queue stats
python -c "from app.utils.background_tasks import job_queue; print(job_queue.get_stats())"
```

---

### Part 5: Docker Setup (15 minutes)

#### 5.1 Build Development Image
```bash
docker build -t voltway:dev -f Dockerfile .
```

#### 5.2 Run Development Container
```bash
docker run -p 8000:8000 -v $(pwd):/app voltway:dev
```

#### 5.3 Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

#### 5.4 Production Deployment
```bash
# Build production image
docker build -t voltway:prod -f Dockerfile.prod .

# Start with compose
docker-compose -f docker-compose.prod.yml up -d
```

---

### Part 6: Database Optimization (10 minutes)

#### 6.1 Apply Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

#### 6.2 Create Indices
```bash
python -c """
from app.utils.db_optimization import create_all_indices
from app.database import SessionLocal
session = SessionLocal()
create_all_indices(session)
print('Indices created successfully')
"""
```

#### 6.3 Verify Indices
```sql
-- Check indices in PostgreSQL
SELECT indexname FROM pg_indexes WHERE tablename='stations';
```

---

### Part 7: Monitoring Setup (20 minutes)

#### 7.1 Install Prometheus
```bash
# Download Prometheus
# On macOS: brew install prometheus
# On Windows: Download from https://prometheus.io/download/

# Create prometheus.yml
cat > prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'voltway'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
EOF
```

#### 7.2 Start Prometheus
```bash
prometheus --config.file=prometheus.yml
# Access at http://localhost:9090
```

#### 7.3 Create Grafana Dashboard
```bash
# Install Grafana
# On macOS: brew install grafana
# On Windows: Download from https://grafana.com/grafana/download

# Start Grafana
# Access at http://localhost:3000

# Add Prometheus data source:
# URL: http://localhost:9090
# Create dashboard with queries:
# - request_count{job="voltway"}
# - request_duration_seconds{job="voltway"}
# - cache_hits{job="voltway"}
```

---

### Part 8: Analytics (15 minutes)

#### 8.1 Initialize Analytics Engine
```python
from app.utils.analytics import AnalyticsEngine, AnalyticsEvent
from datetime import datetime

engine = AnalyticsEngine()

# Record event
event = AnalyticsEvent(
    event_type="visit",
    station_id=1,
    user_id=1,
    timestamp=datetime.utcnow(),
    duration_minutes=30,
    amount_spent=5.50
)
engine.record_event(event)
```

#### 8.2 Get Analytics
```python
# Get station stats
stats = engine.get_station_stats(1)
print(f"Total visits: {stats.total_visits}")
print(f"Peak hour: {stats.peak_hour}")
print(f"Revenue: ${stats.revenue}")

# Get popular stations
popular = engine.get_popular_stations(limit=5)
print(f"Top 5: {popular}")

# Get trends
trends = engine.get_trend_analysis(time_days=30)
print(f"Daily visits: {trends['daily_visits']}")
```

---

### Part 9: API Documentation (5 minutes)

#### 9.1 Access Swagger UI
```
http://localhost:8000/docs
```

#### 9.2 Access ReDoc
```
http://localhost:8000/redoc
```

#### 9.3 Download OpenAPI Schema
```bash
curl http://localhost:8000/openapi.json > openapi.json
```

---

### Part 10: Testing (15 minutes)

#### 10.1 Run Unit Tests
```bash
pytest tests/test_auth.py -v
pytest tests/test_cache.py -v
pytest tests/test_geo.py -v
pytest tests/test_main.py -v
```

#### 10.2 Run Integration Tests
```bash
pytest tests/test_integration.py -v
```

#### 10.3 Run All Tests
```bash
pytest -v --cov=app --cov-report=html
```

---

## Advanced Configuration

### Caching Configuration

#### Redis Cache
```python
from app.utils.caching import redis_cache

@redis_cache(ttl=3600)  # 1 hour
async def get_stations():
    return await db.query(Station).all()
```

#### Memory Cache
```python
from app.utils.caching import memory_cache

@memory_cache(ttl=300)  # 5 minutes
async def compute_distance(lat1, lon1, lat2, lon2):
    return haversine(lat1, lon1, lat2, lon2)
```

### Batch Operations

```python
from app.utils.batch_ops import BatchOperations

async with BatchOperations(db, Station, batch_size=1000) as ops:
    for station_data in large_list:
        station = Station(**station_data)
        await ops.add(station)
    # Auto-flush on exit
```

### Background Tasks

```python
from app.utils.background_tasks import JobQueue

# Initialize
job_queue = JobQueue(max_workers=5)
await job_queue.start()

# Submit job
job_id = await job_queue.submit(
    heavy_operation,
    name="export_data"
)

# Check status
job = job_queue.get_job(job_id)
print(f"Status: {job.status}")
```

---

## Troubleshooting

### Issue 1: ImportError for new modules

**Solution:**
```bash
# Reinstall requirements
pip install --upgrade -r requirements.txt

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +

# Restart application
```

### Issue 2: Redis connection error

**Solution:**
```bash
# Check Redis is running
redis-cli ping

# If not running:
redis-server

# If connection string wrong, set env var:
export REDIS_URL=redis://localhost:6379/0
```

### Issue 3: High memory usage

**Solution:**
```python
from app.utils.memory_optimization import MemoryMonitor

monitor = MemoryMonitor(threshold_mb=500)
monitor.log_memory_usage()

# Check for memory leaks
import gc
gc.collect()
```

### Issue 4: Slow requests

**Solution:**
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep request_duration

# Enable debug logging
export LOG_LEVEL=DEBUG

# Check slow requests in logs
grep "slow_request" logs/app.log
```

---

## Performance Tuning

### Optimize Caching

```python
# Increase cache TTL for stable data
@redis_cache(ttl=86400)  # 24 hours
async def get_configuration():
    pass

# Use memory cache for hot data
@memory_cache(ttl=60)  # 1 minute
async def get_current_stats():
    pass
```

### Optimize Batch Size

```python
# For large datasets, use bigger batches
async with BatchOperations(db, Model, batch_size=5000) as ops:
    for item in million_items:
        await ops.add(item)

# For small datasets, use smaller batches
async with BatchOperations(db, Model, batch_size=100) as ops:
    for item in small_list:
        await ops.add(item)
```

### Optimize Workers

```python
# For CPU-bound: min(4, cpu_count())
# For I/O-bound: 2 * cpu_count()
job_queue = JobQueue(max_workers=8)
```

---

## Monitoring Checklist

### Daily
- [ ] Check application logs for errors
- [ ] Monitor metrics dashboard
- [ ] Review error rates
- [ ] Check cache hit rates

### Weekly
- [ ] Review performance trends
- [ ] Analyze user behavior
- [ ] Check database performance
- [ ] Review resource usage

### Monthly
- [ ] Performance optimization review
- [ ] Capacity planning
- [ ] Security audit
- [ ] Backup verification

---

## Production Deployment Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Security scan completed
- [ ] Performance tested
- [ ] Load tested
- [ ] Documentation updated
- [ ] Monitoring configured
- [ ] Alerting set up
- [ ] Backup strategy in place
- [ ] Rollback plan ready

---

## Support & Resources

### Documentation Files
- `README.md` - Project overview
- `USER_GUIDE.md` - User guide
- `API_DOCUMENTATION.md` - API reference
- `PHASE_4_IMPROVEMENTS.md` - Technical details
- `PHASE_4_INTEGRATION_GUIDE.md` - Integration steps
- `IMPLEMENTATION_CHECKLIST.md` - Progress tracking

### Code References
- `app/utils/advanced_logging.py` - Logging implementation
- `app/utils/metrics.py` - Metrics implementation
- `app/utils/caching.py` - Caching implementation
- `app/utils/analytics.py` - Analytics implementation
- `app/utils/background_tasks.py` - Background jobs

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Docs](https://prometheus.io/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)

---

## Contact & Support

For issues:
1. Check application logs: `logs/app.log`
2. Review metrics: `http://localhost:8000/metrics`
3. Check documentation files
4. Review inline code comments
5. Check GitHub issues

---

**Last Updated:** January 6, 2024
**Version:** 4.0
**Status:** Production Ready ✅
