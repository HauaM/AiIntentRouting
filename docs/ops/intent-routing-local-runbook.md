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
- Admin login: `local-admin@example.com` / `local-admin-password` from startup provisioning variables

The script exports `ADMIN_SYSTEM_ADMIN_EMAIL`, `ADMIN_SYSTEM_ADMIN_PASSWORD`,
and `ADMIN_SYSTEM_ADMIN_DISPLAY_NAME` so the backend creates or synchronizes the
local `system_admin` during startup. In non-local deployments, omit those
variables to skip startup account creation.

## Environment

Use `.env.example` as the local contract. For local smoke tests, set:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing
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

## Verification

For the GitHub CI baseline and the matching local reproduction commands, see `docs/ops/ci-verification.md`.

```bash
uv run ruff check .
uv run mypy src tests
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest -v
```

## Closed-Network Deployment

For the Compose-based closed-network pilot path, use `docs/ops/closed-network-deployment.md`.
