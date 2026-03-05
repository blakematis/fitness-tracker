"""
Pydantic schemas for request/response validation and serialization.

Used by FastAPI for JSON bodies and responses; keeps API contracts
separate from ORM models.
"""

from app.schemas.activity import DailyActivityMetricCreate, DailyActivityMetricResponse
from app.schemas.goals import GoalCreate, GoalResponse, GoalUpdate
from app.schemas.integrations import (
    ConnectedAccountCreate,
    ConnectedAccountResponse,
    SyncJobCreate,
    SyncJobResponse,
)
from app.schemas.metrics import (
    AdminObfuscatedMetric,
    AdminRawMetricsRequest,
    BodyAssessmentCreate,
    BodyAssessmentResponse,
    InBodyCsvUploadResponse,
)
from app.schemas.user import Token, UserCreate, UserResponse

__all__ = [
    "UserCreate",
    "UserResponse",
    "Token",
    "BodyAssessmentCreate",
    "BodyAssessmentResponse",
    "InBodyCsvUploadResponse",
    "AdminObfuscatedMetric",
    "AdminRawMetricsRequest",
    "DailyActivityMetricCreate",
    "DailyActivityMetricResponse",
    "GoalCreate",
    "GoalUpdate",
    "GoalResponse",
    "ConnectedAccountCreate",
    "ConnectedAccountResponse",
    "SyncJobCreate",
    "SyncJobResponse",
]
