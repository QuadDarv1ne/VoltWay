from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.schemas.user import TokenData
from app.utils import logging


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Logger
logger = logging.get_logger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)  # Default 30 minutes
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify a JWT token and return the token data"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)
        
        if username is None:
            return None
        
        token_data = TokenData(username=username, is_admin=is_admin)
        return token_data
    except jwt.exceptions.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.exceptions.JWTError as e:
        logger.error(f"Error decoding token: {e}")
        return None