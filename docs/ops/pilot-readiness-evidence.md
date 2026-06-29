# Pilot Readiness Evidence

For Sprint 5 pilot handoff, prefer `scripts/run_pilot_rehearsal.py`; it wraps the Sprint 4 e2e smoke, Dify smoke matrix, CSV baseline comparison, ops evidence export, and rehearsal secret scan into one manifest. Use `docs/ops/pilot-evidence-bundle-checklist.md` as the Sprint 6 review standard before attaching local rehearsal evidence. Use this page as a diagnostic reference when a checklist step fails and you need to run the lower-level readiness workflow directly after the API is running and `/readyz` returns ready.

Default Sprint 5 rehearsal command:

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

Closed-network rehearsal command:

```bash
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

Lower-level Sprint 4 e2e diagnostic command:

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

Lower-level readiness command:

```bash
uv run python scripts/run_pilot_readiness.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --out-dir var/evidence/${SERVICE_ID}
```

CSV tier options:

- `minimum`: 30-row pilot gate dataset.
- `standard`: 50-row pilot dataset after Sprint 7 CSV expansion; before that file exists it uses the default pilot CSV alias.
- `high-confidence`: 100-row pilot dataset.
- `custom --csv <path>`: operator-supplied CSV using the standard CSV header.

Evidence outputs:

- `pilot-rehearsal-manifest.json` and `pilot-rehearsal-manifest.md` when using the Sprint 5 rehearsal wrapper
- `pilot-e2e-smoke-index.json` and `pilot-e2e-smoke-index.md` when using the e2e wrapper
- `readiness-report.json`
- `readiness-report.md`
- threshold comparison JSON and Markdown reports
- the generated `.secret.json` state file under `var/pilot`

Non-secret evidence reports must not include raw API keys, bearer headers, `RAW_TEXT_KEK_BASE64`, or raw decrypted query text.

## Operations Evidence

After readiness and any security lifecycle work, export the operations evidence package:

```bash
uv run python scripts/export_ops_evidence.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/ops \
  --window-hours 24 \
  --actor-id ops-evidence \
  --environment ${INTENT_ROUTING_ENVIRONMENT}
```

Outputs:

- `ops-evidence.json`
- `ops-evidence.md`

Use `docs/ops/security-lifecycle.md` for KEK rewrap, runtime raw-query retention, rollback, and secret leak checks.
Keep generated `.secret.json` state files outside shared evidence bundles.
