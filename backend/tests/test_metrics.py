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
