"""Tests for /api/users/me (protected by JWT)."""

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str = "me@example.com", password: str = "pass123"):
    """Register a user and return the access token."""
    await client.post("/api/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_me_success(client: AsyncClient):
    """GET /api/users/me with valid Bearer token returns current user."""
    token = await _register_and_login(client)
    response = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    """GET /api/users/me without Authorization header returns 401 or 403."""
    response = await client.get("/api/users/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    """GET /api/users/me with invalid JWT returns 401."""
    response = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_expired_or_wrong_secret(client: AsyncClient):
    """GET /api/users/me with token signed by wrong secret returns 401."""
    token = await _register_and_login(client)
    # Tamper with the token (e.g. flip one character) so signature is invalid
    bad_token = token[:-1] + ("x" if token[-1] != "x" else "y")
    response = await client.get("/api/users/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
