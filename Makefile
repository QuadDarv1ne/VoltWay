# Makefile for VoltWay project
.PHONY: help install dev-run test build deploy clean logs db-migrate db-reset

# Default target
help:
	@echo "VoltWay Development Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev-run      - Run development server"
	@echo "  make test         - Run tests"
	@echo "  make build        - Build Docker images"
	@echo "  make deploy       - Deploy with docker-compose"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make logs         - Show application logs"
	@echo "  make db-migrate   - Run database migrations"
	@echo "  make db-reset     - Reset database"

# Install dependencies
install:
	pip install -r requirements.txt

# Run development server
dev-run:
	uvicorn app.main:app --reload --port 8000

# Run tests
test:
	python -m pytest tests/ -v

# Build Docker images
build:
	docker-compose build

# Deploy with docker-compose (production)
deploy:
	docker-compose up -d

# Deploy for development
dev-deploy:
	docker-compose -f docker-compose.dev.yml up -d

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf *.log
	docker-compose down -v
	docker-compose -f docker-compose.dev.yml down -v

# Show application logs
logs:
	docker-compose logs -f app

# Run database migrations
db-migrate:
	docker-compose run --rm app alembic upgrade head

# Reset database
db-reset:
	docker-compose down -v
	docker-compose up -d db
	sleep 10
	docker-compose run --rm app alembic upgrade head
	docker-compose run --rm app python add_sample_data.py

# Development commands
dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f app

dev-down:
	docker-compose -f docker-compose.dev.yml down

# Health check
health-check:
	curl -f http://localhost:8000/api/v1/monitoring/health || echo "Service unavailable"

# Format code
format:
	black .
	isort .

# Lint code
lint:
	flake8 .
	mypy .

# Run all quality checks
quality: format lint test
	@echo "Quality checks passed!"

# Create .env file from example
setup-env:
	cp .env.example .env
	@echo "Created .env file. Please edit it with your configuration."