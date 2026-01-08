# VoltWay API Documentation

## Overview
VoltWay is an interactive electric vehicle charging station map with real-time notifications and favorites functionality.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Most endpoints require authentication using JWT Bearer tokens.

### Get Access Token
**POST** `/auth/token`

Request body:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Stations Endpoints

### Get All Stations
**GET** `/stations`

Query Parameters:
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)
- `latitude` (float, optional): Filter by latitude
- `longitude` (float, optional): Filter by longitude
- `radius_km` (int, optional): Radius in kilometers for geographic filtering
- `connector_type` (string, optional): Filter by connector type (CCS, CHAdeMO, Type 2)
- `min_power_kw` (float, optional): Minimum power in kW
- `status` (string, optional): Filter by status (available, occupied, maintenance, unknown)

Response:
```json
[
  {
    "id": 1,
    "title": "Зарядная станция ТЦ Атриум",
    "address": "Москва, ул. Земляной Вал, 33",
    "latitude": 55.7568,
    "longitude": 37.6591,
    "connector_type": "CCS",
    "power_kw": 50.0,
    "status": "available",
    "price": 15.0,
    "hours": "24/7",
    "last_updated": "2026-01-04T15:45:47.178939"
  }
]
```

### Get Station by ID
**GET** `/stations/{station_id}`

Response:
```json
{
  "id": 1,
  "title": "Зарядная станция ТЦ Атриум",
  "address": "Москва, ул. Земляной Вал, 33",
  "latitude": 55.7568,
  "longitude": 37.6591,
  "connector_type": "CCS",
  "power_kw": 50.0,
  "status": "available",
  "price": 15.0,
  "hours": "24/7",
  "last_updated": "2026-01-04T15:45:47.178939"
}
```

### Update Cache from External API
**POST** `/stations/update_cache`

Query Parameters:
- `latitude` (float, required): Latitude for cache update
- `longitude` (float, required): Longitude for cache update
- `radius` (int, required): Radius in kilometers

Response:
```json
{
  "message": "Cache update started in background"
}
```

## Favorites Endpoints

### Add Station to Favorites
**POST** `/favorites/{station_id}`

