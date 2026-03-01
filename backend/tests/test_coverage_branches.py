"""Branch-focused tests to keep backend coverage above threshold."""

from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.api.routes import activity, auth, goals, integrations, metrics
from app.auth import dependencies
from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.database import Base, async_session_factory, engine
from app.main import health, lifespan
from app.models import BodyAssessment, ConnectedAccount, DailyActivityMetric, Goal, User
from app.schemas import (
    AdminRawMetricsRequest,
    BodyAssessmentCreate,
    ConnectedAccountCreate,
    DailyActivityMetricCreate,
    GoalCreate,
    GoalUpdate,
    SyncJobCreate,
    UserCreate,
)


async def _create_user(email: str, role: str = "user", password: str = "pass12345") -> User:
    async with async_session_factory() as session:
        user = User(email=email, hashed_password=hash_password(password), role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_auth_route_functions_directly_cover_success_and_error_paths():
    async with async_session_factory() as session:
        created = await auth.register(UserCreate(email="direct-auth@example.com", password="pass12345"), db=session)
        assert created.email == "direct-auth@example.com"

        with pytest.raises(HTTPException) as dup:
            await auth.register(UserCreate(email="direct-auth@example.com", password="pass12345"), db=session)
        assert dup.value.status_code == 400

        token = await auth.login(UserCreate(email="direct-auth@example.com", password="pass12345"), db=session)
        assert token.access_token

        with pytest.raises(HTTPException) as bad:
            await auth.login(UserCreate(email="direct-auth@example.com", password="wrong"), db=session)
        assert bad.value.status_code == 401


@pytest.mark.asyncio
async def test_activity_route_update_and_list_paths():
    user = await _create_user("activity-direct@example.com")
    async with async_session_factory() as session:
        created = await activity.upsert_daily_metric(
            DailyActivityMetricCreate(metric_date=date(2026, 2, 1), steps=7000),
            user=user,
            db=session,
        )
        assert created.steps == 7000

        updated = await activity.upsert_daily_metric(
            DailyActivityMetricCreate(metric_date=date(2026, 2, 1), steps=9000, distance_miles=3.4),
            user=user,
            db=session,
        )
        assert updated.steps == 9000

        listed = await activity.list_daily_metrics(
            from_date=date(2026, 2, 1),
            to_date=date(2026, 2, 1),
            user=user,
            db=session,
        )
        assert len(listed) == 1
        assert int(listed[0].steps or 0) == 9000


@pytest.mark.asyncio
async def test_goals_route_not_found_paths_and_delete():
    owner = await _create_user("goal-owner@example.com")
    other = await _create_user("goal-other@example.com")
    async with async_session_factory() as session:
        created = await goals.create_goal(
            GoalCreate(
                goal_type="weekly_distance_miles",
                period_type="weekly",
                target_value=20,
                start_date=date(2026, 2, 1),
            ),
            user=owner,
            db=session,
        )
        assert created.id > 0

        with pytest.raises(HTTPException) as upd_nf:
            await goals.update_goal(created.id, GoalUpdate(target_value=30), user=other, db=session)
        assert upd_nf.value.status_code == 404

        with pytest.raises(HTTPException) as del_nf:
            await goals.delete_goal(created.id, user=other, db=session)
        assert del_nf.value.status_code == 404

        await goals.delete_goal(created.id, user=owner, db=session)
        await session.flush()
        result = await session.execute(select(Goal))
        assert len(list(result.scalars().all())) == 0


@pytest.mark.asyncio
async def test_integrations_update_list_and_missing_account_sync():
    user = await _create_user("integrations-direct@example.com")
    async with async_session_factory() as session:
        first = await integrations.connect_provider_account(
            body=ConnectedAccountCreate(
                provider="garmin",
                external_user_id="abc123",
                access_token="a",
                refresh_token="r",
            ),
            user=user,
            db=session,
        )
        assert first.id > 0

        second = await integrations.connect_provider_account(
            body=ConnectedAccountCreate(
                provider="garmin",
                external_user_id="abc123",
                access_token="new-access",
                refresh_token="new-refresh",
            ),
            user=user,
            db=session,
        )
        assert second.id == first.id

        listed = await integrations.list_connected_accounts(user=user, db=session)
        assert len(listed) == 1

        with pytest.raises(HTTPException) as sync_nf:
            await integrations.queue_sync_job(9999, SyncJobCreate(cursor="c1"), user=user, db=session)
        assert sync_nf.value.status_code == 404


@pytest.mark.asyncio
async def test_metrics_route_helpers_and_not_found_path():
    owner = await _create_user("metrics-owner@example.com")
    other = await _create_user("metrics-other@example.com")
    admin = await _create_user("metrics-admin@example.com", role="super_admin")
    async with async_session_factory() as session:
        created = await metrics.create_my_metric(
            BodyAssessmentCreate(
                measured_at=datetime.now(UTC),
                weight_lb=180,
                body_fat_pct=20,
                source="manual",
            ),
            user=owner,
            db=session,
        )
        assert created.id > 0

        mine = await metrics.list_my_metrics(user=owner, db=session)
        assert len(mine) == 1

        with pytest.raises(HTTPException) as not_found:
            await metrics.get_my_metric(created.id, user=other, db=session)
        assert not_found.value.status_code == 404

        assert metrics._mask_email("no-at-symbol") == "***"
        assert metrics._mask_email("aa@domain") == "***@***"

        obfuscated = await metrics.list_obfuscated_metrics(
            body=AdminRawMetricsRequest(reason="Investigating privacy-safe aggregate behavior"),
            admin=admin,
            db=session,
        )
        assert len(obfuscated) == 1
        assert obfuscated[0].masked_email.startswith("me***@")

        raw = await metrics.list_user_metrics_raw(
            target_user_id=owner.id,
            body=AdminRawMetricsRequest(reason="User requested data export support"),
            admin=admin,
            db=session,
        )
        assert len(raw) == 1


@pytest.mark.asyncio
async def test_auth_dependency_error_branches_and_super_admin_gate():
    user = await _create_user("dep-user@example.com")
    async with async_session_factory() as session:
        # Invalid token branch
        with pytest.raises(HTTPException) as invalid:
            await dependencies.get_current_user(
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt"),
                db=session,
            )
        assert invalid.value.status_code == 401

        # Missing subject branch
        token_no_sub = create_access_token(sub=user.id, extra_claims={"sub": ""})
        with pytest.raises(HTTPException) as no_sub:
            await dependencies.get_current_user(
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_no_sub),
                db=session,
            )
        assert no_sub.value.status_code == 401

        # Non-int subject branch
        token_bad_sub = create_access_token(sub="abc")
        with pytest.raises(HTTPException) as bad_sub:
            await dependencies.get_current_user(
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_bad_sub),
                db=session,
            )
        assert bad_sub.value.status_code == 401

        # User not found branch
        token_unknown = create_access_token(sub=999999)
        with pytest.raises(HTTPException) as unknown:
            await dependencies.get_current_user(
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_unknown),
                db=session,
            )
        assert unknown.value.status_code == 401

        # super-admin gate
        with pytest.raises(HTTPException) as forbidden:
            await dependencies.get_current_super_admin(user=user)
        assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_jwt_extra_claims_and_main_lifespan():
    token = create_access_token(sub=123, extra_claims={"role": "super_admin"})
    assert token

    # Execute lifespan startup/shutdown lines for coverage.
    async with lifespan(None):
        async with engine.connect() as conn:
            result = await conn.execute(select(BodyAssessment).limit(1))
            assert result is not None
            await health()

    # Restore tables for any tests running after this one.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
