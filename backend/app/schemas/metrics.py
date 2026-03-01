"""
Schemas for user body assessments and privileged admin metric views.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class BodyAssessmentBase(BaseModel):
    """US-unit body assessment fields."""

    measured_at: datetime
    weight_lb: float = Field(gt=0)
    body_fat_pct: float | None = Field(default=None, ge=0, le=70)
    lean_mass_lb: float | None = Field(default=None, ge=0)
    fat_mass_lb: float | None = Field(default=None, ge=0)
    muscle_mass_lb: float | None = Field(default=None, ge=0)
    waist_in: float | None = Field(default=None, ge=0)
    hip_in: float | None = Field(default=None, ge=0)
    chest_in: float | None = Field(default=None, ge=0)
    thigh_in: float | None = Field(default=None, ge=0)
    arm_in: float | None = Field(default=None, ge=0)
    calf_in: float | None = Field(default=None, ge=0)
    source: str = "manual"
    notes: str | None = None


class BodyAssessmentCreate(BodyAssessmentBase):
    """Request body for creating a body assessment."""


class BodyAssessmentResponse(BodyAssessmentBase):
    """Body assessment returned by API routes."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminObfuscatedMetric(BaseModel):
    """Privacy-safe metric view for super-admins."""

    user_ref: str
    masked_email: str
    measured_at: datetime
    weight_lb: float
    body_fat_pct: float | None = None
    lean_mass_lb: float | None = None
    source: str


class AdminRawMetricsRequest(BaseModel):
    """Reason is required for raw metric access."""

    reason: str = Field(min_length=10, max_length=500)
