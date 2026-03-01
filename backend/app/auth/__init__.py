"""
Authentication utilities: password hashing and JWT-based current user.

- hash_password / verify_password: bcrypt for storing and checking passwords.
- get_current_user: FastAPI dependency that validates Bearer token and
  returns the associated User (or 401).
"""

from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_current_super_admin
from app.auth.password import hash_password, verify_password

__all__ = ["get_current_user", "get_current_super_admin", "hash_password", "verify_password"]
