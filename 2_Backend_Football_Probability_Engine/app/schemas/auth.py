"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginCredentials(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class User(BaseModel):
    """User model"""
    id: str
    email: str
    name: str


class AuthResponse(BaseModel):
    """Authentication response"""
    user: User
    token: str
    refreshToken: Optional[str] = None

