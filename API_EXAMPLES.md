# VoltWay API Examples - Phase 4

This file contains practical examples for testing all Phase 4 features.

---

## Health Check Endpoints

### Basic Health Check
```bash
curl http://localhost:8000/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-06T00:00:00Z"
}
```

### API Version 1 Health
```bash
curl http://localhost:8000/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "VoltWay"
}
```

---

## Metrics Endpoint

### Get Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

**Response (200 OK - text/plain):**
```
# HELP request_count Total HTTP requests processed
# TYPE request_count counter
request_count{method="GET",endpoint="/api/v1/stations"} 1234
request_count{method="POST",endpoint="/api/v1/favorites"} 456

# HELP request_duration_seconds Request duration in seconds
# TYPE request_duration_seconds histogram
request_duration_seconds_bucket{le="0.005",endpoint="/api/v1/health"} 100
request_duration_seconds_bucket{le="0.01",endpoint="/api/v1/health"} 102
request_duration_seconds_bucket{le="0.025",endpoint="/api/v1/health"} 103

# HELP cache_hits_total Total cache hits
# TYPE cache_hits_total counter
cache_hits_total{cache_type="redis"} 5000
cache_hits_total{cache_type="memory"} 1000

# HELP cache_misses_total Total cache misses
# TYPE cache_misses_total counter
cache_misses_misses{cache_type="redis"} 50
cache_misses_misses{cache_type="memory"} 100
```

---

## Stations API (with Caching)

### Get All Stations (Cached)
```bash
# First request - cache miss
curl http://localhost:8000/api/v1/stations

# Subsequent requests - cache hit (faster)
curl http://localhost:8000/api/v1/stations?skip=0&limit=10
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Downtown Charging Hub",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "address": "123 Main St, NYC",
      "available_chargers": 5,
      "total_chargers": 10,
      "last_updated": "2024-01-06T10:30:00Z"
    },
    {
      "id": 2,
      "name": "Airport Charging Station",
      "latitude": 40.7769,
      "longitude": -73.8740,
      "address": "JFK Airport, NYC",
      "available_chargers": 3,
      "total_chargers": 8,
      "last_updated": "2024-01-06T10:30:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 10
}
```

### Get Station by ID
```bash
curl http://localhost:8000/api/v1/stations/1
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Downtown Charging Hub",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "address": "123 Main St, NYC",
  "available_chargers": 5,
  "total_chargers": 10,
  "amenities": ["WiFi", "Restroom", "Cafe"],
  "operating_hours": "24/7",
  "pricing": {
    "per_hour": 2.50,
    "per_kwh": 0.25
  },
  "rating": 4.5,
  "reviews": 234,
  "last_updated": "2024-01-06T10:30:00Z"
}
```

### Get Nearby Stations
```bash
curl "http://localhost:8000/api/v1/stations/nearby?latitude=40.7128&longitude=-74.0060&radius_km=5"
```

**Response (200 OK):**
```json
{
  "stations": [
    {
      "id": 1,
      "name": "Downtown Charging Hub",
      "distance_km": 0.0
    },
    {
      "id": 3,
      "name": "Midtown Charger",
      "distance_km": 2.5
    }
  ],
  "center": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "radius_km": 5
}
```

---

## Bulk Operations (Batch Insert)

### Create Multiple Stations
```bash
curl -X POST http://localhost:8000/api/v1/stations/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {
      "name": "Station 1",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "address": "Address 1",
      "total_chargers": 10
    },
    {
      "name": "Station 2",
      "latitude": 40.7580,
      "longitude": -73.9855,
      "address": "Address 2",
      "total_chargers": 8
    }
  ]'
```

**Response (201 Created):**
```json
{
  "created": 2,
  "failed": 0,
  "duration_ms": 245,
  "items_per_second": 8.16
}
```

### Bulk Update Charger Status
```bash
curl -X PUT http://localhost:8000/api/v1/stations/bulk/status \
  -H "Content-Type: application/json" \
  -d {
    "station_ids": [1, 2, 3],
    "available_chargers": 5,
    "status": "operational"
  }
```

**Response (200 OK):**
```json
{
  "updated": 3,
  "failed": 0,
  "duration_ms": 123
}
```

---

## Background Jobs

