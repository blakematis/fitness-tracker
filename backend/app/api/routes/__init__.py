"""
API route aggregation.

Mounts auth and users routers under /api with consistent prefixes and tags
for OpenAPI grouping:
  - /api/auth  -> auth routes (register, login)
  - /api/users -> user routes (me, etc.)
"""

from fastapi import APIRouter

from app.api.routes import auth, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
