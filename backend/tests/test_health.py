"""Tests for the /health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    """GET /health returns 200 and {\"status\": \"ok\"} when DB is reachable."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
