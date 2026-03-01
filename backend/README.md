# Fitness Tracker API

FastAPI backend with JWT authentication and PostgreSQL. This document describes setup, configuration, and the API.

## Overview

- **Framework:** FastAPI (async)
- **Database:** PostgreSQL via SQLAlchemy 2.0 (async) and asyncpg
- **Auth:** JWT access tokens (Bearer); passwords hashed with bcrypt
- **Config:** All config (including secrets) from `.env`; no secrets hardcoded in code.

## Project structure

```
backend/
├── app/
│   ├── __init__.py       # Package docstring
│   ├── main.py           # FastAPI app, lifespan, /health
│   ├── config.py         # Settings from env
│   ├── database.py       # Async engine, session, get_db
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/          # Pydantic request/response models
│   │   ├── __init__.py
│   │   └── user.py
│   ├── auth/             # Password hashing, JWT, get_current_user
│   │   ├── __init__.py
│   │   ├── password.py
│   │   ├── jwt.py
│   │   └── dependencies.py
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py   # api_router (mounts auth + users)
│           ├── auth.py       # register, login
│           └── users.py     # me
├── .env
├── requirements.txt
└── README.md
```

## Setup

1. **Create a virtual environment and install dependencies**

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Configure environment (required)**

   Create a `.env` file in the `backend/` directory with **all** required values. The app does not start without them; no secrets are hardcoded.

   - `DATABASE_URL` – PostgreSQL connection string (must use `postgresql+asyncpg://...` for async).
   - `SECRET_KEY` – A long random string for signing JWTs (e.g. 32+ characters). Generate a new one for production.

3. **Run PostgreSQL**

   From the project root, with Docker (database only):

   ```bash
   docker compose up -d db
   ```

   Or run **database and API** together (see [project README](../README.md)):

   ```bash
   docker compose up -d
   ```

   Or use a local PostgreSQL instance and create a database named `fitness_tracker`.

4. **Run the API** (when not using Docker for the API)

   ```bash
   uvicorn app.main:app --reload
   ```

   - API base: http://127.0.0.1:8000  
   - Interactive docs: http://127.0.0.1:8000/docs  
   - Health: http://127.0.0.1:8000/health  

Tables are created automatically on startup via the app lifespan.

## Configuration reference

All configuration is read from `backend/.env` (and environment variables). **Required** variables have no default in code.

| Variable | Required | Description | Default in code |
|----------|----------|-------------|-----------------|
| `DATABASE_URL` | Yes | Async PostgreSQL URL (`postgresql+asyncpg://user:pass@host:port/db`) | None |
| `SECRET_KEY` | Yes | JWT signing secret; keep secure and long | None |
| `ALGORITHM` | No | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Access token lifetime in minutes | `30` |

## Auth flow

1. **Register:** `POST /api/auth/register` with body `{ "email": "...", "password": "..." }`. Returns `{ "id", "email" }`.
2. **Login:** `POST /api/auth/login` with the same body. Returns `{ "access_token": "...", "token_type": "bearer" }`.
3. **Protected routes:** Send header `Authorization: Bearer <access_token>` (e.g. for `GET /api/users/me`).

Use the `access_token` in the `Authorization: Bearer ...` header for any route that depends on `get_current_user`.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check; verifies DB connectivity. |
| POST | `/api/auth/register` | No | Create user; body: `UserCreate`. |
| POST | `/api/auth/login` | No | Return JWT; body: `UserCreate`. |
| GET | `/api/users/me` | Bearer | Current user profile. |

Full request/response schemas are available in the OpenAPI docs at `/docs`.

## Running with Docker

The API can run in Docker together with PostgreSQL. From the **project root**:

1. Create a root `.env` with `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`, and `SECRET_KEY`.
2. Run `docker compose up -d`. The `api` service gets `DATABASE_URL` and `SECRET_KEY` from the root `.env`; no secrets are in `docker-compose.yml`.

See the [project README](../README.md) for more on Docker usage.

## Testing

Unit and API tests use **pytest** with an in-memory SQLite database (no PostgreSQL required).

**Run tests locally:**

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

Set `DATABASE_URL` and `SECRET_KEY` in the environment, or rely on `tests/conftest.py` (which sets them before importing the app). Optional: `pytest --cov=app --cov-report=term-missing` for coverage.

**CI:** The [Tests](../.github/workflows/test.yml) workflow runs on push and pull requests to `main`/`master`. It installs dependencies, sets the test env, and runs pytest. No database service is required (SQLite in-memory).
