# Upgrade Guide

This guide covers Docker Compose deployments created by `docker/deploy.sh` or `docker/docker-compose.yml`.

> The default Compose file is development-oriented: API and frontend containers mount the repository source tree, and the API runs with `--reload`. Keep the checked-out code, Docker images, and Alembic migrations on the same version during upgrades.

## Before You Upgrade

1. Use a maintenance window when changing backend code or database schema.
2. Confirm the Compose project name used by the running service. The default is `dbvault`; custom deployments may use `./deploy.sh -p <project>`.
3. Never use `./deploy.sh -D` during an upgrade. It runs `docker compose down -v` and deletes PostgreSQL and DBVault data volumes.
4. Preserve production secrets in `.env` or your deployment environment, especially `DBVAULT_JWT_SECRET` and `DBVAULT_ENCRYPTION_KEY`.

If the service was deployed with a custom project name, export it before every direct `docker compose` command:

```bash
export COMPOSE_PROJECT_NAME=<project>
```

## Back Up Runtime Data

Run these commands from the repository root unless noted otherwise.

```bash
cd docker
docker compose ps

# Back up the metadata database.
docker compose exec postgres pg_dump -U dbvault dbvault > ../dbvault-meta-$(date +%Y%m%d-%H%M%S).sql
```

If local storage is used for backup files or uploaded kubeconfigs, also archive the `dbvault-data` volume. Adjust the volume name if `COMPOSE_PROJECT_NAME` is not `dbvault`.

```bash
docker run --rm \
  -v dbvault_dbvault-data:/data:ro \
  -v "$PWD/..:/backup" \
  busybox tar czf /backup/dbvault-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

## Upgrade From Source

Use this path when the server has a Git checkout.

```bash
cd docker
docker compose stop api frontend

cd ..
git fetch --all --tags
git checkout <target-tag-or-branch>

# If the target is a tracking branch, update it. Skip this for fixed tags.
# git pull --ff-only

# Build the new images without starting the application yet.
docker build -t dbvault-api:latest -f docker/Dockerfile .
docker build -t dbvault-frontend:latest -f docker/Dockerfile.frontend frontend

cd docker
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api frontend
```

If there are no backend or migration changes, `./deploy.sh -b -f` is enough for a frontend-only upgrade. For API changes, prefer the sequence above so migrations run before the new API starts.

## Upgrade From Release Images

Use this path when deploying images from GitHub Releases. Keep the repository checkout at the matching release version because the default Compose file mounts local source into the containers.

```bash
git fetch --all --tags
git checkout <matching-release-tag>

gh release download --repo mill413/dbvault -p '*.tar.gz'
docker load -i dbvault-images-*.tar.gz

cd docker
docker compose stop api frontend
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api frontend
```

## Verify the Upgrade

```bash
cd docker
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 frontend
curl -f http://127.0.0.1:8000/docs >/dev/null
```

Open `http://localhost:5173`, sign in, and check the dashboard, database list, backup list, and scheduled jobs.

## Roll Back

If the application fails before a schema migration, check out the previous version or reload the previous image archive, then redeploy:

```bash
cd docker
./deploy.sh -b
```

If a migration already changed the metadata database, restore the database dump taken before the upgrade. Review the Alembic migration before attempting `alembic downgrade -1`; not every application-level change is safely reversible.
