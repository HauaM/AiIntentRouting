# Intent Routing Local Runbook

## Prerequisites

- Python 3.12
- uv
- Docker with Compose
- Local PostgreSQL exposed on `127.0.0.1:30142`

## One-command Admin UI Stack

For local Admin UI work, run the backend, migrations, seed data, and frontend
with the project script:

```bash
./scripts/run_local_dev_stack.sh
```

Defaults:

- Backend: `http://127.0.0.1:30141`
- Frontend: `http://127.0.0.1:30140`
- PostgreSQL: `127.0.0.1:30142`
- Admin login on a fresh local DB: `local-admin@example.com` / `local-admin-password` from startup provisioning variables

The script exports `ADMIN_SYSTEM_ADMIN_EMAIL`, `ADMIN_SYSTEM_ADMIN_PASSWORD`,
and `ADMIN_SYSTEM_ADMIN_DISPLAY_NAME` so the backend creates or synchronizes the
local `system_admin` during startup. In non-local deployments, omit those
variables to skip startup account creation.

If the local DB already has a different `system_admin`, the script preserves that
owner and skips the default `local-admin@example.com` provisioning variables.
This keeps the single-owner policy intact and avoids an app startup failure. Log
in with the existing owner account, or explicitly set `ADMIN_SYSTEM_ADMIN_EMAIL`
to that existing owner email plus `ADMIN_SYSTEM_ADMIN_PASSWORD` to rotate its
password. To recreate the default local account, intentionally reset the local DB
first.

## Environment

Use `.env.example` as the local contract. For local smoke tests, set:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing
export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod
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
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest -v
```

## Closed-Network Deployment

For the Compose-based closed-network pilot path, use `docs/ops/closed-network-deployment.md`.
