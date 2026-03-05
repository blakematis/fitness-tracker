"""Tests for user metrics privacy and super-admin access controls."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.auth.password import hash_password
from app.database import async_session_factory
from app.models import AdminAccessAudit, BodyAssessment, User


async def _register_and_login(client: AsyncClient, email: str, password: str) -> str:
    await client.post("/api/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


async def _create_super_admin(email: str = "super@example.com", password: str = "superpass123") -> str:
    async with async_session_factory() as session:
        user = User(email=email, hashed_password=hash_password(password), role="super_admin")
        session.add(user)
        await session.commit()
    return password


def _metric_payload(weight: float = 180.5) -> dict:
    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "weight_lb": weight,
        "body_fat_pct": 18.5,
        "lean_mass_lb": 147.0,
        "source": "manual",
    }


def _inbody_csv(weight: float, body_fat_pct: float, visceral_fat_level: float) -> str:
    return (
        "date,Measurement device.,Weight(lb),Skeletal Muscle Mass(lb),Soft Lean Mass(lb),"
        "Body Fat Mass(lb),BMI(kg/m²),Percent Body Fat(%),Basal Metabolic Rate(kJ),InBody Score,"
        "Right Arm Lean Mass(lb),Left Arm Lean Mass(lb),Trunk Lean Mass(lb),Right Leg Lean Mass(lb),"
        "Left leg Lean Mass(lb),Right Arm Fat Mass(lb),Left Arm Fat Mass(lb),Trunk Fat Mass(lb),"
        "Right Leg Fat Mass(lb),Left Leg Fat Mass(lb),Right Arm ECW Ratio,Left Arm ECW Ratio,"
        "Trunk ECW Ratio,Right Leg ECW Ratio,Left Leg ECW Ratio,Waist Hip Ratio,Waist Circumference(inch),"
        "Visceral Fat Area(cm²),Visceral Fat Level(Level),Total Body Water(lb),Intracellular Water(lb),"
        "Extracellular Water(lb),ECW Ratio,Upper-Lower,Upper,Lower,Leg Muscle Level(Level),Leg Lean Mass(lb),"
        "Protein(lb),Mineral(lb),Bone Mineral Content(lb),Body Cell Mass(lb),SMI(kg/m²),Whole Body Phase Angle(°)\n"
        f"20260305073323,H30,{weight},92.2,150.4,41.9,30.5,{body_fat_pct},8063,90.0,"
        "-,-,-,-,-,-,-,-,-,-,-,-,-,-,-,0.93,35.1,-,"
        f"{visceral_fat_level},-,-,-,-,1,-,-,-,-,-,-,-,-,-,-\n"
    )


@pytest.mark.asyncio
async def test_user_only_sees_own_metrics(client: AsyncClient):
    token_a = await _register_and_login(client, "a@example.com", "pass12345")
    token_b = await _register_and_login(client, "b@example.com", "pass12345")

    create = await client.post("/api/metrics", json=_metric_payload(181.2), headers={"Authorization": f"Bearer {token_a}"})
    assert create.status_code == 200
    metric_id = create.json()["id"]

    my_list = await client.get("/api/metrics/me", headers={"Authorization": f"Bearer {token_a}"})
    assert my_list.status_code == 200
    assert len(my_list.json()) == 1

    other_get = await client.get(f"/api/metrics/me/{metric_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert other_get.status_code == 404


@pytest.mark.asyncio
async def test_non_admin_cannot_use_admin_metrics_routes(client: AsyncClient):
    token = await _register_and_login(client, "user@example.com", "pass12345")
    response = await client.post(
        "/api/metrics/admin/obfuscated",
        json={"reason": "Support request requires trend review"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_obfuscated_view_and_raw_audit(client: AsyncClient):
    user_token = await _register_and_login(client, "metric.user@example.com", "pass12345")
    create = await client.post("/api/metrics", json=_metric_payload(199.0), headers={"Authorization": f"Bearer {user_token}"})
    assert create.status_code == 200
    target_user_id = create.json()["user_id"]

    admin_password = await _create_super_admin()
    admin_login = await client.post("/api/auth/login", json={"email": "super@example.com", "password": admin_password})
    admin_token = admin_login.json()["access_token"]

    obfuscated = await client.post(
        "/api/metrics/admin/obfuscated",
        json={"reason": "Investigating aggregate trend anomalies"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert obfuscated.status_code == 200
    data = obfuscated.json()
    assert len(data) == 1
    assert data[0]["masked_email"].startswith("me***@")
    assert "user_ref" in data[0]
    assert "user_id" not in data[0]

    too_short_reason = await client.post(
        f"/api/metrics/admin/raw/{target_user_id}",
        json={"reason": "too short"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert too_short_reason.status_code == 422

    raw = await client.post(
        f"/api/metrics/admin/raw/{target_user_id}",
        json={"reason": "User requested account data recovery support"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert raw.status_code == 200
    assert len(raw.json()) == 1

    async with async_session_factory() as session:
        audits = await session.execute(select(AdminAccessAudit).order_by(AdminAccessAudit.id))
        entries = list(audits.scalars().all())
        assert len(entries) == 2
        assert entries[0].action == "view_obfuscated_metrics"
        assert entries[0].obfuscated is True
        assert entries[1].action == "view_raw_metrics"
        assert entries[1].obfuscated is False
        assert entries[1].target_user_id == target_user_id

        metrics = await session.execute(select(BodyAssessment))
        assert len(list(metrics.scalars().all())) == 1


@pytest.mark.asyncio
async def test_upload_inbody_csv_creates_metric(client: AsyncClient):
    token = await _register_and_login(client, "upload@example.com", "pass12345")
    csv_payload = _inbody_csv(weight=200.8, body_fat_pct=20.9, visceral_fat_level=8.0)
    response = await client.post(
        "/api/metrics/upload/inbody",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("inbody.csv", csv_payload, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json() == {"total_rows": 1, "inserted": 1, "updated": 0}

    async with async_session_factory() as session:
        result = await session.execute(select(BodyAssessment))
        metrics = list(result.scalars().all())
        assert len(metrics) == 1
        assert float(metrics[0].weight_lb) == 200.8
        assert float(metrics[0].body_fat_pct) == 20.9
        assert metrics[0].visceral_fat_score == 8
        assert metrics[0].source == "inbody:H30"


@pytest.mark.asyncio
async def test_upload_inbody_csv_updates_existing_measurement(client: AsyncClient):
    token = await _register_and_login(client, "upload-update@example.com", "pass12345")
    first = await client.post(
        "/api/metrics/upload/inbody",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("inbody.csv", _inbody_csv(weight=200.8, body_fat_pct=20.9, visceral_fat_level=8.0), "text/csv")},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/metrics/upload/inbody",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("inbody.csv", _inbody_csv(weight=199.2, body_fat_pct=19.7, visceral_fat_level=7.0), "text/csv")},
    )
    assert second.status_code == 200
    assert second.json() == {"total_rows": 1, "inserted": 0, "updated": 1}

    async with async_session_factory() as session:
        result = await session.execute(select(BodyAssessment))
        metrics = list(result.scalars().all())
        assert len(metrics) == 1
        assert float(metrics[0].weight_lb) == 199.2
        assert float(metrics[0].body_fat_pct) == 19.7
        assert metrics[0].visceral_fat_score == 7
