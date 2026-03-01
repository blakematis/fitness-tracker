"""
User-related endpoints (protected by JWT).

/me returns the currently authenticated user's profile, resolved from
the Bearer token in the request.
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.models import User
from app.schemas import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    """
    Return the current user's profile (id and email).

    Requires a valid JWT in the Authorization header. Used to verify
    the token and fetch the logged-in user's data.
    """
    return user
