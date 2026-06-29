# Pilot Evidence Bundle Checklist

Use this checklist as the Sprint 6 review standard for a local rehearsal
evidence bundle. The lower-level runbooks are diagnostic references when a step
fails; reviewers should approve only the final clean bundle described here.

## Local Evidence Generation

Run the local stack from one terminal:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON="{}"
export EMBEDDING_PROVIDER=fake
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

Run the rehearsal from a separate terminal that has the same environment:

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

Do not run lower-level commands first during Sprint 6 review. Use
`docs/ops/pilot-rehearsal.md`, `docs/ops/intent-routing-pilot-runbook.md`, and
`docs/ops/pilot-readiness-evidence.md` only as diagnostic references after this
wrapper identifies a failed step.

## Required Files

Attach the `var/evidence/${SERVICE_ID}/rehearsal` directory only after all
reviewer checks pass. Relative to that rehearsal bundle root, the required
generated paths are:

- `pilot-rehearsal-manifest.json`
- `pilot-rehearsal-manifest.md`
- `csv-baseline/csv-baseline-comparison.md`
- `dify/dify-smoke-matrix.md`
- `ops/ops-evidence.md`

JSON siblings such as `csv-baseline/csv-baseline-comparison.json`,
`dify/dify-smoke-matrix.json`, and `ops/ops-evidence.json` may also be present
and reviewed when useful.

Reviewers must inspect JSON field paths in `pilot-rehearsal-manifest.json`:

```text
final_status == "PASS"
secret_scan.passed == true
```

Ticket shorthand may keep these literal status strings:

```text
final_status: PASS
secret_scan.passed: true
```

## Reviewer Checks

Run these commands before attaching the bundle:

```bash
uv run python -m json.tool var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
sha256sum var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
find var/evidence/${SERVICE_ID}/rehearsal -name '*.secret.json' -print
rg -n 'Authorization: Bearer|Bearer |RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/rehearsal
```

Expected:

```text
manifest final_status is PASS
manifest secret_scan.passed is true
sha256sum prints one digest for pilot-rehearsal-manifest.json
find prints no .secret.json files
rg prints no matches
```

`rg` returns exit code 1 when it finds no matches. For this checklist, exit code
1 with no output is expected for the `rg` command; exit code 0 or any printed
match fails review.

## Secret Scan Confirmation

Confirm the wrapper's recursive secret scan passed and the reviewer scan prints
no findings. The attached evidence must have:

- no .secret.json files
- no Authorization: Bearer
- no Bearer token
- no RAW_TEXT_KEK_BASE64
- no RAW_TEXT_LEGACY_KEKS_JSON
- no api_key=
- no intent_routing_api_key
- no query_raw
- no text_raw
- no encrypted_dek
- no ciphertext
- no irt_live_
- no irt_secret

If any command prints a finding, stop the review and move to Failure Handling.

## Hash Record

Copy the manifest hash to the ticket:

```bash
sha256sum pilot-rehearsal-manifest.json
```

When running from the repository root, use the full path:

```bash
sha256sum var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
```

Record the single digest and filename printed by `sha256sum`.

## Failure Handling

If `final_status == "PASS"` is false, if `secret_scan.passed == true` is false,
or if reviewer commands find forbidden files or text, do not attach the bundle.

Use the lower-level runbooks only for diagnostics:

- `docs/ops/pilot-rehearsal.md` for wrapper step triage.
- `docs/ops/intent-routing-pilot-runbook.md` for local stack and smoke command
  diagnostics.
- `docs/ops/pilot-readiness-evidence.md` for readiness and operations evidence
  diagnostics.

Fix the source of the evidence, rerun `run_pilot_rehearsal.py`, and review the
new bundle from the beginning.

## Files That Must Not Be Attached

Do not attach or commit runtime-only files:

- `var/pilot/${SERVICE_ID}.state.secret.json`
- Any `.secret.json` file
- Any generated API key, bearer token, KEK value, encrypted DEK, ciphertext, or
  raw query text
- Any local-only logs or scratch outputs outside
  `var/evidence/${SERVICE_ID}/rehearsal`

Also do not commit var/evidence, `var/pilot`, `*.secret.json`, or runtime
evidence files.

## Ticket Fields To Copy

Copy these fields from the reviewed bundle into the pilot approval ticket:

- `SERVICE_ID`
- `STATE_PATH` location, noted as local-only and not attached
- `ADMIN_BOOTSTRAP_TOKEN` source, noted as local bootstrap only and not attached
- Manifest path: `var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json`
- Manifest hash from `sha256sum`
- Manifest status: `final_status == "PASS"` (`final_status: PASS`)
- Secret scan status: `secret_scan.passed == true`
  (`secret_scan.passed: true`)
- Evidence files attached: `pilot-rehearsal-manifest.md`,
  `csv-baseline/csv-baseline-comparison.md`,
  `dify/dify-smoke-matrix.md`, and `ops/ops-evidence.md`
