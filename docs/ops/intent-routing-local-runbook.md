# Intent Routing Local Runbook

## Prerequisites

- Python 3.12
- uv
- Docker with Compose
- Local PostgreSQL exposed on `127.0.0.1:5432`

## Environment

Use `.env.example` as the local contract. For local smoke tests, set:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export EMBEDDING_PROVIDER=fake
```

## Database

```bash
docker compose up -d postgres
uv run alembic upgrade head
```

## API

```bash
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
curl -s http://127.0.0.1:8000/healthz
```

Expected health response:

```json
{"status":"ok"}
```

## Account Auth

Use `POST /admin/v1/auth/bootstrap-admin` only for initial local setup or a
controlled break-glass recovery path. It requires `X-Admin-Token` to match the
local `ADMIN_BOOTSTRAP_TOKEN`, creates the first `system_admin`, and returns
`409` after an initial system admin already exists. Do not use this trusted
header flow as normal Admin UI authentication.

These local examples keep the bootstrap token and password out of `curl`
process arguments by writing request config and JSON to `0600` temp files. Local
shell history and process visibility rules still apply when exporting secrets;
run them from a trusted local shell and unset secrets afterward.

```bash
export LOCAL_ADMIN_PASSWORD='change-me-for-local-only'

BOOTSTRAP_PAYLOAD="$(mktemp)"
BOOTSTRAP_HEADERS="$(mktemp)"
LOGIN_PAYLOAD="$(mktemp)"
COOKIE_JAR="$(mktemp)"
chmod 600 "${BOOTSTRAP_PAYLOAD}" "${BOOTSTRAP_HEADERS}" "${LOGIN_PAYLOAD}" "${COOKIE_JAR}"

cleanup_local_admin_auth() {
  rm -f "${BOOTSTRAP_PAYLOAD}" "${BOOTSTRAP_HEADERS}" "${LOGIN_PAYLOAD}" "${COOKIE_JAR}"
  unset LOCAL_ADMIN_PASSWORD ADMIN_BOOTSTRAP_TOKEN
}
trap cleanup_local_admin_auth EXIT
trap 'cleanup_local_admin_auth; exit 130' INT
trap 'cleanup_local_admin_auth; exit 143' TERM

python -c 'import json, os, sys; payload = {"user_id": "local-system-admin", "email": "admin@example.local", "display_name": "Local System Admin", "password": os.environ["LOCAL_ADMIN_PASSWORD"]}; open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(payload))' "${BOOTSTRAP_PAYLOAD}"
python -c 'import os, sys; open(sys.argv[1], "w", encoding="utf-8").write("header = \"Content-Type: application/json\"\nheader = \"X-Admin-Token: " + os.environ["ADMIN_BOOTSTRAP_TOKEN"] + "\"\n")' "${BOOTSTRAP_HEADERS}"

curl -s -X POST http://127.0.0.1:8000/admin/v1/auth/bootstrap-admin \
  --config "${BOOTSTRAP_HEADERS}" \
  --data-binary @"${BOOTSTRAP_PAYLOAD}"
```

Normal browser/Admin UI login uses the server-issued `irt_admin_session`
HttpOnly cookie. The Admin UI posts credentials to `/admin/v1/auth/login`,
stores the cookie via the browser, and then reads session and service scope from
`/admin/v1/auth/me` and `/admin/v1/me/services`.

```bash
python -c 'import json, os, sys; payload = {"email": "admin@example.local", "password": os.environ["LOCAL_ADMIN_PASSWORD"]}; open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(payload))' "${LOGIN_PAYLOAD}"

curl -s -c "${COOKIE_JAR}" -X POST http://127.0.0.1:8000/admin/v1/auth/login \
  -H "Content-Type: application/json" \
  --data-binary @"${LOGIN_PAYLOAD}"

curl -s -b "${COOKIE_JAR}" http://127.0.0.1:8000/admin/v1/auth/me
curl -s -b "${COOKIE_JAR}" http://127.0.0.1:8000/admin/v1/me/services
cleanup_local_admin_auth
trap - EXIT INT TERM
```

Normal Admin UI requests must not send `X-Admin-Token`, `X-Actor-Id`,
`X-Actor-Roles`, or `X-Service-Scope`. Those trusted headers are reserved for
controlled bootstrap, break-glass, or explicitly configured internal automation
paths, not the browser UI cookie flow.

## Verification

For the GitHub CI baseline and the matching local reproduction commands, see `docs/ops/ci-verification.md`.

```bash
uv run ruff check .
uv run mypy src tests
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest -v
```

## Closed-Network Deployment

For the Compose-based closed-network pilot path, use `docs/ops/closed-network-deployment.md`.
