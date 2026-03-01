# Fitness Tracker

Backend API (FastAPI + PostgreSQL) for the fitness tracker app. React frontend can be added under `frontend/`.

## Quick start with Docker (recommended)

All secrets are read from a **root `.env` file**; nothing is hardcoded in `docker-compose.yml`.

1. Create a `.env` file in the project root with:
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (for the database)
   - `SECRET_KEY` (for the API; use a long random string)

2. Start the database and API:
   ```bash
   docker compose up -d
   ```
   - API: http://localhost:8000  
   - Docs: http://localhost:8000/docs  
   - Postgres: localhost:5432 (for local tools; use `db` as host from other containers)

## Running without Docker

See [backend/README.md](backend/README.md) for local setup (venv, `backend/.env`, PostgreSQL).

## Why run the backend in Docker?

- **Same environment everywhere:** Matches production and avoids “works on my machine.”
- **One command:** `docker compose up` gives you Postgres + API with no local Python or DB install.
- **Secrets in one place:** Root `.env` feeds both the database and the API; no secrets in `docker-compose.yml`.

You can still run the API locally (e.g. `uvicorn` in `backend/`) and only run Postgres in Docker if you prefer.
