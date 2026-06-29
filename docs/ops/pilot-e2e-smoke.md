# Pilot End-to-End Smoke

Preferred path: run the Sprint 5 pilot rehearsal wrapper before Dify handoff. It calls this Sprint 4 e2e smoke, runs the Dify smoke matrix, CSV baseline comparison, and ops evidence export, performs the rehearsal secret scan, and writes `pilot-rehearsal-manifest.json` and `pilot-rehearsal-manifest.md`.

Use this Sprint 4 smoke directly only as a lower-level diagnostic. It seeds a unique pilot service, checks `/healthz` and `/readyz`, runs the CSV threshold comparison with the required `balanced` gate, executes Dify-style runtime smokes, checks masked logs, and writes an e2e evidence index.

## Preconditions

- The API is already running.
- Database migrations are complete.
- CI and local runs use `EMBEDDING_PROVIDER=fake`.
- Use BGE-M3 only after model validation and closed-network resource checks are complete.
- Use a unique `SERVICE_ID` for each persistent database run.

## Local Run

```bash
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

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

Diagnostic e2e-only command:

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

## Closed-Network Run

```bash
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

uv run python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment pilot \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 ${BGE_M3_MODEL_SHA256} \
  --run-bge-benchmark \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

Diagnostic e2e-only command:

```bash
uv run python scripts/run_pilot_e2e_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment pilot \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --out-dir var/evidence/${SERVICE_ID}/e2e
```

## Generated Files

Preferred rehearsal outputs:

- `pilot-rehearsal-manifest.json`
- `pilot-rehearsal-manifest.md`
- `e2e/pilot-e2e-smoke-index.json`
- `e2e/pilot-e2e-smoke-index.md`
- `dify/dify-smoke-matrix.json`
- `dify/dify-smoke-matrix.md`
- `csv-baseline/csv-baseline-comparison.json`
- `csv-baseline/csv-baseline-comparison.md`
- `ops/ops-evidence.json`
- `ops/ops-evidence.md`

Diagnostic e2e-only outputs:

- `pilot-e2e-smoke-index.json`
- `pilot-e2e-smoke-index.md`
- `readiness-report.json`
- `readiness-report.md`
- `${SERVICE_ID}-threshold-comparison.json`
- `${SERVICE_ID}-threshold-comparison.md`
- `${STATE_PATH}` secret state file, kept outside shared evidence bundles

## Acceptance

- Rehearsal manifest final status is PASS.
- Required rehearsal steps are PASS.
- Local-only BGE steps are SKIP in local mode.
- The `csv-baseline` step is PASS when `--baseline docs/pilot/it-helpdesk-pilot-baseline.json` is provided.
- Rehearsal secret scan has no findings.
- `/healthz` returns ok.
- `/readyz` returns ready.
- Required `balanced` quality gate is PASS.
- Risk pass rate is 100%.
- Dify smoke decisions match expected pilot decisions.
- Masked runtime logs do not expose raw query text.

## Failure Triage

| failure | likely cause | next action |
| --- | --- | --- |
| Migration failure | API DB schema is behind the code | Run `uv run alembic upgrade head`, restart the API, then rerun the smoke with a new `SERVICE_ID`. |
| Duplicate `service_id` | The persistent DB already has that pilot service | Export a new timestamped `SERVICE_ID` and matching `STATE_PATH`. |
| Auth failure | `ADMIN_BOOTSTRAP_TOKEN` is missing or mismatched | Confirm the API environment and CLI token use the same value. |
| Balanced gate failure | Pilot CSV results do not satisfy the required threshold | Inspect the threshold comparison Markdown and block reasons before Dify handoff. |
| Dify smoke mismatch | Runtime route decision changed from the expected pilot contract | Inspect the readiness report smoke section and active release configuration. |

## Secret Scan

```bash
grep -R -n -E 'Bearer[[:space:]]+|api_key|authorization|secret state|encrypted_dek|ciphertext|query_raw|query_masked' var/evidence/${SERVICE_ID}/rehearsal \
  | grep -v -E '"(api_key|authorization|state_path|query_raw|query_masked|[^"]*(encrypted_dek|ciphertext)[^"]*)"[[:space:]]*:[[:space:]]*"REDACTED"'
```

Expected result: no matches after filtering fields whose value is exactly `REDACTED`. Investigate any remaining match before sharing the evidence bundle. Do not share `.secret.json` state files, raw API keys, bearer tokens, encrypted DEKs, ciphertext, or raw query text in evidence bundles.
