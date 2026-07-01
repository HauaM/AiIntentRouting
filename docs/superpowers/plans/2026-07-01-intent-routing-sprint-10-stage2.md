# Intent Routing Sprint 10 Stage 2 Operation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the Sprint 10 Stage 2 limited-user pilot with a 50-request cap, BGE-M3 active, local-only evidence, and rollback controls.

**Architecture:** Stage 2 is an operations execution task, not a runtime feature task. The operator uses the existing runtime, active release, HTTP caller contract, BGE-M3 model path, ops evidence exporter, and branch protection checks. Runtime evidence stays under ignored `var/` paths; official docs receive only aggregate values, paths, hashes, decisions, and approvals.

**Tech Stack:** Markdown operations docs, existing FastAPI runtime and admin APIs, HTTP requests to `/v1/intent-route`, BGE-M3 local model package, existing ops evidence exporter, GitHub branch protection, repository secret scan helper, pytest.

---

## Scope

In scope:

- Stage 2 preflight.
- Stage 2A observation segment with 15 total Stage 2 requests.
- Stage 2B completion segment with up to 35 additional requests.
- Aggregate ops evidence capture after preflight, Stage 2A, and Stage 2B.
- Secret-safe update to `docs/ops/pilot-sprint-10-operation-summary.md`.

Out of scope:

- Broad production launch.
- Admin UI implementation.
- Runtime feature code changes.
- Catalog, policy, baseline, or release mutation outside an approved incident or rollback.
- Committing runtime evidence, `var/evidence`, `var/pilot`, Dify screenshots, Dify exports, runtime logs, local state, API keys, or secrets.

## Stage 2 Basis

- Stage 1 summary recommendation: continue limited pilot to Stage 2 planning.
- Stage 1 request count: 10.
- Stage 1 runtime error count: 0.
- Stage 1 runtime p95: 252 ms.
- Stage 1 combined fallback, clarify, and off-topic rate: 20 percent.
- Stage 1 active model: `emb-bge-m3-local`.
- BGE path: `/home/haua/workspace/models/embedded/bge-m3`.
- BGE package SHA-256: `7a680f2c38c16cfee81e29cfc04320271c95496c9b4ec119a6672672535019d3`.
- Dify extra integration test: not required for Stage 2 because Dify is an HTTP caller for `/v1/intent-route`.

## File Boundaries

Read:

- `docs/ops/pilot-sprint-10-operation-summary.md`
- `docs/ops/pilot-sprint-10-stage2-operation-plan.md`
- `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`

Create local-only evidence:

- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2b/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/rollback/`

Modify after operation:

- `docs/ops/pilot-sprint-10-operation-summary.md`

Never commit:

- `var/evidence`
- `var/pilot`
- Dify screenshots or exports
- Runtime logs
- Local state contents
- Raw request or response payload dumps
- Credential material

## Operator Window

Primary window:

- 2026-07-01 13:30-17:30 Asia/Seoul.
- Use only if this plan is merged and preflight is complete by
  2026-07-01 13:00 Asia/Seoul.

Fallback window:

- 2026-07-02 10:30-14:30 Asia/Seoul.
- Use if the primary window is missed or any preflight check is not clean.

## Task 1: Confirm Stage 2 Planning State

**Files:**

- Read: `docs/ops/pilot-sprint-10-operation-summary.md`
- Read: `docs/ops/pilot-sprint-10-stage2-operation-plan.md`

- [ ] **Step 1: Confirm repository state**

Run:

```bash
git status --short --branch
git rev-parse HEAD
git log --oneline -5
```

Expected:

```text
The working tree has no unrelated staged changes.
HEAD includes the Stage 2 planning PR merge.
The operation-start HEAD can be recorded before Stage 2 traffic starts.
```

- [ ] **Step 2: Confirm Stage 1 basis**

Run:

```bash
rg -n 'Stage 1|Runtime request count: 10|Runtime error count: 0|Latency p95: 252 ms|emb-bge-m3-local|continue limited pilot to Stage 2 planning' docs/ops/pilot-sprint-10-operation-summary.md
```

Expected:

```text
The Stage 1 summary confirms the accepted Stage 2 basis.
```

## Task 2: Run Stage 2 Preflight

**Files:**

- Read: `docs/ops/pilot-sprint-10-stage2-operation-plan.md`
- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/`

