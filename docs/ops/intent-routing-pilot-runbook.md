# Intent Routing Pilot Runbook

Use `docs/ops/pilot-rehearsal.md` as the top-level Sprint 5 execution path before
Dify handoff. The lower-level commands in this runbook remain diagnostic paths
when the rehearsal manifest points to a specific failed step.

## 1. Start Local Stack

Export the local runtime contract first:

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

Use a new `SERVICE_ID` for each pilot run on a persistent local database. The admin API intentionally rejects duplicate services.

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

## 2. Run Sprint 5 Pilot Rehearsal

Run the top-level rehearsal before Dify handoff:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

Acceptance: `pilot-rehearsal-manifest.md` shows PASS, the CSV baseline
comparison passes, the Dify smoke matrix passes, operations evidence is present,
and the rehearsal secret scan has no findings.

## 3. Run Sprint 4 E2E Smoke Diagnostic

Run this process-level smoke only when diagnosing a failed rehearsal e2e step:

```bash
uv run python scripts/run_pilot_e2e_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --out-dir var/evidence/${SERVICE_ID}/e2e
```

Acceptance: `/healthz` is ok, `/readyz` is ready, the required `balanced` gate passes, risk pass rate is 100%, Dify-style smoke decisions pass, and masked logs do not expose raw query text.

## 4. Manual Seed Pilot

Use the remaining commands only for manual diagnostics or when isolating a failed e2e smoke step.

```bash
uv run python scripts/seed_pilot.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH}
```

## 5. Compare Thresholds

```bash
uv run python scripts/run_csv_gate.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH} \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --out-dir var/reports
```

Acceptance: `balanced` passes the 70% gate and risk pass rate is 100%.

## 6. Run Dify-Style Smoke

```bash
uv run python scripts/smoke_runtime_dify.py \
  --base-url http://127.0.0.1:8000 \
  --state ${STATE_PATH} \
  --query "API timeout 500 에러가 납니다" \
  --expect-decision confident
```

## 7. Trace/Audit Drill

Pass `--admin-token local-admin-token` in each drill command unless you export `ADMIN_BOOTSTRAP_TOKEN` first.

List masked logs:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH}
```

Fetch one masked log:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH} \
  --trace-id <trace_id>
```

Record raw-query access audit without printing raw text:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH} \
  --trace-id <trace_id> \
  --approval-id SEC-20260628-001 \
  --view-reason "장애 분석 ticket INC-20260626-001"
```

For API key rotation, admin token handling, KEK handling, and raw query approval policy, use `docs/ops/security-operations.md`.

## 8. Failure Drills

Run these manually before Dify handoff:

| Drill | Expected |
| --- | --- |
| Wrong API key | HTTP 401 error envelope with `AUTHENTICATION_FAILED` |
| Wrong `X-Service-Id` | HTTP 403 error envelope with `SERVICE_SCOPE_DENIED` |
| No active release | HTTP 404 error envelope with `ACTIVE_RELEASE_NOT_FOUND` |
| Off-topic query | HTTP 200 with `decision=off_topic` |
| Risk query | HTTP 200 with `decision=risk` |
| Ambiguous query | HTTP 200 with `decision=clarify` or documented fallback |

## Release Readiness Checklist

- [ ] `.env.example` uses `RAW_TEXT_KEK_ID` and `RAW_TEXT_KEK_BASE64`.
- [ ] `docker compose up -d postgres` succeeds.
- [ ] `uv run alembic upgrade head` succeeds.
- [ ] `uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000` starts the API.
- [ ] `run_pilot_e2e_smoke.py` writes the e2e index, readiness reports, and threshold reports with required `balanced` gate PASS.
- [ ] `seed_pilot.py` creates service, API key, policy version, catalog version, test run, release, and active release.
- [ ] `run_csv_gate.py` writes JSON and Markdown reports for `strict`, `balanced`, and `exploratory`.
- [ ] Balanced CSV gate pass rate is at least 70%.
- [ ] Risk pass rate is 100%.
- [ ] `smoke_runtime_dify.py` returns `decision=confident` for the pilot API timeout query.
- [ ] Masked runtime log list does not expose raw query fields.
- [ ] Raw query decrypt requires auditor or system admin role and writes `raw_query.viewed` audit log.
- [ ] Dify HTTP Request node is configured with `Authorization`, `X-Key-Id`, `X-App-Id`, `X-Service-Id`, and `X-Request-Id`.

## Closed-Network Deployment

For the Compose-based closed-network pilot path, use `docs/ops/closed-network-deployment.md`.
For the Sprint 4 default smoke, use `docs/ops/pilot-e2e-smoke.md`.
For lower-level readiness evidence generation, use `docs/ops/pilot-readiness-evidence.md`.
