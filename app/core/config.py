from typing import Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Database
    database_url: str = Field(
        default="sqlite:///./voltway.db",
        description="Database URL for SQLAlchemy"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # External APIs
    open_charge_map_api_key: Optional[str] = Field(
        default=None,
        description="API key for Open Charge Map"
    )
    api_ninjas_key: Optional[str] = Field(
        default=None,
        description="API key for API-Ninjas"
    )
    
    # Security
    secret_key: str = Field(
        default="your-secret-key",
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Token expiration time in minutes"
    )
    
    # Environment
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    # Sentry
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )
    
    # Rate limiting
    rate_limit_requests: int = Field(
        default=100,
        ge=1,
        description="Rate limit: number of requests"
    )
    rate_limit_period_seconds: int = Field(
        default=60,
        ge=1,
        description="Rate limit: period in seconds"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Initialize settings with validation
try:
    settings = Settings()
except ValidationError as e:
    print(f"Settings validation error: {e}")
    raise
