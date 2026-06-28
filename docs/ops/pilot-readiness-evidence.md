# Pilot Readiness Evidence

Use this workflow after the API is running and `/readyz` returns ready.

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

- `readiness-report.json`
- `readiness-report.md`
- threshold comparison JSON and Markdown reports
- the generated `.secret.json` state file under `var/pilot`

Non-secret evidence reports must not include raw API keys, bearer headers, `RAW_TEXT_KEK_BASE64`, or raw decrypted query text.
