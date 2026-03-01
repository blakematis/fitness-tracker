"""
Schemas for daily activity metrics.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class DailyActivityMetricCreate(BaseModel):
    """Request payload for creating/updating a daily metric row."""

    metric_date: date
    steps: int | None = Field(default=None, ge=0)
    active_calories: float | None = Field(default=None, ge=0)
    total_calories_burned: float | None = Field(default=None, ge=0)
    distance_miles: float | None = Field(default=None, ge=0)
    active_minutes: int | None = Field(default=None, ge=0)
    avg_pace_sec_per_mile: float | None = Field(default=None, ge=0)


class DailyActivityMetricResponse(DailyActivityMetricCreate):
    """Daily activity metric row returned by API routes."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
