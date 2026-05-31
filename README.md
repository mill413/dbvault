# DBVault

**[中文](README_CN.md)** | English

**A centralized, agentless database backup and recovery platform.**

DBVault provides a unified management interface for scheduling, executing, and monitoring database backups across your infrastructure. Built with FastAPI and Vue 3, it supports MySQL, PostgreSQL, and MariaDB with local filesystem and S3-compatible storage backends.

---

## Features

- **Agentless Backups** — Remote logical backups without installing agents on target hosts
- **Multi-Database Support** — MySQL, PostgreSQL, MariaDB (extensible architecture)
- **Flexible Storage** — Local filesystem, MinIO, and S3-compatible object storage
- **Scheduled Jobs** — Cron and interval-based scheduling with APScheduler
- **Backup Verification** — SHA256/MD5 checksums with pre-restore integrity checks
- **Compression** — zstd (default) and gzip support
- **Role-Based Access Control** — Admin, Operator, and Viewer roles with full audit logging
- **Storage Capacity Monitoring** — Per-storage capacity limits with usage alerts
- **Self-Registration** — Optional user self-registration with configurable toggle
- **Dashboard** — Real-time backup trends, storage usage, and alert overview
- **RESTful API** — Complete CRUD with auto-generated OpenAPI documentation
- **i18n** — Full Chinese and English interface support

## Tech Stack

| Layer | Technology |
| ----- | ---------- |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic |
| Frontend | Vue 3, Element Plus, ECharts, Pinia, Axios |
| Database | PostgreSQL (metadata), target DBs (backup sources) |
| Storage | Local FS, MinIO/S3 (via boto3) |
| Scheduling | APScheduler |
| Auth | JWT (python-jose), bcrypt, passlib |
| Containerization | Docker, Docker Compose |

## Quick Start

### Docker Compose (Recommended)

```bash
cd docker
./deploy.sh -b
```

This builds both API and frontend images, then starts the full stack including sample MySQL and PostgreSQL instances for testing.

**Default credentials:** `admin` / `admin123456789`

### Deploy Script Usage

```bash
./deploy.sh [options]

Options:
  -p <project>             Project name (default: dbvault)
  -b, --build              Build images before deploying
  -n, --no-build           Use existing images (default)
  -a, --api-only           Build/deploy API service only
  -f, --frontend-only      Build/deploy frontend service only
  -d, --down               Stop and remove all containers
  -D, --down-v             Stop and remove all containers and volumes
  -h, --help               Show help message
```

**Examples:**

```bash
./deploy.sh -b                    # Build all images and deploy
./deploy.sh -b -a                 # Rebuild and deploy API only
./deploy.sh -b -f                 # Rebuild and deploy frontend only
./deploy.sh -p myproject -b       # Deploy with custom project name
./deploy.sh -d                    # Stop all services
./deploy.sh -D                    # Stop all services and remove volumes
```

### Local Development

**Backend:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**Database migrations:**

```bash
alembic upgrade head          # Apply all migrations
alembic revision --autogenerate -m "description"   # Create new migration
```

## Configuration

All configuration is managed via environment variables (prefix `DBVAULT_`):

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DBVAULT_DATABASE_URL` | `postgresql+psycopg://dbvault:dbvault@db:5432/dbvault` | Metadata database connection string |
| `DBVAULT_JWT_SECRET` | *(required)* | Secret key for JWT token signing |
| `DBVAULT_ENABLE_REGISTRATION` | `false` | Enable/disable user self-registration |
| `DBVAULT_OPENAPI_ENABLED` | `true` | Enable/disable OpenAPI documentation endpoint |
| `DBVAULT_BACKUP_TMP_DIR` | `/tmp/dbvault-backups` | Temporary directory for backup processing |
| `DBVAULT_LOCAL_STORAGE_ROOT` | `/var/lib/dbvault/backups` | Root directory for local storage backend |
| `DBVAULT_RUN_BACKGROUND_TASKS_INLINE` | `false` | Run background tasks synchronously (dev only) |

See [`.env.example`](.env.example) for the complete reference.

## Project Structure

```text
dbvault/
├── app/                    # Backend application
│   ├── api/v1/            # REST API endpoints
│   ├── core/              # Configuration, security, logging
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic request/response schemas
│   └── services/          # Business logic layer
├── alembic/               # Database migrations
├── frontend/              # Vue 3 frontend application
│   ├── src/
│   │   ├── api/           # API client modules
│   │   ├── views/         # Page components
│   │   ├── stores/        # Pinia state management
│   │   ├── locales/       # i18n translations
│   │   └── utils/         # Shared utilities
│   └── vite.config.js
├── docker/                # Docker configuration and deploy scripts
│   ├── Dockerfile         # API service image
│   ├── Dockerfile.frontend # Frontend service image
│   ├── docker-compose.yml
│   └── deploy.sh          # Deployment automation script
├── tests/                 # Backend test suite
├── design.md              # Detailed design document
└── pyproject.toml         # Python project configuration
```

## Testing

```bash
# Run all tests with coverage
pytest

# Lint and type check
ruff check app tests alembic
```

## Sample Databases (Docker Compose)

The development stack includes pre-configured sample databases:

| Database   | Host      | Port  | Database  | User     | Password          |
| ---------- | --------- | ----- | --------- | -------- | ----------------- |
| MySQL      | localhost | 3306  | `orders`  | `backup` | `backup-password` |
| PostgreSQL | localhost | 15432 | `reports` | `backup` | `backup-password` |

## Architecture

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Vue 3 Web  │────▶│  FastAPI API  │────▶│   PostgreSQL    │
│   Frontend  │     │   (Uvicorn)   │     │   (Metadata)    │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────┴───────┐
                    │   Services   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  MySQL   │ │PostgreSQL│ │  MinIO   │
        │  Target  │ │  Target  │ │   S3     │
        └──────────┘ └──────────┘ └──────────┘
```

## License

This project is for internal use.
