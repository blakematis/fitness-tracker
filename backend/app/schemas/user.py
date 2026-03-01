"""
User- and auth-related Pydantic schemas.

Defines the shape of registration/login requests and of user/token
responses returned by the API.
"""

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Request body for registration and login (email + plain password)."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user data returned by the API (no password)."""

    id: int
    email: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT access token returned after successful login."""

    access_token: str
    token_type: str = "bearer"
