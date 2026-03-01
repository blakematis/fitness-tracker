"""
User model for authentication and ownership of fitness data.

Stores email (unique) and bcrypt-hashed password. Used by auth routes
and as the subject of JWT tokens.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """
    User account for login and association with workouts/data.

    Attributes:
        id: Primary key, auto-increment.
        email: Unique email address, indexed for login lookups.
        hashed_password: Bcrypt hash; never store plain passwords.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