### Submit Long-Running Task
```bash
curl -X POST http://localhost:8000/api/v1/export/data \
  -H "Content-Type: application/json" \
  -d {
    "format": "csv",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-06"
    }
  }
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "created_at": "2024-01-06T10:00:00Z",
  "estimated_completion": "2024-01-06T10:05:00Z"
}
```

### Check Job Status
```bash
curl http://localhost:8000/api/v1/export/status/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 45,
  "created_at": "2024-01-06T10:00:00Z",
  "started_at": "2024-01-06T10:00:30Z",
  "updated_at": "2024-01-06T10:02:15Z"
}
```

### Download Job Result (When Complete)
```bash
curl http://localhost:8000/api/v1/export/download/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK - CSV file):**
```
station_id,name,latitude,longitude,visits,revenue
1,Downtown Hub,40.7128,-74.0060,5000,12500.00
2,Airport Station,40.7769,-73.8740,3200,8000.00
...
```

---

## Caching Demonstration

### Cached Endpoint - First Request
```bash
# Monitor logs while making first request
tail -f logs/app.log | grep -E "cache_hit|request_duration"

# Make request
curl http://localhost:8000/api/v1/analytics/summary
```

**Log Output (First Request - Cache Miss):**
```json
{
  "level": "INFO",
  "message": "Request completed",
  "duration_ms": 245,
  "cache_hit": false,
  "endpoint": "/api/v1/analytics/summary"
}
```

### Cached Endpoint - Subsequent Request
```bash
# Make same request again
curl http://localhost:8000/api/v1/analytics/summary
```

**Log Output (Subsequent Request - Cache Hit):**
```json
{
  "level": "INFO",
  "message": "Request completed",
  "duration_ms": 3,
  "cache_hit": true,
  "endpoint": "/api/v1/analytics/summary"
}
```

---

## Analytics Endpoints

### Get Popular Stations
```bash
curl "http://localhost:8000/api/v1/analytics/popular-stations?limit=10&days=30"
```

**Response (200 OK):**
```json
{
  "period": "last_30_days",
  "stations": [
    {
      "station_id": 1,
      "name": "Downtown Hub",
      "visits": 5000,
      "revenue": 12500.00,
      "average_rating": 4.5,
      "rank": 1
    },
    {
      "station_id": 3,
      "name": "Midtown Charger",
      "visits": 3200,
      "revenue": 8000.00,
      "average_rating": 4.2,
      "rank": 2
    }
  ]
}
```

### Get Usage Statistics
```bash
curl "http://localhost:8000/api/v1/analytics/station/1/stats?days=30"
```

**Response (200 OK):**
```json
{
  "station_id": 1,
  "period": "last_30_days",
  "statistics": {
    "total_visits": 5000,
    "unique_visitors": 1234,
    "peak_hour": 18,
    "peak_day": "Friday",
    "average_visit_duration_minutes": 45,
    "total_charging_time_hours": 3750,
    "total_revenue": 12500.00,
    "average_rating": 4.5
  }
}
```

### Get User Analytics
```bash
curl "http://localhost:8000/api/v1/analytics/user/123/behavior"
```

**Response (200 OK):**
```json
{
  "user_id": 123,
  "analytics": {
    "total_visits": 42,
    "favorite_stations": {
      "1": 15,
      "2": 10,
      "3": 8
    },
    "average_session_duration_minutes": 35,
    "total_spent": 250.00,
    "first_visit": "2023-12-01T10:00:00Z",
    "last_visit": "2024-01-06T15:30:00Z"
  }
}
```

### Get Recommendations
```bash
curl "http://localhost:8000/api/v1/analytics/user/123/recommendations"
```

**Response (200 OK):**
```json
{
  "user_id": 123,
  "recommendations": [
    {
      "station_id": 5,
      "name": "New Downtown Station",
      "reason": "Popular in your area",
      "predicted_rating": 4.3
    },
    {
      "station_id": 7,
      "name": "Airport Expansion",
      "reason": "High ratings from similar users",
      "predicted_rating": 4.4
    }
  ]
}
```

---

## Error Responses

### 404 Not Found
```bash
curl http://localhost:8000/api/v1/stations/99999
```

**Response (404):**
```json
{
  "error": "Not Found",
  "detail": "Station with id 99999 does not exist",
  "code": "STATION_NOT_FOUND",
  "timestamp": "2024-01-06T10:00:00Z"
}
```

### 400 Bad Request
```bash
curl "http://localhost:8000/api/v1/stations/nearby?latitude=invalid"
```

**Response (400):**
```json
{
  "error": "Bad Request",
  "detail": "Invalid latitude: must be between -90 and 90",
  "code": "INVALID_COORDINATES",
  "timestamp": "2024-01-06T10:00:00Z"
}
```

### 429 Rate Limited
```bash
# Make many requests quickly
for i in {1..101}; do curl http://localhost:8000/api/v1/stations; done
```

**Response (429):**
```json
{
  "error": "Too Many Requests",
  "detail": "Rate limit exceeded: 100 requests per minute",
  "code": "RATE_LIMITED",
  "timestamp": "2024-01-06T10:00:00Z",
  "retry_after": 60
}
```

---

## Monitoring Commands

### View Application Metrics
```bash
# Get all metrics
curl http://localhost:8000/metrics

