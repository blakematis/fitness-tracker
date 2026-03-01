"""
Goal CRUD routes with strict per-user access.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Goal, User
from app.schemas import GoalCreate, GoalResponse, GoalUpdate

router = APIRouter()


@router.post("", response_model=GoalResponse)
async def create_goal(
    body: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Goal:
    """Create a goal for the authenticated user."""
    goal = Goal(user_id=user.id, **body.model_dump())
    db.add(goal)
    await db.flush()
    await db.refresh(goal)
    return goal


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Goal]:
    """List goals for the authenticated user."""
    result = await db.execute(select(Goal).where(Goal.user_id == user.id).order_by(desc(Goal.created_at)))
    return list(result.scalars().all())


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: int,
    body: GoalUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Goal:
    """Update one goal owned by the authenticated user."""
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    await db.flush()
    await db.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete one goal owned by the authenticated user."""
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    await db.delete(goal)
