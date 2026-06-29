# Intent Routing Service

API-only Intent Routing Service for closed-network financial-sector Dify integration.

## Local Quick Start

1. Export the local runtime contract:
   ```bash
   export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
   export INTENT_ROUTING_ENVIRONMENT=dev
   export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
   export RAW_TEXT_KEK_ID=local-kek-001
   export RAW_TEXT_KEK_BASE64="$(openssl rand -base64 32)"
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

5. Run the Sprint 5 pilot rehearsal before Dify handoff:
   `uv run python scripts/run_pilot_rehearsal.py --mode local --base-url http://127.0.0.1:8000 --admin-token ${ADMIN_BOOTSTRAP_TOKEN} --service-id ${SERVICE_ID} --environment ${INTENT_ROUTING_ENVIRONMENT} --state-path ${STATE_PATH} --csv-tier standard --required-preset balanced --out-dir var/evidence/${SERVICE_ID}/rehearsal`

   The rehearsal performs the Sprint 4 e2e smoke, Dify smoke matrix, ops evidence export, CSV baseline placeholder, and recursive secret scan, then writes `pilot-rehearsal-manifest.json` and `pilot-rehearsal-manifest.md`.

6. Use the lower-level Sprint 4 e2e smoke only for diagnosis:
   `uv run python scripts/run_pilot_e2e_smoke.py --base-url http://127.0.0.1:8000 --admin-token ${ADMIN_BOOTSTRAP_TOKEN} --service-id ${SERVICE_ID} --environment ${INTENT_ROUTING_ENVIRONMENT} --state-path ${STATE_PATH} --csv-tier standard --required-preset balanced --out-dir var/evidence/${SERVICE_ID}/rehearsal/e2e`

7. Use the lower-level Dify handoff smoke matrix only for diagnosis:
   `uv run python scripts/run_dify_smoke_matrix.py --base-url http://127.0.0.1:8000 --state ${STATE_PATH} --out-dir var/evidence/${SERVICE_ID}/dify`

   The matrix verifies decision branches and auth/config error branches before the Dify UI handoff.

8. Export operations evidence directly only when you need a standalone diagnostics bundle:
   `uv run python scripts/export_ops_evidence.py --base-url http://127.0.0.1:8000 --admin-token ${ADMIN_BOOTSTRAP_TOKEN} --service-id ${SERVICE_ID} --out-dir var/evidence/${SERVICE_ID}/ops --window-hours 24 --actor-id ops-evidence --environment ${INTENT_ROUTING_ENVIRONMENT}`

   The evidence command writes `ops-evidence.json` and `ops-evidence.md`.

## Documents

- Local runbook: `docs/ops/intent-routing-local-runbook.md`
- CI verification: `docs/ops/ci-verification.md`
- Pilot runbook: `docs/ops/intent-routing-pilot-runbook.md`
- Closed-network deployment: `docs/ops/closed-network-deployment.md`
- Pilot e2e smoke: `docs/ops/pilot-e2e-smoke.md`
- Pilot readiness evidence: `docs/ops/pilot-readiness-evidence.md`
- Security lifecycle and operations evidence: `docs/ops/security-lifecycle.md`
- Security operations: `docs/ops/security-operations.md`
- Dify guide: `docs/integrations/dify-http-request-node.md`
