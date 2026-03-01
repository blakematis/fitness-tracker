"""
Schemas for provider account connection and sync scaffolding.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ConnectedAccountCreate(BaseModel):
    """Create/connect a third-party provider account."""

    provider: str = Field(min_length=2, max_length=64)
    external_user_id: str = Field(min_length=1, max_length=255)
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: str | None = None


class ConnectedAccountResponse(BaseModel):
    """Connected account returned by API routes (safe fields only)."""

    id: int
    user_id: int
    provider: str
    external_user_id: str
    status: str
    token_expires_at: datetime | None
    scopes: str | None
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime | None

    model_config = {"from_attributes": True}


class SyncJobCreate(BaseModel):
    """Request body to create a sync job."""

    cursor: str | None = None


class SyncJobResponse(BaseModel):
    """Integration sync job metadata."""

    id: int
    connected_account_id: int
    status: str
    cursor: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}
