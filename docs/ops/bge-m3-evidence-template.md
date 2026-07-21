# BGE-M3 Closed-Network Evidence Template

Use `docs/ops/bge-m3-evidence-template.md` to record the closed-network BGE-M3
package, benchmark, rehearsal, offline runtime, and pilot go/no-go evidence.
This procedure is documented here for operators to execute on the approved
closed-network host; do not commit `var/evidence`, `var/pilot`, model files,
benchmark output, or generated secret state files.

## Status

Allowed status values:

- `measured-pass`
- `measured-fail`
- `pending-host-access`

`pending-host-access can close a local documentation sprint only when the closed-network host is not yet available.`
`pending-host-access blocks pilot go/no-go.`
`pilot handoff requires measured-pass for package preflight, benchmark, closed-network rehearsal, and secret scan.`

`pending-host-access exception approval` is the only allowed documentation
closure path when the approved closed-network host is not available.
pending-host-access requires an exception approval ID, an owner, and a next
measurement date.
pending-host-access may support documentation closure, but it blocks
closed-network pilot traffic.
Conditional Go with pending-host-access must state that Dify or closed-network
traffic remains blocked until measured-pass evidence is attached.
The exception owner must confirm the exception expires before pilot traffic and
that the next measurement date is scheduled.

If the closed-network host is unavailable, fill this record with
`pending-host-access`, attach it to the release ticket, and mark pilot go/no-go
as blocked until measured closed-network evidence is available.

## Pending Host Access Exception

Use this section only when the approved closed-network host is not yet available.
It records the pending-host-access exception approval without authorizing Dify
or closed-network pilot traffic.

- Exception approval ID:
- Exception owner:
- Approved by:
- Approval timestamp:
- Expires before pilot traffic: yes
- Next measurement date:
- Decision impact: Conditional Go cannot send closed-network pilot traffic until
  measured-pass is attached.

The exception approval ID, exception owner, expiration before pilot traffic, and
next measurement date must be copied into the release ticket and pilot go/no-go
decision record.

## Package Approval Record

Record:

- Service ID:
- Release ticket:
- Approved model source:
- Import approver:
- Import date:
- `BGE_M3_MODEL_PATH`: `/models/bge-m3`
- `BGE_M3_MODEL_SHA256`:
- Approval status: `measured-pass` / `measured-fail` / `pending-host-access`

The approved model must be present at `/models/bge-m3` before any runtime,
preflight, benchmark, or rehearsal command runs. The package approval record
must confirm that the model was imported from an approved internal artifact
source and was not downloaded by the image build, startup path, benchmark, or
request handling path.

## Package Preflight Result

Run on the closed-network host after `/models/bge-m3` is mounted:

```bash
uv run python scripts/verify_bge_m3_package.py \
  --model-path /models/bge-m3 \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/bge-package \
  --expected-sha256 ${BGE_M3_MODEL_SHA256}
```

Expected results:

- `bge-m3-package.json exists`
- `bge-m3-package.md exists`
- `offline_required` is true.
- The computed SHA-256 matches `BGE_M3_MODEL_SHA256`.
- Package preflight status: `measured-pass` / `measured-fail` / `pending-host-access`

## Benchmark Result

Run only after package preflight passes:

```bash
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/models/bge-m3 \
BGE_M3_BATCH_SIZE=16 \
uv run python scripts/benchmark_bge_m3.py \
  --model-path /models/bge-m3 \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/bge-benchmark \
  --batch-size 16
```

Expected results:

- `bge-m3-benchmark.json exists`
- `bge-m3-benchmark.md exists`
- `dimension: 1024`
- `batch_size: 16`
- `max_tokens: 256`
- `latency_ms.p50` is recorded.
- `latency_ms.p95` is recorded.
- `max_rss_mb` is recorded.
- Benchmark status: `measured-pass` / `measured-fail` / `pending-host-access`

## Closed-Network Rehearsal Result

Run after the image, API, environment file, model mount, package preflight, and
benchmark are ready:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment prod \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 ${BGE_M3_MODEL_SHA256} \
  --run-bge-benchmark \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

Expected results:

- `pilot-rehearsal-manifest.json final_status is PASS`
- `secret_scan.passed is true`
- Closed-network rehearsal status: `measured-pass` / `measured-fail` / `pending-host-access`

## Offline Runtime Confirmation

Confirm:

- `/models/bge-m3` is mounted read-only into the API container.
- `EMBEDDING_PROVIDER=bge-m3`.
- `BGE_M3_MODEL_PATH=/models/bge-m3`.
- `BGE_M3_MODEL_SHA256` matches the approved package record.
- No package preflight, benchmark, rehearsal, startup, or runtime request path
  downloads model files.
- Package evidence records `offline_required`.

Offline runtime status: `measured-pass` / `measured-fail` / `pending-host-access`

## Failure Handling

Use `measured-fail` when the host is available but package preflight, benchmark,
closed-network rehearsal, offline runtime confirmation, or secret scan does not
meet the expected result.

Common failure responses:

- Missing model path: mount the approved `/models/bge-m3` directory and rerun.
- Checksum mismatch: reject the package and re-import the approved model.
- Wrong `dimension: 1024`, `batch_size: 16`, or `max_tokens: 256`: stop pilot
  approval and rerun with the documented BGE-M3 profile.
- Missing `latency_ms.p50`, `latency_ms.p95`, or `max_rss_mb`: rerun the
  benchmark and attach complete reports.
- `secret_scan.passed is true` is not satisfied: remove unsafe evidence at the
  source, rerun the rehearsal, and attach only clean evidence.
- Host unavailable: use `pending-host-access`, attach this record to the release
  ticket, record the exception approval ID, exception owner, expiration before
  pilot traffic, and next measurement date, and keep closed-network pilot
  traffic blocked.

## Pilot Go/No-Go

Pilot go requires:

- Package preflight status: `measured-pass`.
- Benchmark status: `measured-pass`.
- Closed-network rehearsal status: `measured-pass`.
- Secret scan status: `measured-pass`, with `secret_scan.passed is true`.

`pending-host-access` is not acceptable for actual pilot go/no-go. It only
documents that the local documentation sprint could close before host access was
available; pilot traffic remains blocked until measured closed-network evidence
passes.
Conditional Go cannot send closed-network pilot traffic until measured-pass is
attached.
