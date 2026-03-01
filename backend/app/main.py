"""
Application entry point and FastAPI app configuration.

Creates the FastAPI instance, wires API routes, and defines lifespan
behavior (create DB tables on startup, dispose engine on shutdown).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app import models  # noqa: F401 - register all tables with Base.metadata
from app.api.routes import api_router
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: create all database tables on startup,
    dispose the engine on shutdown.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Fitness Tracker API",
    description="Backend API for the fitness tracker app",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health():
    """
    Health check endpoint. Verifies the API and database are reachable.
    Returns 200 with {"status": "ok"} if the database connection succeeds.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}
