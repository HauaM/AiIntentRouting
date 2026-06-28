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

## Verification

```bash
uv run ruff check .
uv run mypy src tests
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest -v
```

## Closed-Network Deployment

For the Compose-based closed-network pilot path, use `docs/ops/closed-network-deployment.md`.
