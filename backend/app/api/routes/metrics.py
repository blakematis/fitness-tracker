"""
Metrics endpoints with strict ownership and super-admin privacy controls.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_super_admin, get_current_user
from app.database import get_db
from app.models import AdminAccessAudit, BodyAssessment, User
from app.schemas import (
    AdminObfuscatedMetric,
    AdminRawMetricsRequest,
    BodyAssessmentCreate,
    BodyAssessmentResponse,
)

router = APIRouter()


def _mask_email(email: str) -> str:
    local, sep, domain = email.partition("@")
    if not sep:
        return "***"
    local_masked = (local[:2] + "***") if len(local) > 2 else "***"
    domain_parts = domain.split(".")
    if len(domain_parts) > 1:
        domain_masked = "***." + domain_parts[-1]
    else:
        domain_masked = "***"
    return f"{local_masked}@{domain_masked}"


@router.post("", response_model=BodyAssessmentResponse)
async def create_my_metric(
    body: BodyAssessmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BodyAssessment:
    """Create a metric snapshot for the authenticated user."""
    metric = BodyAssessment(user_id=user.id, **body.model_dump())
    db.add(metric)
    await db.flush()
    await db.refresh(metric)
    return metric


@router.get("/me", response_model=list[BodyAssessmentResponse])
async def list_my_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BodyAssessment]:
    """List only the authenticated user's metrics."""
    result = await db.execute(
        select(BodyAssessment)
        .where(BodyAssessment.user_id == user.id)
        .order_by(desc(BodyAssessment.measured_at))
    )
    return list(result.scalars().all())


@router.get("/me/{metric_id}", response_model=BodyAssessmentResponse)
async def get_my_metric(
    metric_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BodyAssessment:
    """Fetch one metric owned by the authenticated user."""
    result = await db.execute(
        select(BodyAssessment).where(
            BodyAssessment.id == metric_id,
            BodyAssessment.user_id == user.id,
        )
    )
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found")
    return metric


@router.post("/admin/obfuscated", response_model=list[AdminObfuscatedMetric])
async def list_obfuscated_metrics(
    body: AdminRawMetricsRequest,
    admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminObfuscatedMetric]:
    """
    Super-admin safe view: obfuscated user identity and limited fields.
    """
    rows = await db.execute(
        select(BodyAssessment, User)
        .join(User, User.id == BodyAssessment.user_id)
        .order_by(desc(BodyAssessment.measured_at))
        .limit(200)
    )
    payload: list[AdminObfuscatedMetric] = []
    for metric, metric_user in rows.all():
        payload.append(
            AdminObfuscatedMetric(
                user_ref=f"user-{metric_user.id:06d}",
                masked_email=_mask_email(metric_user.email),
                measured_at=metric.measured_at,
                weight_lb=float(metric.weight_lb),
                body_fat_pct=float(metric.body_fat_pct) if metric.body_fat_pct is not None else None,
                lean_mass_lb=float(metric.lean_mass_lb) if metric.lean_mass_lb is not None else None,
                source=metric.source,
            )
        )
    db.add(
        AdminAccessAudit(
            admin_user_id=admin.id,
            target_user_id=None,
            action="view_obfuscated_metrics",
            reason=body.reason,
            obfuscated=True,
        )
    )
    return payload


@router.post("/admin/raw/{target_user_id}", response_model=list[BodyAssessmentResponse])
async def list_user_metrics_raw(
    target_user_id: int,
    body: AdminRawMetricsRequest,
    admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
) -> list[BodyAssessment]:
    """
    Break-glass raw access for super-admins with mandatory reason and audit trail.
    """
    result = await db.execute(
        select(BodyAssessment)
        .where(BodyAssessment.user_id == target_user_id)
        .order_by(desc(BodyAssessment.measured_at))
    )
    metrics = list(result.scalars().all())
    db.add(
        AdminAccessAudit(
            admin_user_id=admin.id,
            target_user_id=target_user_id,
            action="view_raw_metrics",
            reason=body.reason,
            obfuscated=False,
        )
    )
    return metrics
