# Multi-stage Dockerfile for VoltWay application (optimized)

# Builder stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r voltway && useradd -r -g voltway voltway

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/voltway/.local

# Copy application code
COPY --chown=voltway:voltway app ./app
COPY --chown=voltway:voltway alembic.ini .
COPY --chown=voltway:voltway migrations ./migrations

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads && \
    chown -R voltway:voltway /app

# Switch to non-root user
USER voltway

# Add local bin to PATH
ENV PATH=/home/voltway/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with proper signal handling
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]