# Get specific metric
curl http://localhost:8000/metrics | grep request_count

# Filter errors only
curl http://localhost:8000/metrics | grep errors_total
```

### View Application Logs
```bash
# Real-time logs
tail -f logs/app.log

# JSON formatted logs with jq
tail -f logs/app.log | jq .

# Filter specific level
tail -f logs/app.log | jq 'select(.level=="ERROR")'

# Filter by endpoint
tail -f logs/app.log | jq 'select(.endpoint=="/api/v1/stations")'

# View error logs
tail -f logs/error.log | jq .
```

### Check Background Jobs
```python
# In Python shell
from app.utils.background_tasks import job_queue

# Get stats
stats = job_queue.get_stats()
print(f"Total jobs: {stats['total_jobs']}")
print(f"Running: {stats['running']}")
print(f"Completed: {stats['completed']}")
print(f"Failed: {stats['failed']}")
```

---

## Performance Testing

### Load Test with Apache Bench
```bash
# Test 1000 requests with 10 concurrent
ab -n 1000 -c 10 http://localhost:8000/api/v1/stations

# Test with GET parameters
ab -n 1000 -c 10 "http://localhost:8000/api/v1/stations?skip=0&limit=10"
```

### Load Test with wrk
```bash
# Test 100 connections, 10 threads, 30 seconds
wrk -t10 -c100 -d30s http://localhost:8000/api/v1/stations

# Test with custom script
wrk -t10 -c100 -d30s -s test.lua http://localhost:8000/api/v1/stations
```

---

## Testing Checklist

Use these commands to verify all features:

- [ ] Health checks working: `curl http://localhost:8000/health`
- [ ] Metrics endpoint accessible: `curl http://localhost:8000/metrics`
- [ ] API endpoints responding: `curl http://localhost:8000/api/v1/stations`
- [ ] Caching working: Check cache_hit in logs
- [ ] Batch operations: Create multiple items
- [ ] Background jobs: Submit and check status
- [ ] Analytics: Get popular stations and stats
- [ ] Error handling: Test 404, 400, 429 responses
- [ ] Performance: Run load tests

---

## Integration with External Tools

### Prometheus Scrape Configuration
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'voltway'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Query Examples
```
# Request rate per minute
rate(request_count[1m])

# Request latency (p95)
histogram_quantile(0.95, request_duration_seconds)

# Cache hit ratio
cache_hits_total / (cache_hits_total + cache_misses_total)

# Error rate
rate(errors_total[5m])
```

---

## Common Issues & Solutions

### 1. Metrics Not Showing
```bash
# Check if metrics module is imported
curl http://localhost:8000/metrics | head -5

# If empty, restart application
# Check imports in app/main.py
```

### 2. Cache Not Working
```bash
# Verify Redis is running
redis-cli ping

# Check cache hit ratio in metrics
curl http://localhost:8000/metrics | grep cache_hits

# Enable debug logging
export LOG_LEVEL=DEBUG
```

### 3. Slow Requests
```bash
# Check request_duration metrics
curl http://localhost:8000/metrics | grep request_duration

# View slow requests in logs
grep "slow_request" logs/app.log
```

---

**Last Updated:** January 6, 2024
**Version:** 4.0
**Status:** Production Ready ✅
