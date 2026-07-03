<p align="center">
  <a href="README_CN.md">中文</a> | <b>English</b>
</p>

<h1 align="center">DBVault</h1>

<p align="center">
  <b>A centralized, agentless database backup and recovery platform.</b>
</p>

<p align="center">
  <a href="https://github.com/mill413/dbvault/actions/workflows/build-and-release.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/mill413/dbvault/build-and-release.yml?style=flat-square&label=CI" alt="CI">
  </a>
  <a href="https://github.com/mill413/dbvault/releases">
    <img src="https://img.shields.io/github/v/release/mill413/dbvault?style=flat-square&label=Release" alt="Release">
  </a>
  <a href="https://github.com/mill413/dbvault/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/mill413/dbvault?style=flat-square" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.x-brightgreen?style=flat-square&logo=vuedotjs" alt="Vue">
</p>

---

DBVault provides a unified management interface for scheduling, executing, and monitoring database backups across your infrastructure. It supports MySQL, PostgreSQL, and MariaDB with flexible storage backends including local filesystem and S3-compatible object storage. Built with **FastAPI** and **Vue 3**, it offers a modern web UI, complete REST API, and Kubernetes integration.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Screenshots](#screenshots)
- [Quick Start](#quick-start)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Pre-built Images](#pre-built-images)
  - [Local Development](#local-development)
- [Upgrade Guide](#upgrade-guide)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development](#development)
- [CI/CD](#cicd)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Capabilities

- **Agentless Backups** — Remote logical backups via `mysqldump`/`pg_dump` without installing agents on target hosts
- **Multi-Database Support** — MySQL, PostgreSQL, and MariaDB with an extensible driver architecture for future additions
- **Kubernetes Integration** — Backup and restore database Pods via kubeconfig with namespace/Pod/label selection
- **Flexible Storage** — Local filesystem, MinIO, and S3-compatible object storage with pluggable storage drivers
- **Scheduled Jobs** — Cron and interval-based scheduling powered by APScheduler
- **Backup Verification** — SHA256/MD5 checksums with pre-restore integrity validation
- **Compression** — zstd (default, high ratio) and gzip support
- **One-Click Restore** — Restore to original or new database instances with progress tracking and event logging

### Security & Access Control

- **Role-Based Access Control (RBAC)** — Admin and User roles with granular permission enforcement
- **JWT Authentication** — Access/refresh token flow with configurable expiration
- **Credential Encryption** — Database credentials encrypted at rest using Fernet symmetric encryption
- **Full Audit Logging** — Every operation logged with user, action, resource, and timestamp

### Operations & Monitoring

- **Dashboard** — Real-time backup trends, storage capacity usage, and alert overview with ECharts visualization
- **Storage Capacity Monitoring** — Per-storage capacity limits with automatic alerting on threshold breach
- **Alert System** — Backup failure, restore failure, storage anomaly, and capacity warnings
- **Audit Trail** — Complete operation history for compliance and troubleshooting

### Developer Experience

- **RESTful API** — Comprehensive CRUD endpoints with auto-generated OpenAPI/Swagger documentation
- **i18n** — Full Chinese and English interface support
- **CI/CD** — Automated Docker image builds and releases via GitHub Actions
- **Self-Registration** — Optional user self-registration with configurable toggle

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Vue 3 Frontend                           │
│            Element Plus · ECharts · Pinia · Axios                │
└─────────────────────────────┬────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────┴────────────────────────────────────┐
│                        FastAPI Backend                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │
│  │  Auth &   │  │  Backup  │  │  Restore  │  │  Scheduler    │  │
│  │  RBAC     │  │  Service │  │  Service  │  │  (APScheduler)│  │
│  └──────────┘  └──────────┘  └───────────┘  └───────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Driver Registry                        │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  DB Drivers  │  │Storage Drivers│  │Compression Drv │  │   │
│  │  │ MySQL/PgSQL  │  │ Local/S3     │  │ zstd/gzip      │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐   ┌────────┴────────┐   ┌────────┴────────┐
│  PostgreSQL   │   │  Target DBs     │   │  Storage Backends│
│  (Metadata)   │   │  MySQL/PgSQL    │   │  Local FS / S3   │
│               │   │  MariaDB/K8s    │   │  MinIO           │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

> For the complete design document, see [design.md](design.md).

## Tech Stack

| Layer | Technology |
| --- | --- |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, structlog |
| **Frontend** | Vue 3, Element Plus, ECharts, Pinia, Axios, vue-i18n |
| **Metadata DB** | PostgreSQL 16 (production), SQLite (development) |
| **Storage** | Local filesystem, MinIO, S3-compatible (boto3) |
| **Scheduling** | APScheduler (Cron / Interval / One-time) |
| **Auth** | JWT (python-jose), bcrypt, passlib, Fernet encryption |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Testing** | pytest, pytest-cov, ruff |

## Screenshots

| Dashboard | Database Management |
| --- | --- |
| ![Dashboard](docs/screenshots/dashboard.png) | ![Databases](docs/screenshots/databases.png) |

| Backup Management | Job Scheduling |
| --- | --- |
| ![Backups](docs/screenshots/backups.png) | ![Jobs](docs/screenshots/jobs.png) |

## Quick Start

### Docker Compose (Recommended)

The fastest way to get started. This builds both API and frontend images, starts the full stack with PostgreSQL and Redis.

```bash
cd docker
./deploy.sh -b
```

Once running:

- **Frontend:** `http://localhost:5173`
- **API:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs`

**Default credentials:** `admin` / `admin123456789`

> **Note:** Change `DBVAULT_JWT_SECRET` in production. The default value is for development only.

#### Deploy Script Usage

```bash
./deploy.sh [options]

Options:
  -p <project>             Project name (default: dbvault)
  -b, --build              Build images before deploying
  -n, --no-build           Use existing images (default)
  -a, --api-only           Build/deploy API service only
  -f, --frontend-only      Build/deploy frontend service only
  -d, --down               Stop and remove all containers
  -D, --down-v             Stop and remove containers and volumes
  -e, --export             Export images to a tar archive
  -o, --output <dir>       Export directory (default: current directory)
  -h, --help               Show help message
```

**Examples:**

```bash
./deploy.sh -b                    # Build all images and deploy
./deploy.sh -b -a                 # Rebuild and deploy API only
./deploy.sh -b -f                 # Rebuild and deploy frontend only
./deploy.sh -p myproject -b       # Deploy with custom project name
./deploy.sh -e -o /tmp            # Export built images to /tmp
./deploy.sh -d                    # Stop all services
./deploy.sh -D                    # Stop and remove all data
```

### Pre-built Images

Pre-built Docker images are published to [GitHub Releases](https://github.com/mill413/dbvault/releases) on every push to `main`.

```bash
# Download the latest release
gh release download --repo mill413/dbvault -p '*.tar.gz'

# Load images
docker load -i dbvault-images-*.tar.gz

# Start the stack
docker compose -f docker/docker-compose.yml up -d
```

### Local Development

For development without Docker. Requires Python 3.11+ and Node.js 18+.

**Prerequisites:**

- PostgreSQL 16+ (or use SQLite with default config)
- Redis 7+
- Node.js 18+ and npm

**Backend:**

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start the API server with hot reload
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend

# Install dependencies
npm install

# Start dev server with API proxy
npm run dev
```

**Database migrations:**

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Rollback last migration
alembic downgrade -1
```

## Upgrade Guide

For running services, follow the documented upgrade flow before replacing containers: back up the metadata database and local DBVault data volume, keep the Git checkout and Docker images on the same version, run `alembic upgrade head`, then restart the API and frontend.

See [docs/UPGRADE.md](docs/UPGRADE.md) for source-based upgrades, release-image upgrades, validation, and rollback steps.

## Configuration

All configuration is managed via environment variables (prefix `DBVAULT_`). See [`.env.example`](.env.example) for a complete reference file.

### Application

| Variable | Default | Description |
| --- | --- | --- |
| `DBVAULT_ENV` | `dev` | Runtime environment (`dev` / `prod`) |
| `DBVAULT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `DBVAULT_OPENAPI_ENABLED` | `true` | Enable/disable Swagger UI at `/docs` |

### Database

| Variable | Default | Description |
| --- | --- | --- |
| `DBVAULT_DATABASE_URL` | `sqlite:///./dbvault.db` | Metadata database connection string |

> Use `postgresql+psycopg://user:pass@host:port/db` for production.

### Authentication & Security

| Variable | Default | Description |
| --- | --- | --- |
| `DBVAULT_JWT_SECRET` | `change-me-in-production` | **Required in production.** Secret key for JWT signing |
| `DBVAULT_ENCRYPTION_KEY` | *(auto-generated)* | Fernet key for encrypting stored credentials |
| `DBVAULT_ENABLE_REGISTRATION` | `false` | Allow user self-registration |
| `DBVAULT_INITIAL_ADMIN_USERNAME` | `admin` | Default admin username on first startup |
| `DBVAULT_INITIAL_ADMIN_PASSWORD` | `admin123456789` | Default admin password (min 12 chars) |

### Storage

| Variable | Default | Description |
| --- | --- | --- |
| `DBVAULT_BACKUP_TMP_DIR` | `./dbvault_tmp` | Temporary directory for backup processing |
| `DBVAULT_LOCAL_STORAGE_ROOT` | `./dbvault_backups` | Root directory for local storage backend |
| `DBVAULT_KUBECONFIG_DIR` | `/var/lib/dbvault/kubeconfigs` | Directory for uploaded kubeconfig files |

### Advanced

| Variable | Default | Description |
| --- | --- | --- |
| `DBVAULT_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `DBVAULT_SCHEDULER_ENABLED` | `true` | Enable/disable the background job scheduler |
| `DBVAULT_RUN_BACKGROUND_TASKS_INLINE` | `false` | Run background tasks synchronously (dev/test only) |
| `DBVAULT_INITIAL_ADMIN_USERNAME` | `admin` | Initial admin username created on first startup |
| `DBVAULT_INITIAL_ADMIN_PASSWORD` | `admin123456789` | Initial admin password created on first startup |

## API Documentation

The API is organized into the following modules:

| Module | Prefix | Description |
| --- | --- | --- |
| **Auth** | `/api/v1/auth` | Login, refresh, user profile |
| **Users** | `/api/v1/users` | User CRUD and role management |
| **Databases** | `/api/v1/databases` | Database instance registration and testing |
| **Storages** | `/api/v1/storages` | Storage backend management |
| **Backups** | `/api/v1/backups` | Backup execution, download, and metadata |
| **Restores** | `/api/v1/restore`, `/api/v1/restore-tasks` | Restore execution and progress tracking |
| **Jobs** | `/api/v1/jobs` | Scheduled job configuration and control |
| **Alerts** | `/api/v1/alerts` | Alert querying and acknowledgment |
| **Audit** | `/api/v1/audit-logs` | Operation audit log |
| **Kubeconfigs** | `/api/v1/kubeconfigs` | Kubernetes cluster configuration |
| **Dashboard** | `/api/v1/dashboard` | Summary statistics and trends |

Interactive API documentation is available at `http://localhost:8000/docs` when `DBVAULT_OPENAPI_ENABLED=true`.

## Project Structure

```text
dbvault/
├── app/                        # Backend application
│   ├── api/v1/                 # REST API endpoint handlers
│   │   ├── auth.py             #   Authentication (login/refresh)
│   │   ├── backups.py          #   Backup operations
│   │   ├── databases.py        #   Database instance management
│   │   ├── jobs.py             #   Scheduled job management
│   │   ├── restores.py         #   Restore operations
│   │   ├── storages.py         #   Storage backend management
│   │   └── router.py           #   API route registry
│   ├── core/                   # Framework layer
│   │   ├── config.py           #   Settings (pydantic-settings)
│   │   ├── database.py         #   SQLAlchemy engine & session
│   │   ├── encryption.py       #   Fernet credential encryption
│   │   ├── errors.py           #   Custom exception handler
│   │   ├── logging.py          #   Structured logging (structlog)
│   │   └── security.py         #   JWT & password utilities
│   ├── drivers/                # Pluggable driver system
│   │   ├── database/           #   MySQL, PostgreSQL, K8s drivers
│   │   ├── storage/            #   Local FS, S3 drivers
│   │   ├── compression/        #   zstd, gzip drivers
│   │   ├── bootstrap.py        #   Driver auto-registration
│   │   └── registry.py         #   Driver registry
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer
│   ├── scheduler/              # APScheduler integration
│   └── main.py                 # FastAPI application entry
├── alembic/                    # Database migration scripts
├── frontend/                   # Vue 3 frontend application
│   ├── src/
│   │   ├── api/                #   API client modules
│   │   ├── assets/             #   Global styles
│   │   ├── locales/            #   i18n translations (en/zh)
│   │   ├── router/             #   Vue Router configuration
│   │   ├── stores/             #   Pinia state management
│   │   ├── utils/              #   Shared utilities
│   │   ├── views/              #   Page components
│   │   ├── App.vue             #   Root component
│   │   └── main.js             #   Application entry
│   └── vite.config.js          #   Vite build config
├── docker/                     # Container configuration
│   ├── Dockerfile              #   API service (multi-stage, kubectl)
│   ├── Dockerfile.frontend     #   Frontend service
│   ├── docker-compose.yml      #   Development stack
│   └── deploy.sh               #   Deployment automation
├── tests/                      # Backend test suite
├── .github/workflows/          # GitHub Actions CI/CD
├── design.md                   # Detailed design document
├── pyproject.toml              # Python project configuration
└── .env.example                # Environment variable reference
```

## Development

### Testing

```bash
# Run all tests with coverage report
pytest

# Run specific test file
pytest tests/test_auth_rbac.py

# Run with verbose output
pytest -v

# Run Docker-backed integration tests for real MySQL, PostgreSQL, and MinIO services
scripts/run_integration_tests.sh
```

### Code Quality

```bash
# Lint all Python code
ruff check app tests alembic

# Auto-fix linting issues
ruff check --fix app tests alembic
```

### Adding a New Driver

The driver system supports pluggable extensions. To add a new database, storage, or compression driver:

1. Create a new module under `app/drivers/<type>/`
2. Implement the corresponding base class (`BaseDatabaseDriver`, `BaseStorageDriver`, or `BaseCompressionDriver`)
3. Register it in `app/drivers/bootstrap.py`

See existing drivers for reference implementations.

## CI/CD

Every push to `main` triggers a [GitHub Actions](.github/workflows/build-and-release.yml) workflow that:

1. Runs Ruff, pytest, and the frontend production build
2. Builds API and Frontend Docker images
3. Tags them with the commit SHA and timestamp
4. Exports to a `.tar.gz` archive
5. Creates a GitHub Release with the archive attached

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Keep commits focused and use conventional commit messages, for example `fix(restore): require target database`
4. Run `ruff check app tests alembic`, `pytest`, and `cd frontend && npm run build`
5. Include screenshots for frontend-visible changes
6. Push to the branch and open a Pull Request with a summary and validation results

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
