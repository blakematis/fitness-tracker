"""
Database connection and session management for async SQLAlchemy.

Provides the async engine, session factory, declarative Base, and a
get_db dependency that yields a session per request with commit/rollback.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Async engine for PostgreSQL via asyncpg.
engine = create_async_engine(
    settings.database_url,
    echo=False,
)

# Factory for request-scoped async sessions.
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy models.
    Subclass this when defining new tables.
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields a database session per request.
    Commits on success, rolls back on exception, and always closes the session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
