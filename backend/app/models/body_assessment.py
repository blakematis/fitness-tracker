"""
Body assessment model for fitness exam snapshots in US units.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BodyAssessment(Base):
    """One body-composition exam snapshot for a user."""

    __tablename__ = "body_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Canonical US units.
    weight_lb: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    lean_mass_lb: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    fat_mass_lb: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    muscle_mass_lb: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    visceral_fat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    waist_in: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    hip_in: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    chest_in: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    thigh_in: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    arm_in: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    calf_in: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
