# Intent Routing Service

API-only Intent Routing Service for closed-network financial-sector Dify integration.

## Local Quick Start

1. Export the local runtime contract:
   ```bash
   export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
   export INTENT_ROUTING_ENVIRONMENT=dev
   export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
   export RAW_TEXT_KEK_ID=local-kek-001
   export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
   export EMBEDDING_PROVIDER=fake
   export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
   export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
   ```

   Use a new `SERVICE_ID` for each pilot run on a persistent local database.

2. Start PostgreSQL:
   `docker compose up -d postgres`

3. Apply migrations:
   `uv run alembic upgrade head`

4. Start the API:
   `uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000`

5. Seed the pilot:
   `uv run python scripts/seed_pilot.py --base-url http://127.0.0.1:8000 --admin-token ${ADMIN_BOOTSTRAP_TOKEN} --service-id ${SERVICE_ID} --environment ${INTENT_ROUTING_ENVIRONMENT} --state-path ${STATE_PATH}`

6. Compare CSV gate thresholds:
   `uv run python scripts/run_csv_gate.py --base-url http://127.0.0.1:8000 --admin-token ${ADMIN_BOOTSTRAP_TOKEN} --state ${STATE_PATH} --csv docs/pilot/it-helpdesk-pilot-cases.csv --out-dir var/reports`

7. Run a Dify-style runtime smoke:
   `uv run python scripts/smoke_runtime_dify.py --base-url http://127.0.0.1:8000 --state ${STATE_PATH} --query "API timeout 500 에러가 납니다" --expect-decision confident`

8. Inspect masked runtime logs:
   `uv run python scripts/trace_audit_drill.py --base-url http://127.0.0.1:8000 --admin-token ${ADMIN_BOOTSTRAP_TOKEN} --state ${STATE_PATH}`

## Documents

- Local runbook: `docs/ops/intent-routing-local-runbook.md`
- Pilot runbook: `docs/ops/intent-routing-pilot-runbook.md`
- Closed-network deployment: `docs/ops/closed-network-deployment.md`
- Dify guide: `docs/integrations/dify-http-request-node.md`
