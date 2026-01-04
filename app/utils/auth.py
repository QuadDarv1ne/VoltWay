from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.schemas.user import TokenData
from app.utils import logging


# Import bcrypt directly to avoid initialization issues
import bcrypt

# Create a custom hashing function using bcrypt directly
def hash_password_direct(password: str) -> str:
    """Hash a password using bcrypt directly"""
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    # Return as string
    return hashed.decode('utf-8')

def verify_password_direct(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt directly"""
    try:
        plain_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception:
        return False

# Logger
logger = logging.get_logger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    try:
        return verify_password_direct(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        # Bcrypt has a 72-byte password length limit, so we truncate if necessary
        # First, encode to bytes to check actual byte length (not character length)
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes and decode back to string
            truncated_bytes = password_bytes[:72]
            # Ensure we don't cut multi-byte characters in the middle
            truncated_password = truncated_bytes.decode('utf-8', errors='ignore')
        else:
            truncated_password = password
        
        return hash_password_direct(truncated_password)
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