"""Tests for /api/auth/register and /api/auth/login."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """POST /api/auth/register with valid body creates user and returns id and email."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert "id" in data
    assert isinstance(data["id"], int)
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """POST /api/auth/register with existing email returns 400."""
    payload = {"email": "dup@example.com", "password": "password123"}
    await client.post("/api/auth/register", json=payload)
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """POST /api/auth/register with invalid email returns 422."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """POST /api/auth/login with valid credentials returns access_token."""
    await client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "mypassword"},
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """POST /api/auth/login with wrong password returns 401."""
    await client.post(
        "/api/auth/register",
        json={"email": "wrong@example.com", "password": "correct"},
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert "invalid" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    """POST /api/auth/login with unregistered email returns 401."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "any"},
    )
    assert response.status_code == 401
