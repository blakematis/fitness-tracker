"""
Daily fitness metrics in canonical US units.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyActivityMetric(Base):
    """Per-user daily aggregate metrics from wearable/integration providers."""

    __tablename__ = "daily_activity_metrics"
    __table_args__ = (UniqueConstraint("user_id", "metric_date", name="uq_daily_metric_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_calories: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    total_calories_burned: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    distance_miles: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    active_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_pace_sec_per_mile: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
