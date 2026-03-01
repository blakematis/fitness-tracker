"""
Application configuration loaded from environment variables.

Uses pydantic-settings to read from the backend/.env file and the process
environment. Secrets (e.g. SECRET_KEY, DATABASE_URL) must be set in .env;
no secret values are hardcoded.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# When running locally, load from backend/.env. In Docker, .env may be absent; use env vars only.
_env_path = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """
    Central configuration for the Fitness Tracker API.
    All values are read from .env (if present) or environment variables; no secrets are defaulted.
    """

    model_config = SettingsConfigDict(
        env_file=_env_path if _env_path.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL connection string. Must use the async driver: postgresql+asyncpg://...
    # Set in .env; no default to avoid hardcoding credentials.
    database_url: str

    # Secret key used to sign JWTs. Set in .env; must be long and random.
    secret_key: str

    # JWT signing algorithm (HS256 is symmetric).
    algorithm: str = "HS256"

    # How long access tokens remain valid, in minutes.
    access_token_expire_minutes: int = 30


# Singleton used across the app. Fails at import if .env is missing required vars.
settings = Settings()