- [ ] **Step 1: Confirm BGE package path and SHA**

Run:

```bash
uv run python scripts/verify_bge_m3_package.py \
  --model-path /home/haua/workspace/models/embedded/bge-m3 \
  --out-dir var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/bge-package \
  --expected-sha256 7a680f2c38c16cfee81e29cfc04320271c95496c9b4ec119a6672672535019d3
```

Expected:

```text
The command prints local JSON and Markdown evidence paths.
The expected SHA-256 matches.
The evidence remains under var/evidence.
```

- [ ] **Step 2: Confirm runtime readiness**

Set the base URL for the operator-managed runtime:

```bash
export STAGE2_BASE_URL=http://127.0.0.1:8002
curl -sS "${STAGE2_BASE_URL}/readyz"
```

Expected:

```json
{"status":"ready","checks":{"database":"ok","alembic":"ok","pgvector":"ok"}}
```

- [ ] **Step 3: Capture preflight ops evidence**

Run with the intended operator database URL:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id it-helpdesk-pilot-sprint10-operation-monitoring \
  --out-dir var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/ops \
  --window-hours 1 \
  --actor-id sprint10-stage2-preflight \
  --environment dev
```

Expected:

```text
The command prints ops-evidence.json and ops-evidence.md paths.
Active release model version is emb-bge-m3-local.
Request count before Stage 2 traffic is recorded.
```

- [ ] **Step 4: Confirm branch protection**

Run:

```bash
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  --jq '{required_status_checks, enforce_admins: .enforce_admins.enabled}'
```

Expected:

```text
required_status_checks includes verify.
enforce_admins is true.
```

## Task 3: Execute Stage 2A Observation Segment

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/`

- [ ] **Step 1: Open Stage 2A only inside the approved window**

Expected:

```text
The current time is inside the selected Stage 2 window.
The operator has confirmed the 15-request Stage 2A cap.
The audience is limited internal pilot users only.
```

- [ ] **Step 2: Send or observe at most 15 Stage 2 requests**

Expected:

```text
No more than 15 Stage 2 requests are sent or observed before the checkpoint.
Request identifiers are preserved.
The HTTP caller path targets /v1/intent-route.
```

- [ ] **Step 3: Capture Stage 2A ops evidence**

Run:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id it-helpdesk-pilot-sprint10-operation-monitoring \
  --out-dir var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/ops \
  --window-hours 1 \
  --actor-id sprint10-stage2a-checkpoint \
  --environment dev
```

Expected:

```text
The command prints Stage 2A ops evidence paths.
The Stage 2A checkpoint can be evaluated from aggregate metrics.
```

- [ ] **Step 4: Evaluate Stage 2A checkpoint**

Expected:

```text
Total Stage 2A count is no more than 15.
Runtime error count is 0.
Latency p95 is below 2000 ms.
Combined fallback, clarify, and off-topic rate is at or below 30 percent, or explicitly explained.
Risk count is 0, or every risk result has operator review.
Top route keys remain in approved IT helpdesk scope.
Active model remains emb-bge-m3-local.
No runtime evidence is staged.
```

## Task 4: Execute Stage 2B Completion Segment

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2b/`

- [ ] **Step 1: Continue only after Stage 2A is accepted**

Expected:

```text
Stage 2A checkpoint is accepted.
No stop criterion is open.
The remaining cap is at most 35 requests.
```

- [ ] **Step 2: Send or observe at most 35 additional Stage 2 requests**

Expected:

```text
Stage 2 total count remains at or below 50.
Limited internal user scope is preserved.
No external or broad production users are added.
```

- [ ] **Step 3: Capture Stage 2B final ops evidence**

Run:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id it-helpdesk-pilot-sprint10-operation-monitoring \
  --out-dir var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2b/ops \
  --window-hours 4 \
  --actor-id sprint10-stage2b-final \
  --environment dev
```

Expected:

```text
The command prints final Stage 2 ops evidence paths.
Aggregate metrics cover the Stage 2 window.
```

- [ ] **Step 4: Evaluate Stage 2 final criteria**

Expected:

```text
Stage 2 total request count is no more than 50.
Error rate is below 2 percent.
Latency p95 is below 2000 ms.
No repeated timeout or server error branch occurs.
Combined fallback, clarify, and off-topic rate is at or below 30 percent, or documented as expected pilot traffic.
No risk result advances without operator review.
Route keys stay inside IT helpdesk pilot scope.
BGE-M3 path and active model remain normal.
Branch protection remains unchanged.
No runtime evidence is staged.
```

## Task 5: Apply Rollback If Required

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/rollback/`
- Modify only if rollback occurs: `docs/ops/pilot-sprint-10-operation-summary.md`

