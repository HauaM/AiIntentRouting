#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="${0:A:h:h}"
FRONTEND_DIR="${ROOT_DIR}/frontend/intent-routing-console"
LOG_DIR="${ROOT_DIR}/var/logs/local-dev-stack"
DEFAULT_DATABASE_URL="postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing"

typeset -A CALLER_ENVIRONMENT
typeset -a COMPOSE_CMD PNPM_CMD
typeset BACKEND_PID="" FRONTEND_PID="" BACKEND_TAIL_PID="" FRONTEND_TAIL_PID=""
typeset ADMIN_SYSTEM_ADMIN_EMAIL_WAS_SET=0
typeset ADMIN_SYSTEM_ADMIN_PASSWORD_WAS_SET=0
typeset ADMIN_SYSTEM_ADMIN_DISPLAY_NAME_WAS_SET=0
BACKEND_COLOR=$'\033[36m'
FRONTEND_COLOR=$'\033[35m'
RESET_COLOR=$'\033[0m'

for key in DATABASE_URL APP_ENV INTENT_ROUTING_ENVIRONMENT ADMIN_AUTH_MODE \
  ADMIN_BOOTSTRAP_TOKEN ADMIN_SYSTEM_ADMIN_EMAIL ADMIN_SYSTEM_ADMIN_PASSWORD \
  ADMIN_SYSTEM_ADMIN_DISPLAY_NAME RAW_TEXT_KEK_ID RAW_TEXT_KEK_BASE64 \
  RAW_TEXT_LEGACY_KEKS_JSON EMBEDDING_PROVIDER BGE_M3_MODEL_PATH \
  BGE_M3_MODEL_SHA256 BGE_M3_BATCH_SIZE BGE_M3_MAX_TOKENS EMBED_EXAMPLES_FROM \
  LOCAL_DEV_HOST BACKEND_PORT FRONTEND_PORT ADMIN_UI_SERVICE_ID; do
  if (( ${+parameters[$key]} )); then
    CALLER_ENVIRONMENT[$key]="${(P)key}"
  fi
done

(( ${+CALLER_ENVIRONMENT[ADMIN_SYSTEM_ADMIN_EMAIL]} )) && ADMIN_SYSTEM_ADMIN_EMAIL_WAS_SET=1
(( ${+CALLER_ENVIRONMENT[ADMIN_SYSTEM_ADMIN_PASSWORD]} )) && ADMIN_SYSTEM_ADMIN_PASSWORD_WAS_SET=1
(( ${+CALLER_ENVIRONMENT[ADMIN_SYSTEM_ADMIN_DISPLAY_NAME]} )) && ADMIN_SYSTEM_ADMIN_DISPLAY_NAME_WAS_SET=1

log() {
  printf '[local] %s\n' "$*"
}

prefix_logs() {
  local label="$1"
  local color="$2"
  if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    awk -v prefix="${color}[${label}] ${RESET_COLOR}" '{ print prefix $0; fflush(); }'
  else
    awk -v prefix="[${label}] " '{ print prefix $0; fflush(); }'
  fi
}

fail() {
  printf '[local] %s\n' "$*" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || \
    fail "Missing required command: ${command_name}"
}

load_local_env() {
  local key value

  if [[ -f "${ROOT_DIR}/.env" ]]; then
    log "Loading ${ROOT_DIR}/.env"
    set -a
    source "${ROOT_DIR}/.env"
    set +a
  fi

  for key value in ${(kv)CALLER_ENVIRONMENT}; do
    export "${key}=${value}"
  done
}

apply_local_defaults() {
  export HOST="${LOCAL_DEV_HOST:-127.0.0.1}"
  export BACKEND_PORT="${BACKEND_PORT:-30141}"
  export FRONTEND_PORT="${FRONTEND_PORT:-30140}"
  export ADMIN_UI_SERVICE_ID="${ADMIN_UI_SERVICE_ID:-it-helpdesk-pilot-sprint10-operation-monitoring}"
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
  if [[ -z "${RAW_TEXT_LEGACY_KEKS_JSON:-}" ]]; then
    export RAW_TEXT_LEGACY_KEKS_JSON="{}"
  else
    export RAW_TEXT_LEGACY_KEKS_JSON
  fi
  export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-fake}"
  export BGE_M3_MODEL_PATH="${BGE_M3_MODEL_PATH:-/models/bge-m3}"
  export BGE_M3_MODEL_SHA256="${BGE_M3_MODEL_SHA256:-}"
  export BGE_M3_BATCH_SIZE="${BGE_M3_BATCH_SIZE:-16}"
  export BGE_M3_MAX_TOKENS="${BGE_M3_MAX_TOKENS:-256}"
  export EMBED_EXAMPLES_FROM="${EMBED_EXAMPLES_FROM:-masked}"
}

