#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend/intent-routing-console"
LOG_DIR="${ROOT_DIR}/var/logs/local-dev-stack"

HOST="${HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-30141}"
FRONTEND_PORT="${FRONTEND_PORT:-30140}"
ADMIN_UI_SERVICE_ID="${ADMIN_UI_SERVICE_ID:-it-helpdesk-pilot-sprint10-operation-monitoring}"
DEFAULT_DATABASE_URL="postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing"
ADMIN_SYSTEM_ADMIN_EMAIL_WAS_SET=0
ADMIN_SYSTEM_ADMIN_PASSWORD_WAS_SET=0
ADMIN_SYSTEM_ADMIN_DISPLAY_NAME_WAS_SET=0
[[ -n "${ADMIN_SYSTEM_ADMIN_EMAIL+x}" ]] && ADMIN_SYSTEM_ADMIN_EMAIL_WAS_SET=1
[[ -n "${ADMIN_SYSTEM_ADMIN_PASSWORD+x}" ]] && ADMIN_SYSTEM_ADMIN_PASSWORD_WAS_SET=1
[[ -n "${ADMIN_SYSTEM_ADMIN_DISPLAY_NAME+x}" ]] && ADMIN_SYSTEM_ADMIN_DISPLAY_NAME_WAS_SET=1

export DATABASE_URL="${DATABASE_URL:-${DEFAULT_DATABASE_URL}}"
export APP_ENV="${APP_ENV:-local}"
export INTENT_ROUTING_ENVIRONMENT="${INTENT_ROUTING_ENVIRONMENT:-dev}"
export ADMIN_AUTH_MODE="${ADMIN_AUTH_MODE:-trusted_headers}"
export ADMIN_BOOTSTRAP_TOKEN="${ADMIN_BOOTSTRAP_TOKEN:-local-admin-token}"
export ADMIN_SYSTEM_ADMIN_EMAIL="${ADMIN_SYSTEM_ADMIN_EMAIL:-local-admin@example.com}"
export ADMIN_SYSTEM_ADMIN_PASSWORD="${ADMIN_SYSTEM_ADMIN_PASSWORD:-local-admin-password}"
export ADMIN_SYSTEM_ADMIN_DISPLAY_NAME="${ADMIN_SYSTEM_ADMIN_DISPLAY_NAME:-Local Admin}"
export RAW_TEXT_KEK_ID="${RAW_TEXT_KEK_ID:-local-kek-001}"
export RAW_TEXT_KEK_BASE64="${RAW_TEXT_KEK_BASE64:-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=}"
export RAW_TEXT_LEGACY_KEKS_JSON="${RAW_TEXT_LEGACY_KEKS_JSON:-{}}"
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-fake}"
export BGE_M3_MODEL_PATH="${BGE_M3_MODEL_PATH:-/models/bge-m3}"
export BGE_M3_MODEL_SHA256="${BGE_M3_MODEL_SHA256:-}"
export BGE_M3_BATCH_SIZE="${BGE_M3_BATCH_SIZE:-16}"
export BGE_M3_MAX_TOKENS="${BGE_M3_MAX_TOKENS:-256}"
export EMBED_EXAMPLES_FROM="${EMBED_EXAMPLES_FROM:-masked}"

BACKEND_PID=""
FRONTEND_PID=""
BACKEND_TAIL_PID=""
FRONTEND_TAIL_PID=""
PNPM_CMD=()

log() {
  printf '[local] %s\n' "$*"
}

prefix_logs() {
  local label="$1"
  awk -v prefix="[${label}] " '{ print prefix $0; fflush(); }'
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf '[local] Missing required command: %s\n' "${command_name}" >&2
    exit 1
  fi
}

resolve_pnpm_command() {
  if command -v pnpm >/dev/null 2>&1; then
    PNPM_CMD=(pnpm)
    return
  fi

  if command -v corepack >/dev/null 2>&1; then
    PNPM_CMD=(corepack pnpm)
    return
  fi

  printf '[local] Missing required command: pnpm or corepack\n' >&2
  exit 1
}

default_db_port_owners() {
  docker ps --format '{{.ID}} {{.Names}} {{.Image}} {{.Ports}}' \
    | awk '/(0\.0\.0\.0|127\.0\.0\.1|\[::\]):30142->5432\/tcp/'
}

compose_postgres_is_running() {
  docker compose ps --status running --services postgres 2>/dev/null | grep -qx postgres
}

wait_for_compose_postgres() {
  for _ in {1..60}; do
    if docker compose exec -T postgres pg_isready -U intent -d intent_routing >/dev/null 2>&1; then
      log "postgres is ready"
      return
    fi
    sleep 1
  done

  printf '[local] Timed out waiting for compose postgres readiness\n' >&2
  exit 1
}

