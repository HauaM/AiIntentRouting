# Intent Routing Pilot Runbook

## 1. Start Local Stack

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

## 2. Seed Pilot

```bash
uv run python scripts/seed_pilot.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token local-admin-token \
  --service-id it-helpdesk-pilot \
  --environment dev \
  --state-path var/pilot/it-helpdesk-pilot.state.secret.json
```

## 3. Compare Thresholds

```bash
uv run python scripts/run_csv_gate.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token local-admin-token \
  --state var/pilot/it-helpdesk-pilot.state.secret.json \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --out-dir var/reports
```

Acceptance: `balanced` passes the 70% gate and risk pass rate is 100%.

## 4. Run Dify-Style Smoke

```bash
uv run python scripts/smoke_runtime_dify.py \
  --base-url http://127.0.0.1:8000 \
  --state var/pilot/it-helpdesk-pilot.state.secret.json \
  --query "API timeout 500 에러가 납니다" \
  --expect-decision confident
```

## 5. Trace/Audit Drill

Pass `--admin-token local-admin-token` in each drill command unless you export `ADMIN_BOOTSTRAP_TOKEN` first.

List masked logs:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token local-admin-token \
  --state var/pilot/it-helpdesk-pilot.state.secret.json
```

Fetch one masked log:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token local-admin-token \
  --state var/pilot/it-helpdesk-pilot.state.secret.json \
  --trace-id <trace_id>
```

Record raw-query access audit without printing raw text:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token local-admin-token \
  --state var/pilot/it-helpdesk-pilot.state.secret.json \
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