Requires authentication.

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "station_id": 5,
  "created_at": "2026-01-08T15:30:00"
}
```

### Remove Station from Favorites
**DELETE** `/favorites/{station_id}`

Requires authentication.

Response:
```json
{
  "message": "Station removed from favorites"
}
```

### Get My Favorites
**GET** `/favorites/`

Query Parameters:
- `skip` (int, optional): Number of records to skip
- `limit` (int, optional): Maximum number of records to return

Requires authentication.

Response:
```json
[
  {
    "id": 1,
    "user_id": 1,
    "station_id": 5,
    "created_at": "2026-01-08T15:30:00"
  }
]
```

### Check if Station is Favorited
**GET** `/favorites/check/{station_id}`

Requires authentication.

Response:
```json
{
  "is_favorite": true
}
```

### Get Favorite Count for Station
**GET** `/favorites/count/{station_id}`

Response:
```json
{
  "favorite_count": 15
}
```

## Notifications Endpoints

### Get Notification Statistics
**GET** `/notifications/stats`

Response:
```json
{
  "connected_users": 5,
  "subscriptions": {
    "1": 3,
    "2": 1,
    "5": 2
  }
}
```

### Send Test Notification (Admin Only)
**POST** `/notifications/test/{station_id}`

Query Parameters:
- `message` (string, optional): Custom message

Requires authentication and admin privileges.

Response:
```json
{
  "message": "Test notification sent"
}
```

### Trigger Availability Notification
**POST** `/notifications/trigger/{station_id}`

Query Parameters:
- `is_available` (boolean, required): New availability status

Requires authentication and admin privileges.

Response:
```json
{
  "message": "Availability notification triggered for station 5"
}
```

## Cache Management Endpoints

### Get Cache Cleanup Statistics
**GET** `/monitoring/cache-cleanup/stats`

Response:
```json
{
  "total_entries": 150,
  "station_entries": 120,
  "other_entries": 30,
  "memory_usage": "25.42M",
  "running": true,
  "cleanup_interval": 300,
  "max_cache_size": 1000,
  "max_memory_usage_mb": 100.0
}
```

### Start Automatic Cache Cleanup
**POST** `/monitoring/cache-cleanup/start`

Response:
```json
{
  "message": "Cache cleanup scheduler started"
}
```

### Stop Automatic Cache Cleanup
**POST** `/monitoring/cache-cleanup/stop`

Response:
```json
{
  "message": "Cache cleanup scheduler stopped"
}
```

### Perform Manual Cache Cleanup
**POST** `/monitoring/cache-cleanup/manual`

Response:
```json
{
  "message": "Manual cache cleanup completed",
  "stats": {
    "total_entries": 145,
    "station_entries": 115,
    "other_entries": 30,
    "memory_usage": "24.15M"
  }
}
```

### Warm Cache
**POST** `/monitoring/warm-cache`

Query Parameters:
- `latitude` (float, optional): Latitude for cache warming (default: 55.7558)
- `longitude` (float, optional): Longitude for cache warming (default: 37.6173)
- `radius_km` (int, optional): Radius in kilometers (default: 10)

Response:
```json
{
  "message": "Cache warming initiated for 3 queries",
  "queries_warmed": 3
}
```

## Temporary Files Management Endpoints

### Get Temporary Files Statistics
**GET** `/monitoring/temp-files/stats`

Response:
```json
{
  "message": "Temporary files statistics",
  "stats": {
    "temp_directories": [
      {
        "path": "C:\\Users\\user\\project\\tmp",
        "size_bytes": 102400
      }
    ],
    "temp_files": [
      {
        "path": "C:\\Users\\user\\project\\temp_file.tmp",
        "size_bytes": 1024
      }
    ],
    "total_size_bytes": 103424
  },
  "total_size_mb": 0.1
}
```

### Manual Temporary Files Cleanup
**POST** `/monitoring/temp-files/cleanup`

Response:
```json
{
  "message": "Temporary files cleanup completed",
  "cleaned_count": 15,
  "error_count": 0,
  "errors": []
}
```

### Simulate Shutdown Cleanup
**POST** `/monitoring/temp-files/cleanup-on-shutdown`

Response:
```json
{
  "message": "Shutdown cleanup simulation completed",
  "cleaned_count": 23,
  "error_count": 1
}
```

## User Management Endpoints

### Create New User
**POST** `/users/`

Request body:
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123"
}
```

Response:
```json
{
  "id": 10,
  "username": "newuser",
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-01-08T15:30:00",
  "updated_at": "2026-01-08T15:30:00"
}
```

### Get Current User Info
**GET** `/users/me`

Requires authentication.

Response:
```json
{
  "id": 1,
  "username": "currentuser",
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-01-01T10:00:00",
  "updated_at": "2026-01-08T15:30:00"
}
```

## Utility Endpoints

### Root Endpoint
**GET** `/`

Response:
```json
{
  "message": "Welcome to VoltWay API"
}
```

### Health Check
**GET** `/health`

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T15:30:00Z"
}
```

## Error Responses

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

Error response format:
```json
{
  "detail": "Error message"
}
```

## WebSocket Notifications

Connect to WebSocket endpoint: `ws://localhost:8000/ws`

### Events

**Client Events:**
- `subscribe_to_station`: Subscribe to station notifications
  ```json
  {
    "station_id": 5
  }
  ```

- `unsubscribe_from_station`: Unsubscribe from station notifications
  ```json
  {
    "station_id": 5
  }
  ```

**Server Events:**
- `subscribed`: Confirmation of subscription
  ```json
  {
    "station_id": 5
  }
  ```

- `unsubscribed`: Confirmation of unsubscription
  ```json
  {
    "station_id": 5
  }
  ```

- `notification`: Station update notification
  ```json
  {
    "type": "availability_change",
    "station_id": 5,
    "is_available": true,
    "message": "Станция освободилась",
    "timestamp": 1234567890.123
  }
  ```

## Rate Limiting
Currently no rate limiting is implemented.

## CORS Policy
CORS is configured to allow:
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:8000`

## Data Validation

### Coordinates
- Latitude: -90 to 90 degrees
- Longitude: -180 to 180 degrees

### Power
- Must be positive value

### Status
Valid values: `available`, `occupied`, `maintenance`, `unknown`

### Connector Types
Valid values: `CCS`, `CHAdeMO`, `Type 2`