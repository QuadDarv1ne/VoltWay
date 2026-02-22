import secrets
from typing import Optional

from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""

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

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is sufficiently random and long"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file


# Initialize settings with validation
try:
    settings = Settings()
except ValidationError as e:
    print(f"Settings validation error: {e}")
    raise
