# Intent Routing Pilot Runbook

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

## 2. Seed Pilot

```bash
uv run python scripts/seed_pilot.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH}
```

## 3. Compare Thresholds

```bash
uv run python scripts/run_csv_gate.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH} \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --out-dir var/reports
```

Acceptance: `balanced` passes the 70% gate and risk pass rate is 100%.

## 4. Run Dify-Style Smoke

```bash
uv run python scripts/smoke_runtime_dify.py \
  --base-url http://127.0.0.1:8000 \
  --state ${STATE_PATH} \
  --query "API timeout 500 에러가 납니다" \
  --expect-decision confident
```

## 5. Trace/Audit Drill

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
  --view-reason "장애 분석 ticket INC-20260626-001"
```

## 6. Failure Drills

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
