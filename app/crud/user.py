from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.auth import get_password_hash


def get_user_by_username(db: Session, username: str):
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get list of users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate):
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_active=user.is_active,
        is_admin=user.is_admin,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate):
    """Update user information"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    """Delete a user"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    db.delete(db_user)
    db.commit()
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user by username and password"""
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    from app.utils.auth import verify_password as auth_verify_password

    return auth_verify_password(plain_password, hashed_password)
