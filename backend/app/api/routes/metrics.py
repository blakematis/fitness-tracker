"""
Metrics endpoints with strict ownership and super-admin privacy controls.
"""

import csv
import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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
    InBodyCsvUploadResponse,
)

router = APIRouter()

_INBODY_DATE_COL = "date"
_INBODY_DEVICE_COL = "Measurement device."
_INBODY_WEIGHT_COL = "Weight(lb)"
_INBODY_SMM_COL = "Skeletal Muscle Mass(lb)"
_INBODY_SOFT_LEAN_COL = "Soft Lean Mass(lb)"
_INBODY_FAT_MASS_COL = "Body Fat Mass(lb)"
_INBODY_PBF_COL = "Percent Body Fat(%)"
_INBODY_VFL_COL = "Visceral Fat Level(Level)"
_INBODY_WAIST_COL = "Waist Circumference(inch)"

_INBODY_REQUIRED_COLUMNS = {
    _INBODY_DATE_COL,
    _INBODY_WEIGHT_COL,
}


def _parse_optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized == "-":
        return None
    return float(normalized)


def _parse_optional_int(value: str | None) -> int | None:
    parsed = _parse_optional_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def _parse_inbody_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def _measurement_key(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y%m%d%H%M%S")


def _parse_inbody_row(row: dict[str, str]) -> dict[str, object]:
    measured_at = _parse_inbody_timestamp(row[_INBODY_DATE_COL])
    device = (row.get(_INBODY_DEVICE_COL) or "").strip()
    source = f"inbody:{device}" if device else "inbody_csv"
    return {
        "measured_at": measured_at,
        "weight_lb": float(row[_INBODY_WEIGHT_COL]),
        "muscle_mass_lb": _parse_optional_float(row.get(_INBODY_SMM_COL)),
        "lean_mass_lb": _parse_optional_float(row.get(_INBODY_SOFT_LEAN_COL)),
        "fat_mass_lb": _parse_optional_float(row.get(_INBODY_FAT_MASS_COL)),
        "body_fat_pct": _parse_optional_float(row.get(_INBODY_PBF_COL)),
        "visceral_fat_score": _parse_optional_int(row.get(_INBODY_VFL_COL)),
        "waist_in": _parse_optional_float(row.get(_INBODY_WAIST_COL)),
        "source": source,
        "notes": "Imported from InBody CSV upload",
    }


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


@router.post("/upload/inbody", response_model=InBodyCsvUploadResponse)
async def upload_inbody_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InBodyCsvUploadResponse:
    """Ingest an InBody CSV for the authenticated user and upsert by measured_at."""
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty")
    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must be UTF-8 encoded",
        ) from exc

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV header is missing")
    missing_columns = sorted(_INBODY_REQUIRED_COLUMNS - set(reader.fieldnames))
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV is missing required columns: {', '.join(missing_columns)}",
        )

    parsed_rows: list[dict[str, object]] = []
    total_rows = 0
    for line_no, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        total_rows += 1
        try:
            parsed_rows.append(_parse_inbody_row(row))
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV row at line {line_no}: {exc}",
            ) from exc

    if not parsed_rows:
        return InBodyCsvUploadResponse(total_rows=0, inserted=0, updated=0)

    existing_result = await db.execute(
        select(BodyAssessment).where(BodyAssessment.user_id == user.id)
    )
    existing_by_measurement_key = {
        _measurement_key(metric.measured_at): metric for metric in existing_result.scalars().all()
    }

    inserted = 0
    updated = 0
    for parsed in parsed_rows:
        measured_at = parsed["measured_at"]
        measurement_key = _measurement_key(measured_at)
        existing = existing_by_measurement_key.get(measurement_key)
        if existing is None:
            created = BodyAssessment(user_id=user.id, **parsed)
            db.add(created)
            existing_by_measurement_key[measurement_key] = created
            inserted += 1
            continue
        for key, value in parsed.items():
            setattr(existing, key, value)
        updated += 1

    await db.flush()
    return InBodyCsvUploadResponse(total_rows=total_rows, inserted=inserted, updated=updated)


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
