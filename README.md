# DBVault

DBVault is a FastAPI backend service for centralized database backup management.

This repository implements the backend API described in `design.md`. It covers
database instance management, storage backends, backup and restore orchestration,
RBAC, auditing, task tracking, lifecycle handling, and tests.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

## Docker

```bash
docker compose up --build
```

