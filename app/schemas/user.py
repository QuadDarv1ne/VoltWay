from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False


class UserCreate(UserBase):
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        return v


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    is_admin: Optional[bool] = False