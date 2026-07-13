#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-dbvault-it}"
API_IMAGE="${DBVAULT_IT_API_IMAGE:-dbvault-api:integration}"

export DBVAULT_IT_MYSQL_PORT="${DBVAULT_IT_MYSQL_PORT:-13306}"
export DBVAULT_IT_POSTGRES_PORT="${DBVAULT_IT_POSTGRES_PORT:-15433}"
export DBVAULT_IT_MINIO_PORT="${DBVAULT_IT_MINIO_PORT:-19000}"
export DBVAULT_IT_MINIO_CONSOLE_PORT="${DBVAULT_IT_MINIO_CONSOLE_PORT:-19001}"
export DBVAULT_IT_MINIO_ENDPOINT="${DBVAULT_IT_MINIO_ENDPOINT:-http://127.0.0.1:${DBVAULT_IT_MINIO_PORT}}"

export COMPOSE_PROJECT_NAME
export DBVAULT_POSTGRES_PASSWORD="${DBVAULT_POSTGRES_PASSWORD:-dbvault-integration-password}"
export DBVAULT_JWT_SECRET="${DBVAULT_JWT_SECRET:-dbvault-integration-jwt-secret}"
export DBVAULT_ENCRYPTION_KEY="${DBVAULT_ENCRYPTION_KEY:-IZN7N5Btn6qgQ9M2MXb2A_TwdGNVRIhJHiAiHrEK_x0=}"

cd "$PROJECT_ROOT"

cleanup() {
    if [[ "${DBVAULT_IT_KEEP_SERVICES:-false}" != "true" ]]; then
        docker compose -f "$COMPOSE_FILE" --profile integration down -v --remove-orphans >/dev/null
    fi
}

trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" --profile integration up -d --wait --wait-timeout 90 mysql-source postgres-source minio

if [[ "${DBVAULT_IT_SKIP_BUILD:-false}" != "true" ]]; then
    docker build -t "$API_IMAGE" -f "$PROJECT_ROOT/docker/Dockerfile" "$PROJECT_ROOT"
fi

docker run --rm \
    --network host \
    -v "$PROJECT_ROOT:/app" \
    -w /app \
    -e DBVAULT_RUN_INTEGRATION=1 \
    -e DBVAULT_IT_MYSQL_HOST="${DBVAULT_IT_MYSQL_HOST:-127.0.0.1}" \
    -e DBVAULT_IT_MYSQL_PORT="$DBVAULT_IT_MYSQL_PORT" \
    -e DBVAULT_IT_MYSQL_ROOT_PASSWORD="${DBVAULT_IT_MYSQL_ROOT_PASSWORD:-root-password}" \
    -e DBVAULT_IT_MYSQL_USER="${DBVAULT_IT_MYSQL_USER:-backup}" \
    -e DBVAULT_IT_MYSQL_PASSWORD="${DBVAULT_IT_MYSQL_PASSWORD:-backup-password}" \
    -e DBVAULT_IT_POSTGRES_HOST="${DBVAULT_IT_POSTGRES_HOST:-127.0.0.1}" \
    -e DBVAULT_IT_POSTGRES_PORT="$DBVAULT_IT_POSTGRES_PORT" \
    -e DBVAULT_IT_POSTGRES_USER="${DBVAULT_IT_POSTGRES_USER:-backup}" \
    -e DBVAULT_IT_POSTGRES_PASSWORD="${DBVAULT_IT_POSTGRES_PASSWORD:-backup-password}" \
    -e DBVAULT_IT_MINIO_ENDPOINT="$DBVAULT_IT_MINIO_ENDPOINT" \
    -e DBVAULT_IT_MINIO_ACCESS_KEY="${DBVAULT_IT_MINIO_ACCESS_KEY:-minioadmin}" \
    -e DBVAULT_IT_MINIO_SECRET_KEY="${DBVAULT_IT_MINIO_SECRET_KEY:-minioadmin}" \
    -e DBVAULT_IT_MINIO_BUCKET="${DBVAULT_IT_MINIO_BUCKET:-dbvault-integration}" \
    "$API_IMAGE" \
    python -m pytest tests/integration "$@"