resolve_pnpm_command() {
  if command -v pnpm >/dev/null 2>&1; then
    PNPM_CMD=(pnpm)
  elif command -v corepack >/dev/null 2>&1; then
    PNPM_CMD=(corepack pnpm)
  else
    fail "Missing required command: pnpm or corepack"
  fi
}

resolve_compose_command() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
  else
    fail "Docker Compose is unavailable. Install the Docker Compose plugin with Homebrew."
  fi
}

ensure_colima() {
  require_command colima
  if ! colima status >/dev/null 2>&1; then
    log "Starting Colima"
    colima start
  else
    log "Colima is already running"
  fi

  if [[ "$(docker context show 2>/dev/null || true)" != "colima" ]]; then
    log "Selecting Docker context: colima"
    docker context use colima >/dev/null
  fi
}

default_db_port_owners() {
  docker ps --format '{{.ID}} {{.Names}} {{.Image}} {{.Ports}}' | \
    awk '/(0\.0\.0\.0|127\.0\.0\.1|\[::\]):30142->5432\/tcp/'
}

compose_postgres_is_running() {
  "${COMPOSE_CMD[@]}" ps --status running --services postgres 2>/dev/null | grep -qx postgres
}

wait_for_compose_postgres() {
  local attempt
  for attempt in {1..60}; do
    if "${COMPOSE_CMD[@]}" exec -T postgres pg_isready -U intent -d intent_routing >/dev/null 2>&1; then
      log "PostgreSQL is ready"
      return
    fi
    sleep 1
  done
  fail "Timed out waiting for Compose PostgreSQL readiness"
}

ensure_local_database() {
  local owners

  if [[ "${DATABASE_URL}" != "${DEFAULT_DATABASE_URL}" ]]; then
    log "Skipping Colima and Compose PostgreSQL management for custom DATABASE_URL"
    return
  fi

  require_command docker
  ensure_colima
  resolve_compose_command

  if compose_postgres_is_running; then
    log "Compose PostgreSQL is already running"
    wait_for_compose_postgres
    return
  fi

  owners="$(default_db_port_owners)"
  if [[ -n "${owners}" ]]; then
    printf '[local] Port 30142 is already used by another container:\n%s\n' "${owners}" >&2
    fail "Stop that container or set DATABASE_URL to the intended PostgreSQL instance."
  fi

  log "Starting Compose PostgreSQL"
  "${COMPOSE_CMD[@]}" up -d postgres
  wait_for_compose_postgres
}

find_port_pids() {
  local port="$1"
  lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
}

