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

The Compose stack includes the DBVault API dependencies plus source databases
that can be registered in DBVault for local backup testing:

- MySQL: `127.0.0.1:3306`, database `orders`, user `backup`, password `backup-password`
- PostgreSQL: `127.0.0.1:15432`, database `reports`, user `backup`, password `backup-password`

Default API credentials:

- Username: `admin`
- Password: `admin123456789`

## Quality Gates

```bash
ruff check app tests alembic
pytest
alembic upgrade head
```

