# 🚀 VoltWay - Deployment Guide

## Quick Start - Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup .env
cp .env.example .env

# 3. Run with auto-reload
uvicorn app.main:app --reload

# 4. Access API
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/redoc (ReDoc)
```

## Production Deployment with Docker

### Prerequisites
- Docker 20+
- Docker Compose 2+

### Setup

```bash
# 1. Setup environment
cp .env.production .env

# Edit .env with your values:
# - DB_PASSWORD
# - SENTRY_DSN
# - SECRET_KEY

# 2. Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 3. Check status
docker-compose -f docker-compose.prod.yml ps

# 4. View logs
docker-compose -f docker-compose.prod.yml logs -f app
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run integration tests
pytest tests/test_integration.py -v

# Check code quality
flake8 app/
black --check app/
mypy app/
```

## CI/CD Pipeline

GitHub Actions workflows are configured in `.github/workflows/`:

1. **ci-cd.yml** - Main pipeline
   - Tests on Python 3.8-3.11
   - Code linting (Black, Flake8, isort)
   - Security checks (Bandit, Safety)
   - Docker build
   - Auto-deploy on main branch

2. **code-quality.yml** - Code quality checks
   - Complexity analysis (Radon)
   - Linting (Pylint)
   - Test execution

### Triggering CI/CD

Workflows run automatically on:
- Push to `main` or `develop`
- Pull requests

## API Versioning

### V1 (Current Stable)
- Endpoint: `/api/v1/`
- Features: Core functionality, rate limiting

### V2 (Next Generation)
- Endpoint: `/api/v2/`
- Features: Enhanced error handling, batch operations

Both versions run in parallel for backward compatibility.

## Database Optimization

### Indices
Automatically created for:
- Station location (latitude, longitude)
- Connector types
- User email
- Favorites lookup

### Query Optimization
See `app/utils/db_optimization.py` for:
- Query optimization tips
- EXPLAIN plan examples
- Best practices

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
- Application logs go to console
- Sentry integration for error tracking
- Nginx access logs in docker

### Performance Monitoring
- Add Prometheus/Grafana for metrics
- Use py-spy for profiling
- Monitor database query times

## Scaling

### Horizontal Scaling
```bash
# Multiple app instances behind Nginx
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

### Database
- Use PostgreSQL for production (not SQLite)
- Enable connection pooling (pgBouncer)
- Regular backups

### Caching
- Redis for session/cache
- Increase cache TTL for less frequently updated data

## Troubleshooting

### Port already in use
```bash
# Change port in docker-compose.prod.yml or use:
docker-compose -f docker-compose.prod.yml down
```

### Database connection errors
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml logs db

# Recreate database
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

### Out of memory
```bash
# Check resource limits
docker stats

# Increase in docker-compose.prod.yml or system settings
```

## Security Checklist

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=false` in production
- [ ] Configure HTTPS/SSL
- [ ] Set up firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable Sentry for error tracking
- [ ] Regular dependency updates
- [ ] Use strong database password

## Useful Commands

```bash
# View environment
docker-compose -f docker-compose.prod.yml config

# Run migrations (if using Alembic)
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Run shell
docker-compose -f docker-compose.prod.yml exec app bash

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Clean up volumes
docker-compose -f docker-compose.prod.yml down -v

# Update dependencies
pip install --upgrade -r requirements.txt

# Format code
black app/
isort app/
```

## Next Steps

1. Configure SSL/HTTPS
2. Set up monitoring and alerting
3. Configure backup strategy
4. Set up staging environment
5. Document API endpoints
6. Create deployment runbook

---

For more information, see the main README.md or API documentation at `/docs`.
