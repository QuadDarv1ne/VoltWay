"""
Application settings with validation and environment-based configuration.
"""

import secrets
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    app_name: str = Field(default="VoltWay", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")

    # Database
    database_url: str = Field(
        default="sqlite:///./voltway.db", description="Database URL for SQLAlchemy"
    )

    # PostgreSQL Configuration (for Docker)
    postgres_db: str = Field(default="voltway", description="PostgreSQL database name")
    postgres_user: str = Field(
        default="voltway_user", description="PostgreSQL username"
    )
    postgres_password: str = Field(
        default="voltway_password", description="PostgreSQL password"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )
    redis_enabled: bool = Field(
        default=True, description="Enable Redis caching"
    )

    # External APIs
    open_charge_map_api_key: Optional[str] = Field(
        default=None, description="API key for Open Charge Map"
    )
    api_ninjas_key: Optional[str] = Field(
        default=None, description="API key for API-Ninjas"
    )

    # Security
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT tokens",
    )
    access_token_expire_minutes: int = Field(
        default=30, ge=1, le=1440, description="Token expiration time in minutes"
    )

    # Environment
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # Sentry
    sentry_dsn: Optional[str] = Field(
        default=None, description="Sentry DSN for error tracking"
    )

    # Rate limiting
    rate_limit_requests: int = Field(
        default=100, ge=1, description="Rate limit: number of requests"
    )
    rate_limit_period_seconds: int = Field(
        default=60, ge=1, description="Rate limit: period in seconds"
    )

    # CORS
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Performance
    enable_compression: bool = Field(
        default=True, description="Enable gzip compression"
    )
    compression_minimum_size: int = Field(
        default=500, ge=0, description="Minimum response size for compression (bytes)"
    )

    # Database
    use_postgis: bool = Field(
        default=False, description="Use PostGIS for geospatial queries"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is sufficiently random and long"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file


# Initialize settings with validation
settings = Settings()