ensure_local_database() {
  local owners

  if [[ "${DATABASE_URL}" != "${DEFAULT_DATABASE_URL}" ]]; then
    log "Skipping compose postgres management for custom DATABASE_URL"
    return
  fi

  require_command docker

  if compose_postgres_is_running; then
    log "Compose postgres is already running"
    wait_for_compose_postgres
    return
  fi

  owners="$(default_db_port_owners)"
  if [[ -n "${owners}" ]]; then
    printf '[local] Port 30142 is already used by another container:\n' >&2
    printf '%s\n' "${owners}" | sed 's/^/[local]   /' >&2
    printf '[local] Stop that container or set DATABASE_URL to a PostgreSQL instance with the expected credentials.\n' >&2
    printf '[local] For this project default, use: docker compose up -d postgres\n' >&2
    exit 1
  fi

  log "Starting compose postgres"
  docker compose up -d postgres
  wait_for_compose_postgres
}

find_port_pids() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return
  fi

  if command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "${port}" 2>/dev/null | tr ' ' '\n' | awk 'NF'
    return
  fi

  printf '[local] lsof or fuser is required to inspect port %s\n' "${port}" >&2
  exit 1
}

stop_port_listeners() {
  local port="$1"
  local label="$2"
  local pids=()
  local remaining=()

  mapfile -t pids < <(find_port_pids "${port}" | awk 'NF')
  if ((${#pids[@]} == 0)); then
    log "No existing ${label} process on port ${port}"
    return
  fi

  log "Stopping existing ${label} process(es) on port ${port}: ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true

  for _ in {1..20}; do
    remaining=()
    for pid in "${pids[@]}"; do
      if kill -0 "${pid}" 2>/dev/null; then
        remaining+=("${pid}")
      fi
    done
    ((${#remaining[@]} == 0)) && return
    sleep 0.25
  done

  log "Force stopping ${label} process(es): ${remaining[*]}"
  kill -9 "${remaining[@]}" 2>/dev/null || true
}

cleanup_stale_log_followers() {
  local pids=()

  if ! command -v pgrep >/dev/null 2>&1; then
    return
  fi

  mapfile -t pids < <(
    pgrep -u "${USER}" -f "tail -n \\+1 -F ${LOG_DIR}/(backend|frontend)\\.log" || true
  )
  if ((${#pids[@]} == 0)); then
    return
  fi

  log "Stopping stale local log follower process(es): ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true
}

cleanup() {
  local pids=()

  [[ -n "${FRONTEND_PID}" ]] && pids+=("${FRONTEND_PID}")
  [[ -n "${BACKEND_PID}" ]] && pids+=("${BACKEND_PID}")
  [[ -n "${FRONTEND_TAIL_PID}" ]] && pids+=("${FRONTEND_TAIL_PID}")
  [[ -n "${BACKEND_TAIL_PID}" ]] && pids+=("${BACKEND_TAIL_PID}")

  if ((${#pids[@]} > 0)); then
    log "Stopping local dev stack"
    kill "${pids[@]}" 2>/dev/null || true
  fi
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local pid="$3"

  for _ in {1..120}; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      log "${label} is ready: ${url}"
      return
    fi
    if ! kill -0 "${pid}" 2>/dev/null; then
      printf '[local] %s exited before becoming ready\n' "${label}" >&2
      exit 1
    fi
    sleep 0.5
  done

  printf '[local] Timed out waiting for %s: %s\n' "${label}" "${url}" >&2
  exit 1
}

admin_service_metrics_status() {
  curl -sS -o /dev/null -w '%{http_code}' \
    -H "X-Admin-Token: ${ADMIN_BOOTSTRAP_TOKEN}" \
    -H "X-Actor-Id: local-dev-stack" \
    -H "X-Actor-Roles: system_admin" \
    -H "X-Service-Scope: ${ADMIN_UI_SERVICE_ID}" \
    "http://${HOST}:${BACKEND_PORT}/admin/v1/services/${ADMIN_UI_SERVICE_ID}/runtime-metrics?window_hours=24"
}

seed_local_admin_service() {
  local status_code
  local state_path="${ROOT_DIR}/var/pilot/${ADMIN_UI_SERVICE_ID}.state.secret.json"

  status_code="$(admin_service_metrics_status)"
  if [[ "${status_code}" == "200" ]]; then
    log "Admin UI service is already seeded: ${ADMIN_UI_SERVICE_ID}"
    return
  fi

  if [[ "${status_code}" != "404" ]]; then
    printf '[local] Unexpected Admin UI service probe status: %s\n' "${status_code}" >&2
    exit 1
  fi

  log "Seeding Admin UI service: ${ADMIN_UI_SERVICE_ID}"
  (
    cd "${ROOT_DIR}"
    uv run python scripts/seed_pilot.py \
      --base-url "http://${HOST}:${BACKEND_PORT}" \
      --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
      --service-id "${ADMIN_UI_SERVICE_ID}" \
      --environment "${INTENT_ROUTING_ENVIRONMENT}" \
      --state-path "${state_path}"
  ) 2>&1 | prefix_logs backend
}

run_migrations() {
  log "Running DB migration"
  (cd "${ROOT_DIR}" && uv run alembic upgrade head) 2>&1 | prefix_logs backend
}

current_system_admin_email() {
  (
    cd "${ROOT_DIR}"
    uv run python - <<'PY'
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from intent_routing.db.models import AdminUser, AdminUserRole
from intent_routing.db.session import get_database_url

engine = create_engine(get_database_url())
try:
    with Session(engine) as session:
        email = session.scalar(
            select(AdminUser.email)
            .join(AdminUserRole, AdminUserRole.user_id == AdminUser.user_id)
            .where(AdminUserRole.role == "system_admin")
            .limit(1)
        )
        if email:
            print(email)
finally:
    engine.dispose()
PY
  )
}

prepare_startup_system_admin_provisioning() {
  local owner_email

  owner_email="$(current_system_admin_email)"
  if [[ -z "${owner_email}" ]]; then
    log "Admin UI login account is configured: ${ADMIN_SYSTEM_ADMIN_EMAIL}"
    return
  fi

  if [[ "${owner_email,,}" == "${ADMIN_SYSTEM_ADMIN_EMAIL,,}" ]]; then
    log "Admin UI login account is configured: ${ADMIN_SYSTEM_ADMIN_EMAIL}"
    return
  fi

  if ((ADMIN_SYSTEM_ADMIN_EMAIL_WAS_SET || ADMIN_SYSTEM_ADMIN_PASSWORD_WAS_SET || ADMIN_SYSTEM_ADMIN_DISPLAY_NAME_WAS_SET)); then
    printf '[local] Existing system_admin owner is %s, but ADMIN_SYSTEM_ADMIN_EMAIL is %s.\n' \
      "${owner_email}" "${ADMIN_SYSTEM_ADMIN_EMAIL}" >&2
    printf '[local] Startup provisioning will not transfer system_admin ownership.\n' >&2
    printf '[local] Set ADMIN_SYSTEM_ADMIN_EMAIL to the existing owner email to rotate its password, or reset the local database intentionally.\n' >&2
    exit 1
  fi

  log "Existing system_admin owner detected: ${owner_email}"
  log "Skipping default startup system_admin provisioning to preserve single-owner policy"
  unset ADMIN_SYSTEM_ADMIN_EMAIL
  unset ADMIN_SYSTEM_ADMIN_PASSWORD
  unset ADMIN_SYSTEM_ADMIN_DISPLAY_NAME
}

start_backend() {
  local backend_log="${LOG_DIR}/backend.log"

  : > "${backend_log}"
  log "Starting backend on http://${HOST}:${BACKEND_PORT}"
  (
    cd "${ROOT_DIR}"
    uv run uvicorn intent_routing.main:create_app --factory --host "${HOST}" --port "${BACKEND_PORT}"
  ) >"${backend_log}" 2>&1 &
  BACKEND_PID="$!"

  tail -n +1 -F "${backend_log}" 2>/dev/null | prefix_logs backend &
  BACKEND_TAIL_PID="$!"

  wait_for_url "backend" "http://${HOST}:${BACKEND_PORT}/healthz" "${BACKEND_PID}"
}

start_frontend() {
  local frontend_log="${LOG_DIR}/frontend.log"

  : > "${frontend_log}"
  log "Starting frontend on http://${HOST}:${FRONTEND_PORT}"
  (
    cd "${FRONTEND_DIR}"
    HOST="${HOST}" \
      PORT="${FRONTEND_PORT}" \
      ADMIN_API_PROXY="http://${HOST}:${BACKEND_PORT}" \
      CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-true}" \
      WATCHPACK_POLLING="${WATCHPACK_POLLING:-true}" \
      CHOKIDAR_INTERVAL="${CHOKIDAR_INTERVAL:-1000}" \
      "${PNPM_CMD[@]}" dev
  ) >"${frontend_log}" 2>&1 &
  FRONTEND_PID="$!"

  tail -n +1 -F "${frontend_log}" 2>/dev/null | prefix_logs frontend &
  FRONTEND_TAIL_PID="$!"
}

main() {
  require_command uv
  require_command curl
  resolve_pnpm_command

  mkdir -p "${LOG_DIR}"
  trap cleanup EXIT INT TERM

  stop_port_listeners "${BACKEND_PORT}" "backend"
  stop_port_listeners "${FRONTEND_PORT}" "frontend"
  cleanup_stale_log_followers
  ensure_local_database
  run_migrations
  prepare_startup_system_admin_provisioning
  start_backend
  seed_local_admin_service
  start_frontend

  log "Local dev stack is running. Press Ctrl+C to stop."
  wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
}

main "$@"