- [ ] **Step 1: Pause traffic on any stop criterion**

Expected:

```text
The HTTP caller path is paused.
Limited pilot users are routed to fallback or human handoff.
Immediate local rollback evidence is captured.
```

- [ ] **Step 2: Restore known-good runtime state when needed**

Expected:

```text
The prior approved image or prior known-good release is restored when the incident points to runtime or release state.
Readiness is confirmed after rollback.
Branch protection is unchanged.
```

## Task 6: Produce Secret-Safe Stage 2 Summary

**Files:**

- Modify: `docs/ops/pilot-sprint-10-operation-summary.md`
- Read local-only evidence under ignored `var/evidence`

- [ ] **Step 1: Update official summary with aggregate values only**

Expected:

```text
The summary records Stage 2 cap, actual aggregate count, decision counts, error count, latency p50/p95/max, BGE status, Dify HTTP caller boundary, rollback status, evidence paths, hashes, Admin UI exclusion, runtime evidence commit boundary, and one recommendation value.
```

- [ ] **Step 2: Select one final recommendation**

Expected recommendation values:

```text
continue limited pilot to Stage 3 planning
hold
rollback complete
no-go for broader traffic
```

## Task 7: Verify Stage 2 Artifacts

**Files:**

- Verify: `docs/ops/pilot-sprint-10-operation-summary.md`
- Verify local-only evidence boundaries.

- [ ] **Step 1: Secret scan the official summary**

Run:

```bash
uv run python - docs/ops/pilot-sprint-10-operation-summary.md <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory
with TemporaryDirectory() as tmpdir:
    result = scan_evidence_directory(Path(tmpdir), extra_paths=[Path(path) for path in sys.argv[1:]])
expected = SecretScanResult(passed=True, findings=[])
if result != expected:
    raise SystemExit(result)
print('secret-safe Sprint 10 Stage 2 official summary verified')
PY
```

Expected:

```text
secret-safe Sprint 10 Stage 2 official summary verified
```

- [ ] **Step 2: Whitespace check official summary**

Run:

```bash
uv run python - docs/ops/pilot-sprint-10-operation-summary.md <<'PY'
from pathlib import Path
import sys

failed = False
for path_arg in sys.argv[1:]:
    path = Path(path_arg)
    text = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip(" \t") != line:
            print(f"{path}:{line_number}: trailing whitespace")
            failed = True
    if text and not text.endswith("\n"):
        print(f"{path}: missing final newline")
        failed = True
if failed:
    raise SystemExit(1)
print("whitespace-safe Sprint 10 Stage 2 official summary verified")
PY
```

Expected:

```text
whitespace-safe Sprint 10 Stage 2 official summary verified
```

- [ ] **Step 3: Confirm runtime evidence is not tracked**

Run:

```bash
git ls-files var/evidence var/pilot
```

Expected:

```text
No output.
```

- [ ] **Step 4: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected:

```text
All tests pass with no failures.
```

## Completion Criteria

- Stage 2 uses at most 50 limited internal pilot requests.
- Stage 2A pauses after at most 15 requests for aggregate review.
- Stage 2B starts only after Stage 2A is accepted.
- Dify remains treated as an HTTP caller and does not require an extra integration test.
- BGE-M3 remains active with model version `emb-bge-m3-local`.
- Runtime evidence remains local and ignored.
- Official summary contains aggregate values, paths, hashes, approvals, and decisions only.
- Admin UI implementation remains excluded.

## Self-Review

- Stage 2 window and cap: covered in Operator Window and Tasks 2 through 4.
- Evidence capture and commit boundary: covered in File Boundaries, Tasks 2 through 7, and Completion Criteria.
- Dify caller boundary: covered in Stage 2 Basis and Completion Criteria.
- BGE path and SHA: covered in Stage 2 Basis and Task 2.
- Stop and rollback criteria: covered in Tasks 3 through 5.
- Official summary boundary: covered in Task 6 and Task 7.
- Admin UI exclusion: covered in Scope and Completion Criteria.