stop_port_listeners() {
  local port="$1"
  local label="$2"
  local attempt pid
  local -a pids remaining

  pids=("${(@f)$(find_port_pids "${port}")}")
  pids=("${(@)pids:#}")
  if (( ${#pids[@]} == 0 )); then
    log "No existing ${label} process on port ${port}"
    return
  fi

  log "Stopping existing ${label} process(es) on port ${port}: ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true

  for attempt in {1..20}; do
    remaining=()
    for pid in "${pids[@]}"; do
      kill -0 "${pid}" 2>/dev/null && remaining+=("${pid}")
    done
    (( ${#remaining[@]} == 0 )) && return
    sleep 0.25
  done

  log "Force stopping ${label} process(es): ${remaining[*]}"
  kill -9 "${remaining[@]}" 2>/dev/null || true
}

cleanup_stale_log_followers() {
  local -a pids
  pids=("${(@f)$(pgrep -u "${USER}" -f "tail -n \\+1 -F ${LOG_DIR}/(backend|frontend)\\.log" 2>/dev/null || true)}")
  pids=("${(@)pids:#}")
  (( ${#pids[@]} == 0 )) && return
  log "Stopping stale local log follower process(es): ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true
}

cleanup() {
  local pid
  local -a pids
  pids=("${FRONTEND_PID}" "${BACKEND_PID}" "${FRONTEND_TAIL_PID}" "${BACKEND_TAIL_PID}")
  pids=("${(@)pids:#}")
  if (( ${#pids[@]} > 0 )); then
    log "Stopping local development stack"
    for pid in "${pids[@]}"; do
      kill "${pid}" 2>/dev/null || true
    done
  fi
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local pid="$3"
  local attempt

  for attempt in {1..120}; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      log "${label} is ready: ${url}"
      return
    fi
    kill -0 "${pid}" 2>/dev/null || fail "${label} exited before becoming ready"
    sleep 0.5
  done
  fail "Timed out waiting for ${label}: ${url}"
}

admin_service_metrics_status() {
  curl -sS -o /dev/null -w '%{http_code}' \
    -H "X-Admin-Token: ${ADMIN_BOOTSTRAP_TOKEN}" \
    -H "X-Actor-Id: local-dev-stack-macos" \
    -H "X-Actor-Roles: system_admin" \
    -H "X-Service-Scope: ${ADMIN_UI_SERVICE_ID}" \
    "http://${HOST}:${BACKEND_PORT}/admin/v1/services/${ADMIN_UI_SERVICE_ID}/runtime-metrics?window_hours=24"
}

seed_local_admin_service() {
  local status_code state_path
  status_code="$(admin_service_metrics_status)"
  state_path="${ROOT_DIR}/var/pilot/${ADMIN_UI_SERVICE_ID}.state.secret.json"

  if [[ "${status_code}" == "200" ]]; then
    log "Admin UI service is already seeded: ${ADMIN_UI_SERVICE_ID}"
    return
  fi
  [[ "${status_code}" == "404" ]] || fail "Unexpected Admin UI service probe status: ${status_code}"

  log "Seeding Admin UI service: ${ADMIN_UI_SERVICE_ID}"
  (
    cd "${ROOT_DIR}"
    uv run python scripts/seed_pilot.py \
      --base-url "http://${HOST}:${BACKEND_PORT}" \
      --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
      --service-id "${ADMIN_UI_SERVICE_ID}" \
      --environment "${INTENT_ROUTING_ENVIRONMENT}" \
      --state-path "${state_path}"
  ) 2>&1 | prefix_logs backend "${BACKEND_COLOR}"
}

run_migrations() {
  log "Running database migrations"
  (cd "${ROOT_DIR}" && uv run alembic upgrade head) 2>&1 | \
    prefix_logs backend "${BACKEND_COLOR}"
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

  if [[ -z "${owner_email}" || "${owner_email:l}" == "${ADMIN_SYSTEM_ADMIN_EMAIL:l}" ]]; then
    log "Admin UI login account is configured: ${ADMIN_SYSTEM_ADMIN_EMAIL}"
    return
  fi

  if (( ADMIN_SYSTEM_ADMIN_EMAIL_WAS_SET || ADMIN_SYSTEM_ADMIN_PASSWORD_WAS_SET || ADMIN_SYSTEM_ADMIN_DISPLAY_NAME_WAS_SET )); then
    fail "Existing system_admin owner is ${owner_email}, but ADMIN_SYSTEM_ADMIN_EMAIL is ${ADMIN_SYSTEM_ADMIN_EMAIL}. Set the existing owner email or intentionally reset the local database."
  fi

  log "Existing system_admin owner detected: ${owner_email}"
  log "Skipping default startup system_admin provisioning to preserve single-owner policy"
  unset ADMIN_SYSTEM_ADMIN_EMAIL ADMIN_SYSTEM_ADMIN_PASSWORD ADMIN_SYSTEM_ADMIN_DISPLAY_NAME
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

  tail -n +1 -F "${backend_log}" 2>/dev/null | \
    prefix_logs backend "${BACKEND_COLOR}" &
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

  tail -n +1 -F "${frontend_log}" 2>/dev/null | \
    prefix_logs frontend "${FRONTEND_COLOR}" &
  FRONTEND_TAIL_PID="$!"
}

wait_for_applications() {
  while kill -0 "${BACKEND_PID}" 2>/dev/null && kill -0 "${FRONTEND_PID}" 2>/dev/null; do
    sleep 1
  done
  fail "A local application process exited. Check the prefixed logs above."
}

main() {
  [[ "$(uname -s)" == "Darwin" ]] || fail "This script supports macOS only."
  load_local_env
  apply_local_defaults

  require_command uv
  require_command curl
  require_command lsof
  resolve_pnpm_command

  mkdir -p "${LOG_DIR}"
  trap cleanup EXIT
  trap 'cleanup; exit 130' INT TERM

  stop_port_listeners "${BACKEND_PORT}" "backend"
  stop_port_listeners "${FRONTEND_PORT}" "frontend"
  cleanup_stale_log_followers
  ensure_local_database
  run_migrations
  prepare_startup_system_admin_provisioning
  start_backend
  seed_local_admin_service
  start_frontend

  log "Local development stack is running. Press Ctrl+C to stop applications; PostgreSQL will remain running."
  wait_for_applications
}

main "$@"
