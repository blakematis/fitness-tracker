"""
Provider integration account and sync scaffolding routes.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import ConnectedAccount, IntegrationSyncJob, User
from app.schemas import ConnectedAccountCreate, ConnectedAccountResponse, SyncJobCreate, SyncJobResponse

router = APIRouter()


@router.post("/connect", response_model=ConnectedAccountResponse)
async def connect_provider_account(
    body: ConnectedAccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConnectedAccount:
    """
    Create or update a provider account for the current user.
    """
    existing_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider == body.provider,
            ConnectedAccount.external_user_id == body.external_user_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    payload = body.model_dump()
    if existing is None:
        account = ConnectedAccount(user_id=user.id, **payload)
        db.add(account)
        await db.flush()
        await db.refresh(account)
        return account

    for key, value in payload.items():
        setattr(existing, key, value)
    await db.flush()
    await db.refresh(existing)
    return existing


@router.get("", response_model=list[ConnectedAccountResponse])
async def list_connected_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConnectedAccount]:
    """List connected accounts for the current user only."""
    result = await db.execute(
        select(ConnectedAccount).where(ConnectedAccount.user_id == user.id).order_by(desc(ConnectedAccount.created_at))
    )
    return list(result.scalars().all())


@router.post("/{account_id}/sync", response_model=SyncJobResponse)
async def queue_sync_job(
    account_id: int,
    body: SyncJobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IntegrationSyncJob:
    """
    Create a sync job record for a connected account owned by the user.
    """
    account_result = await db.execute(
        select(ConnectedAccount).where(ConnectedAccount.id == account_id, ConnectedAccount.user_id == user.id)
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connected account not found")

    account.last_sync_at = datetime.now(UTC)
    job = IntegrationSyncJob(connected_account_id=account.id, status="queued", cursor=body.cursor)
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job
