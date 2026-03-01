"""
Schemas for user goal CRUD operations.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    """Create a new goal for the current user."""

    goal_type: str = Field(min_length=3, max_length=64)
    period_type: str = Field(default="daily", min_length=3, max_length=32)
    target_value: float = Field(gt=0)
    start_date: date
    end_date: date | None = None
    status: str = Field(default="active", min_length=3, max_length=32)


class GoalUpdate(BaseModel):
    """Partial goal update."""

    goal_type: str | None = Field(default=None, min_length=3, max_length=64)
    period_type: str | None = Field(default=None, min_length=3, max_length=32)
    target_value: float | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = Field(default=None, min_length=3, max_length=32)


class GoalResponse(BaseModel):
    """Goal returned by API routes."""

    id: int
    user_id: int
    goal_type: str
    period_type: str
    target_value: float
    start_date: date
    end_date: date | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
