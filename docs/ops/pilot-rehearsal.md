# Pilot Rehearsal Operations Runbook

This runbook is the top-level Sprint 5 execution path for pilot readiness,
security operations rehearsal, and incident response rehearsal. Run
`scripts/run_pilot_rehearsal.py` before Dify handoff and attach its evidence
bundle to the pilot approval record.

Use `docs/ops/pilot-evidence-bundle-checklist.md` as the Sprint 6 review standard
before attaching a local evidence bundle. Use the older runbooks for
diagnostic commands when one rehearsal step fails.
Use `docs/ops/pilot-launch-readiness-checklist.md` as the Sprint 7 launch
closure checklist after the Sprint 6 bundle review; it records final evidence
ownership and the pilot go/no-go decision instead of replacing bundle review.
Use `docs/pilot/csv-baseline-refresh-policy.md` as the source of truth before
approving or rolling back any checked-in CSV baseline refresh.
Use `docs/ops/bge-m3-evidence-template.md` as the closed-network BGE-M3 evidence
record for package approval, preflight, benchmark, rehearsal, offline runtime,
and pilot go/no-go.
Use `docs/ops/pilot-handoff-release-ticket-template.md` for the final pilot
handoff and release ticket after the manifest, BGE evidence, branch protection,
Dify UI dry-run, CSV baseline comparison, and security rehearsal evidence are
ready.
The wrapper calls the readiness and evidence tools, writes a manifest, and runs
the evidence `secret scan`; no destructive security operation is executed by the wrapper.

## Purpose And Scope

The rehearsal proves that the pilot can be started, checked, handed to Dify, and
audited using repeatable evidence.

In scope:

- Local rehearsal with fake embeddings and CSV baseline comparison.
- Closed-network rehearsal with BGE-M3 package preflight and benchmark evidence.
- Manifest evidence using `pilot-rehearsal-manifest.json` and
  `pilot-rehearsal-manifest.md`.
- Security rehearsal procedures for approved manual drills around the wrapper.
- Incident rehearsal procedures for fallback and audit evidence.

Out of scope for the wrapper:

- KEK rewrap execute.
- Runtime raw-query retention execute.
- API key revoke.
- Raw query plaintext export.

## Local Rehearsal Command

Use local mode on a developer or operator host that runs fake embeddings. The
baseline argument makes the wrapper call `compare_csv_baseline.py` after
`run_pilot_e2e_smoke.py` produces the threshold comparison report.

```bash
export EMBEDDING_PROVIDER=fake
export INTENT_ROUTING_ENVIRONMENT=dev
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

Local acceptance:

- `run_pilot_e2e_smoke.py` passes the required `balanced` preset.
- `run_dify_smoke_matrix.py` passes the Dify request and error branches.
- `compare_csv_baseline.py` reports no blocking regression against the checked-in
  pilot baseline. Baseline refresh approval is governed by
  `docs/pilot/csv-baseline-refresh-policy.md`.
- `export_ops_evidence.py` writes operations evidence for the service.
- The rehearsal `secret scan` passes.

## Closed-Network Rehearsal Command

Use closed-network mode only after the runtime image is loaded, the real
secret-managed environment file is active, and `/models/bge-m3` is mounted
read-only. Closed-network mode requires BGE package preflight and benchmark
evidence; the wrapper calls `verify_bge_m3_package.py` before
`benchmark_bge_m3.py` and refuses to run without `--run-bge-benchmark`.

```bash
export INTENT_ROUTING_ENVIRONMENT=pilot
export EMBEDDING_PROVIDER=bge-m3
export BGE_M3_MODEL_PATH=/models/bge-m3
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

uv run python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 ${BGE_M3_MODEL_SHA256} \
  --run-bge-benchmark \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

Closed-network acceptance:

- BGE-M3 package checksum evidence matches the approved import record.
- The BGE-M3 benchmark report shows CPU-only execution with expected dimension,
  batch size, token limit, latency, and memory measurements.
- The remaining readiness, Dify matrix, baseline, ops evidence, and secret scan
  steps pass.

Record closed-network BGE evidence status as `measured-pass`, `measured-fail`,
or `pending-host-access` in `docs/ops/bge-m3-evidence-template.md`.
`pending-host-access` can close a local documentation sprint only when the
closed-network host is not yet available. It requires a pending-host-access
exception approval with an exception approval ID, exception owner, expiration
before pilot traffic, and next measurement date. pending-host-access may support
documentation closure, but it blocks closed-network pilot traffic. Pilot handoff
requires `measured-pass` for package preflight, benchmark, closed-network
rehearsal, and secret scan.
Conditional Go with pending-host-access must state that Dify or closed-network
traffic remains blocked until measured-pass evidence is attached.

Expected closed-network measured results:

- `bge-m3-package.json exists`
- `bge-m3-package.md exists`
- `bge-m3-benchmark.json exists`
- `bge-m3-benchmark.md exists`
- `pilot-rehearsal-manifest.json final_status is PASS`
- `secret_scan.passed is true`
- `dimension is 1024`
- `batch_size is 16`
- `max_tokens is 256`

If the closed-network host is unavailable, fill the template status as
`pending-host-access`, attach it to the release ticket, and keep pilot go/no-go
blocked. Conditional Go cannot send closed-network pilot traffic until
measured-pass is attached.

## Evidence Bundle Layout

The rehearsal evidence directory is safe to attach only after the secret scan
passes.

```text
var/evidence/${SERVICE_ID}/rehearsal/
  pilot-rehearsal-manifest.json
  pilot-rehearsal-manifest.md
  bge-package/
  bge-benchmark/
  e2e/
  dify/
  csv-baseline/
  ops/
```

Notes:

