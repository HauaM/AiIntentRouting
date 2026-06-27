# Intent Routing Service

API-only Intent Routing Service for closed-network financial-sector Dify integration.

## Local Quick Start

1. Start PostgreSQL:
   `docker compose up -d postgres`

2. Apply migrations:
   `DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run alembic upgrade head`

3. Start the API:
   `uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000`

4. Seed the pilot:
   `uv run python scripts/seed_pilot.py --base-url http://127.0.0.1:8000 --service-id it-helpdesk-pilot --environment dev`

5. Run a Dify-style runtime smoke:
   `uv run python scripts/smoke_runtime_dify.py --base-url http://127.0.0.1:8000 --state var/pilot/it-helpdesk-pilot.state.secret.json --query "API timeout 500 에러가 납니다" --expect-decision confident`

## Documents

- Local runbook: `docs/ops/intent-routing-local-runbook.md`
- Pilot runbook: `docs/ops/intent-routing-pilot-runbook.md`
- Dify guide: `docs/integrations/dify-http-request-node.md`
