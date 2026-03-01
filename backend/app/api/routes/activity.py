"""
Daily activity metric routes with per-user ownership controls.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import DailyActivityMetric, User
from app.schemas import DailyActivityMetricCreate, DailyActivityMetricResponse

router = APIRouter()


@router.post("/daily", response_model=DailyActivityMetricResponse)
async def upsert_daily_metric(
    body: DailyActivityMetricCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DailyActivityMetric:
    """
    Create or update one daily metric row for the current user and date.
    """
    existing_result = await db.execute(
        select(DailyActivityMetric).where(
            DailyActivityMetric.user_id == user.id,
            DailyActivityMetric.metric_date == body.metric_date,
        )
    )
    existing = existing_result.scalar_one_or_none()
    payload = body.model_dump()
    if existing is None:
        metric = DailyActivityMetric(user_id=user.id, **payload)
        db.add(metric)
        await db.flush()
        await db.refresh(metric)
        return metric

    for key, value in payload.items():
        setattr(existing, key, value)
    await db.flush()
    await db.refresh(existing)
    return existing


@router.get("/daily", response_model=list[DailyActivityMetricResponse])
async def list_daily_metrics(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DailyActivityMetric]:
    """
    List current user's daily activity metrics with optional date range.
    """
    query = select(DailyActivityMetric).where(DailyActivityMetric.user_id == user.id)
    if from_date is not None:
        query = query.where(DailyActivityMetric.metric_date >= from_date)
    if to_date is not None:
        query = query.where(DailyActivityMetric.metric_date <= to_date)
    query = query.order_by(desc(DailyActivityMetric.metric_date))
    result = await db.execute(query)
    return list(result.scalars().all())
