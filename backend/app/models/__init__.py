"""
SQLAlchemy ORM models for the Fitness Tracker API.

Import models here so they are registered with Base.metadata and
can be used in migrations and create_all().
"""

from app.models.admin_access_audit import AdminAccessAudit
from app.models.body_assessment import BodyAssessment
from app.models.connected_account import ConnectedAccount
from app.models.daily_activity_metric import DailyActivityMetric
from app.models.goal import Goal
from app.models.integration_sync_job import IntegrationSyncJob
from app.models.user import User

__all__ = [
    "User",
    "BodyAssessment",
    "AdminAccessAudit",
    "DailyActivityMetric",
    "Goal",
    "ConnectedAccount",
    "IntegrationSyncJob",
]
