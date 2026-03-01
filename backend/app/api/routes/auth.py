"""
Authentication endpoints: registration and login.

Register creates a new user and returns their public profile.
Login validates credentials and returns a JWT access token for use
in the Authorization header on protected routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Register a new user with email and password.

    Passwords are hashed with bcrypt before storage. Returns the new user's
    id and email. Raises 400 if the email is already registered.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Authenticate with email and password; return a JWT access token.

    The client should send this token in the Authorization header as
    "Bearer <access_token>" for protected endpoints. Returns 401 if
    credentials are invalid.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(sub=user.id)
    return Token(access_token=access_token)
