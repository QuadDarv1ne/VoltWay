# Changelog

All notable changes to VoltWay project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository pattern implementation for better data access layer
- Structured JSON logging for improved observability
- Request ID middleware for distributed tracing
- Enhanced health check endpoints with dependency status
- Dependency injection system for better testability
- Response compression middleware (gzip)
- Performance indexes for database queries
- Repository layer tests
- Docker image optimization with multi-stage builds
- .dockerignore for smaller image sizes
- Development docker-compose overrides
- Connection pooling for database with configurable settings

### Changed
- Optimized Dockerfile with smaller image size
- Improved database configuration with connection pooling
- Enhanced health check endpoints (basic, detailed, ready, live)
- Updated docker-compose health checks to use new endpoints

### Fixed
- Database connection management with proper cleanup
- Health check paths in docker-compose

### Security
- Non-root user in Docker container
- Proper file permissions in Docker image
- SQL injection prevention in repository layer

## [1.0.0] - 2026-01-06

### Added
- Initial release
- FastAPI backend with async support
- PostgreSQL and SQLite database support
- Redis caching layer
- WebSocket notifications
- Interactive map with Leaflet
- Station search and filtering
- User authentication
- Favorites system
- External API integration (Open Charge Map, API-Ninjas)
- Docker support
- Monitoring and metrics
- Rate limiting
- CORS configuration
- Comprehensive API documentation

[Unreleased]: https://github.com/QuadDarv1ne/VoltWay/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/QuadDarv1ne/VoltWay/releases/tag/v1.0.0