- `bge-package/` and `bge-benchmark/` are present only in closed-network mode.
- `csv-baseline/` is present when `--baseline` is provided.
- `e2e/` contains the Sprint 4 e2e index, threshold comparison, and masked
  runtime log checks.
- `dify/` contains the Dify smoke matrix report.
- `ops/` contains `ops-evidence.json` and `ops-evidence.md`.

The manifest is the first file to read during review. It records each step,
required status, evidence paths, failure messages, and the final pass/fail
status.

## Release Ticket Dry-Fill Review

After evidence review, copy `docs/ops/pilot-handoff-release-ticket-template.md`
to the release ticket path and fill it with references only. Do not create this
file until the pilot handoff package is being prepared.

Manual review commands for the filled ticket:

```bash
rg -n 'PASS|CI / verify|pilot-rehearsal-manifest.md|Dify workflow version identifier|go/no-go' var/evidence/${SERVICE_ID}/release-ticket.md
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/release-ticket.md
```

Expected:

```text
first rg prints the required evidence references
second rg prints no matches
```

## Secret Scan Policy

The wrapper recursively scans the evidence bundle before writing final success.
The secret scan fails closed if the evidence directory is missing, is not a
directory, or contains disallowed secret markers.

Evidence must not include:

- `.secret.json` state files.
- Raw API keys, bearer tokens, `Authorization` headers, or
  `intent_routing_api_key` values.
- `RAW_TEXT_KEK_BASE64` or `RAW_TEXT_LEGACY_KEKS_JSON` values.
- `query_raw`, `text_raw`, plaintext raw queries, encrypted DEKs, or ciphertext.
- Live key prefixes such as `irt_live_` or local secret markers such as
  `irt_secret`.

Evidence may include redacted marker names when the value is `REDACTED`. If the
scan fails, do not attach the bundle to a ticket. Remove the unsafe evidence at
the source, rerun the rehearsal, and attach only the clean bundle.

## Security Rehearsal Procedures

Security drills are approved manual steps around the rehearsal. They produce
evidence that is stored next to the rehearsal bundle, but the wrapper does not
execute them.

### API key rotation overlap

Rehearse API key rotation overlap with `scripts/rotate_api_key.py` without
`--revoke-old`. The expected evidence is a rotation report with old/new key IDs,
the new key fingerprint, a passing smoke trace, and `old_key_revoked=false`.
Keep the generated `.secret.json` outside the rehearsal evidence directory.

### raw query decrypt exception

A raw query decrypt exception requires an approval ID, an incident or audit
reason, and an `auditor` or `system_admin` role. Use
`scripts/trace_audit_drill.py` with `--approval-id` and `--view-reason`; the
output must confirm raw-query access metadata without printing plaintext. Verify
that `raw_query.viewed` appears in operations evidence.

### KEK rewrap dry-run

Run the KEK rewrap dry-run from `docs/ops/security-lifecycle.md` with
`scripts/rewrap_raw_text.py --dry-run`. The rehearsal evidence should show
`failed_count=0`, the expected source and target key IDs, and
`plaintext_exported=false`. Execute mode requires a separate approved change and
is not part of this Sprint 5 rehearsal.

### runtime raw-query retention dry-run

Run the runtime raw-query retention dry-run from
`docs/ops/security-lifecycle.md` with `scripts/apply_log_retention.py
--dry-run`. The evidence should show eligible, already redacted, and would-redact
counts without printing raw queries. Execute mode requires separate approval and
is not part of this Sprint 5 rehearsal.

## Incident Rehearsal Procedures

Use the Dify smoke matrix and the operator diagnostics to rehearse incident
fallback before Dify handoff.

Required incident drills:

- Wrong API key returns an authentication error envelope.
- Wrong service header returns a service-scope error envelope.
- Invalid request body returns a validation error envelope.
- Off-topic, risk, and ambiguous queries return documented fallback decisions.
- A simulated 5xx or timeout at the Dify boundary routes to the approved
  incident fallback message and operator escalation path.

For every incident drill, record the `trace_id`, `request_id`, `service_id`,
active `release_version`, Dify workflow version identifier, observed decision,
and operator action. If raw-query access is needed, follow the raw query decrypt
exception procedure instead of reading database fields directly.

## Failure Triage

| Failure | Likely cause | First diagnostic |
| --- | --- | --- |
| BGE checksum mismatch | Wrong model package, incomplete transfer, or stale approval checksum | Rerun `verify_bge_m3_package.py`, compare the generated SHA-256 with the import record, and reject the package until they match. |
| BGE benchmark memory or latency failure | Host sizing, batch size, or dependency issue | Rerun `benchmark_bge_m3.py` with a smaller `BGE_M3_BATCH_SIZE`, then attach before/after benchmark reports. |
| Balanced gate failure | Catalog, policy, threshold, or embedding regression | Inspect the `run_pilot_e2e_smoke.py` threshold comparison report and rerun lower-level CSV diagnostics. |
| Baseline regression | Current threshold report drifted from the approved pilot baseline | Inspect `compare_csv_baseline.py` Markdown and update the baseline only through `docs/pilot/csv-baseline-refresh-policy.md`. |
| Dify branch mismatch | HTTP Request node headers, request body mapping, or workflow branch rules differ from the handoff contract | Inspect `run_dify_smoke_matrix.py` output and the Dify workflow version identifier. |
| Ops evidence export failure | Admin token, role scope, service ID, or API availability issue | Run `export_ops_evidence.py` directly with the same service ID and actor headers. |
| Secret scan failure | Evidence bundle contains state files, tokens, KEKs, raw queries, encrypted DEKs, or ciphertext | Remove unsafe files from the evidence source, rerun the wrapper, and attach only the clean manifest. |
