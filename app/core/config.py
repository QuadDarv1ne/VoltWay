import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./voltway.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    open_charge_map_api_key: str = os.getenv("OPEN_CHARGE_MAP_API_KEY")
    api_ninjas_key: str = os.getenv("API_NINJAS_KEY")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"

settings = Settings()