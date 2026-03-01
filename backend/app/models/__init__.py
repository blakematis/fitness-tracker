"""
SQLAlchemy ORM models for the Fitness Tracker API.

Import models here so they are registered with Base.metadata and
can be used in migrations and create_all().
"""

from app.models.user import User

__all__ = ["User"]
