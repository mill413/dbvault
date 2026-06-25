# Repository Guidelines

## Project Structure & Module Organization

DBVault is a FastAPI backend with a Vue 3/Vite frontend. Backend source lives in `app/`: routes in `app/api/v1/`, business logic in `app/services/`, models in `app/models/`, schemas in `app/schemas/`, and backup/storage/compression drivers in `app/drivers/`. Database migrations are in `alembic/versions/`. Frontend code is in `frontend/src/`, with views, API clients, stores, utilities, locales, and styles split by directory. Backend tests live in `tests/`; screenshots and documentation live under `docs/`, `README.md`, `README_CN.md`, and `design.md`.

## Build, Test, and Development Commands

- `pip install -e ".[dev]"`: install the backend and development tools.
- `alembic upgrade head`: apply database migrations.
- `uvicorn app.main:app --reload --port 8000`: run the API locally.
- `cd frontend && npm install`: install frontend dependencies.
- `cd frontend && npm run dev`: start the Vite dev server with API proxy support.
- `cd frontend && npm run build`: build the production frontend.
- `docker compose -f docker/docker-compose.yml up -d`: start the containerized stack.

## Coding Style & Naming Conventions

Python targets 3.11 and uses Ruff with a 120-character line length plus `E`, `F`, `I`, `B`, and `UP` rules. Run `ruff check app tests alembic` before submitting backend changes; use `ruff check --fix app tests alembic` for mechanical fixes. Keep backend modules snake_case. Vue pages use PascalCase, such as `Dashboard.vue`; JavaScript modules use concise domain names, such as `frontend/src/api/backups.js`.

## Testing Guidelines

Pytest is configured in `pyproject.toml` with coverage for `app` and discovery from `tests/`. Run `pytest` for the full suite, `pytest tests/test_auth_rbac.py` for a focused file, or `.venv/bin/python -m pytest` when relying on the checked-in virtual environment. Name new tests `test_<behavior>.py` and cover permissions, ownership isolation, migrations, and driver behavior when those surfaces change.

## Commit & Pull Request Guidelines

Git history follows conventional commits: examples include `feat(auth): collapse roles to admin and user`, `fix(dashboard): omit empty backup datasets`, and `docs: update role and ownership model`. Split unrelated work into separate commits and run `git diff --cached --check` before committing. Pull requests should state the change, list validation commands, link issues when applicable, and include screenshots for frontend-visible UI changes.

## Security & Configuration Tips

Use `.env.example` as the configuration reference and never commit real secrets. Change `DBVAULT_JWT_SECRET` outside development. The role model is intentionally limited to `Admin` and `User`; update backend permissions, frontend role controls, docs, migrations, and regression tests together if authorization behavior changes.
