"""Tests for goals, daily activity metrics, and integration scaffolding routes."""

from datetime import date

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, password: str) -> tuple[str, int]:
    reg = await client.post("/api/auth/register", json={"email": email, "password": password})
    user_id = reg.json()["id"]
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"], user_id


@pytest.mark.asyncio
async def test_goals_crud_with_user_ownership(client: AsyncClient):
    token_a, _ = await _register_and_login(client, "goal.a@example.com", "pass12345")
    token_b, _ = await _register_and_login(client, "goal.b@example.com", "pass12345")

    create = await client.post(
        "/api/goals",
        json={
            "goal_type": "daily_steps",
            "period_type": "daily",
            "target_value": 10000,
            "start_date": date.today().isoformat(),
            "status": "active",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create.status_code == 200
    goal_id = create.json()["id"]

    list_a = await client.get("/api/goals", headers={"Authorization": f"Bearer {token_a}"})
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1

    update_b = await client.patch(
        f"/api/goals/{goal_id}",
        json={"target_value": 12000},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert update_b.status_code == 404

    delete_b = await client.delete(f"/api/goals/{goal_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert delete_b.status_code == 404

    update_a = await client.patch(
        f"/api/goals/{goal_id}",
        json={"target_value": 12000},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert update_a.status_code == 200
    assert float(update_a.json()["target_value"]) == 12000


@pytest.mark.asyncio
async def test_daily_activity_upsert_and_filtering(client: AsyncClient):
    token, _ = await _register_and_login(client, "activity@example.com", "pass12345")

    first = await client.post(
        "/api/activity/daily",
        json={
            "metric_date": "2026-01-01",
            "steps": 8000,
            "active_calories": 450,
            "distance_miles": 3.2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    first_id = first.json()["id"]

    second_upsert = await client.post(
        "/api/activity/daily",
        json={
            "metric_date": "2026-01-01",
            "steps": 9000,
            "active_calories": 500,
            "distance_miles": 3.7,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_upsert.status_code == 200
    assert second_upsert.json()["id"] == first_id
    assert second_upsert.json()["steps"] == 9000

    another_day = await client.post(
        "/api/activity/daily",
        json={"metric_date": "2026-01-02", "steps": 10000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert another_day.status_code == 200

    filtered = await client.get(
        "/api/activity/daily?from_date=2026-01-02&to_date=2026-01-02",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert filtered.status_code == 200
    payload = filtered.json()
    assert len(payload) == 1
    assert payload[0]["metric_date"] == "2026-01-02"


@pytest.mark.asyncio
async def test_integrations_connected_accounts_and_sync_jobs_are_user_scoped(client: AsyncClient):
    token_a, _ = await _register_and_login(client, "int.a@example.com", "pass12345")
    token_b, _ = await _register_and_login(client, "int.b@example.com", "pass12345")

    connect = await client.post(
        "/api/integrations/connect",
        json={
            "provider": "garmin",
            "external_user_id": "garmin-user-123",
            "access_token": "token-abc",
            "refresh_token": "refresh-abc",
            "scopes": "activity:read",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert connect.status_code == 200
    account_id = connect.json()["id"]

    list_a = await client.get("/api/integrations", headers={"Authorization": f"Bearer {token_a}"})
    list_b = await client.get("/api/integrations", headers={"Authorization": f"Bearer {token_b}"})
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    sync_b = await client.post(
        f"/api/integrations/{account_id}/sync",
        json={"cursor": "cursor-1"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert sync_b.status_code == 404

    sync_a = await client.post(
        f"/api/integrations/{account_id}/sync",
        json={"cursor": "cursor-1"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert sync_a.status_code == 200
    assert sync_a.json()["status"] == "queued"
