"""
Pytest configuration and shared fixtures for the Fitness Tracker API tests.

Test env is set before any app import so the app uses in-memory SQLite and a fixed
SECRET_KEY. No PostgreSQL is required for CI.
"""

import os

# Force test database and secret before app (config/database) is imported.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-chars-for-ci"

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
async def ensure_tables():
    """Create DB tables before any test. Session-scoped so we do this once."""
    from app.database import Base, engine
    from app.models import User  # noqa: F401 - register with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="session")
async def client(ensure_tables):
    """
    Session-scoped async HTTP client. Depends on ensure_tables so DB exists.
    Reused by all tests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def clear_users(client):
    """
    Clear the users table before each test so tests are isolated.
    Depends on client so ensure_tables has already run.
    """
    from sqlalchemy import delete

    from app.database import engine
    from app.models import (
        AdminAccessAudit,
        BodyAssessment,
        ConnectedAccount,
        DailyActivityMetric,
        Goal,
        IntegrationSyncJob,
        User,
    )

    async with engine.begin() as conn:
        await conn.execute(delete(AdminAccessAudit))
        await conn.execute(delete(IntegrationSyncJob))
        await conn.execute(delete(ConnectedAccount))
        await conn.execute(delete(DailyActivityMetric))
        await conn.execute(delete(Goal))
        await conn.execute(delete(BodyAssessment))
        await conn.execute(delete(User))
