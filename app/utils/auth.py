from datetime import datetime, timedelta
from typing import Optional
import secrets

# Import bcrypt directly to avoid initialization issues
import bcrypt
import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.user import TokenData
from app.utils import logging
from app.utils.logging import log_security_event


# Logger
logger = logging.get_logger(__name__)


# Password hashing functions
def hash_password_direct(password: str) -> str:
    """Hash a password using bcrypt directly"""
    # Convert password to bytes
    password_bytes = password.encode("utf-8")
    # Generate salt and hash
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    # Return as string
    return hashed.decode("utf-8")


def verify_password_direct(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt directly"""
    try:
        plain_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        result = bcrypt.checkpw(plain_bytes, hash_bytes)
        return result
    except Exception as e:
        logger.error(f"Error in password verification: {e}")
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    try:
        result = verify_password_direct(plain_password, hashed_password)
        log_security_event(
            "password_verification",
            success=result,
            password_length=len(plain_password) if plain_password else 0,
        )
        return result
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        log_security_event("password_verification", success=False, error=str(e))
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        # Bcrypt has a 72-byte password length limit, so we truncate if necessary
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            truncated_bytes = password_bytes[:72]
            truncated_password = truncated_bytes.decode("utf-8", errors="ignore")
        else:
            truncated_password = password

        return hash_password_direct(truncated_password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


# API Key hashing functions
def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using bcrypt.

    Args:
        api_key: The plain text API key

    Returns:
        The hashed API key
    """
    try:
        key_bytes = api_key.encode("utf-8")
        hashed = bcrypt.hashpw(key_bytes, bcrypt.gensalt())
        return hashed.decode("utf-8")
    except Exception as e:
        logger.error(f"Error hashing API key: {e}")
        raise


def verify_api_key(plain_api_key: str, hashed_key: str) -> bool:
    """
    Verify a plain API key against a hashed key.

    Args:
        plain_api_key: The plain text API key
        hashed_key: The hashed API key from database

    Returns:
        True if the key matches, False otherwise
    """
    try:
        plain_bytes = plain_api_key.encode("utf-8")
        hash_bytes = hashed_key.encode("utf-8")
        result = bcrypt.checkpw(plain_bytes, hash_bytes)

        log_security_event(
            "api_key_verification",
            success=result,
            key_length=len(plain_api_key) if plain_api_key else 0,
        )
        return result
    except Exception as e:
        logger.error(f"Error verifying API key: {e}")
        log_security_event("api_key_verification", success=False, error=str(e))
        return False


def generate_api_key() -> str:
    """
    Generate a secure random API key.

    Returns:
        A secure random API key (48 characters)
    """
    # Use secrets.token_urlsafe for cryptographically secure random string
    return secrets.token_urlsafe(36)  # 48 characters


def get_api_key_prefix(api_key: str) -> str:
    """
    Get the prefix of an API key for identification.

    Args:
        api_key: The API key

    Returns:
        First 8 characters of the key
    """
    return api_key[:8] if len(api_key) >= 8 else api_key


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
