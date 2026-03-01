"""
Password hashing and verification using bcrypt.

Use hash_password when storing a new password (e.g. on register).
Use verify_password when checking a login attempt.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password for storage.
    Returns a bcrypt hash that can be stored in the database.
    """
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Check a plain-text password against a stored hash.
    Returns True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain, hashed)
