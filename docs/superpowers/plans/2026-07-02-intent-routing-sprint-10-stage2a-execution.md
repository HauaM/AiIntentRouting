# Intent Routing Sprint 10 Stage 2A Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the next Sprint 10 operation step: run or hold Stage 2A from the July 2 fallback window, capture aggregate-only evidence, and decide whether Stage 2B may start.

**Architecture:** This is an operations execution plan, not a runtime feature plan. It reuses the existing FastAPI runtime, active release, Dify HTTP caller boundary, BGE-M3 local model path, ops evidence exporter, branch protection checks, and secret-safe summary document. Runtime evidence stays under ignored `var/` paths; the only committed output after execution is the aggregate-only Sprint 10 operation summary.

**Tech Stack:** Markdown operations docs, existing FastAPI runtime and admin APIs, HTTP requests to `/v1/intent-route`, BGE-M3 local model package, `scripts/export_ops_evidence.py`, GitHub branch protection capture through `gh`, repository secret scan helper, pytest.

---

## Source Context

Read these documents before executing any step:

- `docs/ops/pilot-sprint-10-operation-summary.md`
- `docs/ops/pilot-sprint-10-stage2-operation-plan.md`
- `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`
- `docs/superpowers/plans/2026-07-01-intent-routing-sprint-10-stage2.md`

Current documented state:

- Sprint 9 launch decision is `Go`.
- Sprint 10 Stage 1 completed 10 of 10 operator requests.
- Stage 1 runtime error count was 0.
- Stage 1 runtime p95 was 252 ms.
- Stage 1 combined fallback, clarify, and off-topic rate was 20 percent.
- Stage 1 active model was `emb-bge-m3-local`.
- Stage 2 preflight completed.
- Stage 2 limited-user traffic is still 0 of 50.
- The next planned action is Stage 2A observation, capped at 15 requests.
- The Stage 2 fallback window is 2026-07-02 10:30-14:30 Asia/Seoul.

## File Boundaries

Read:

- `docs/ops/pilot-sprint-10-operation-summary.md`
- `docs/ops/pilot-sprint-10-stage2-operation-plan.md`
- `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`

Create local-only evidence:

- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2b/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/rollback/`

Modify only after operation or a hold decision:

- `docs/ops/pilot-sprint-10-operation-summary.md`

Do not stage or commit:

- `var/evidence`
- `var/pilot`
- Dify screenshots or exports
- Runtime logs
- Local state contents
- Raw request payloads
- Raw response payloads
- API keys, bearer tokens, KEK material, secret state files, or any credential material
- Unrelated Admin UI Phase 0 files already present in the working tree

## Execution Variables

Use shell variables so secrets are not written into commands or docs:

```bash
export SERVICE_ID=it-helpdesk-pilot-sprint10-operation-monitoring
export STAGE2_BASE_URL=http://127.0.0.1:8002
export STAGE2_ENVIRONMENT=dev
export STAGE2_MODEL_PATH=/home/haua/workspace/models/embedded/bge-m3
export STAGE2_MODEL_SHA=7a680f2c38c16cfee81e29cfc04320271c95496c9b4ec119a6672672535019d3
export STAGE2_EVIDENCE_ROOT=var/evidence/${SERVICE_ID}/stage2
```

`ADMIN_BOOTSTRAP_TOKEN` and `DATABASE_URL` must already be present in the operator shell. Do not print their values.

## Task 1: Confirm The Go Or Hold Branch

**Files:**

- Read: `docs/ops/pilot-sprint-10-operation-summary.md`
- Read: `docs/ops/pilot-sprint-10-stage2-operation-plan.md`
- Modify only if outside the approved window: `docs/ops/pilot-sprint-10-operation-summary.md`

- [ ] **Step 1: Confirm local time and branch**

Run:

```bash
date '+%Y-%m-%d %H:%M:%S %Z %z'
git status --short --branch
git rev-parse HEAD
```

Expected:

```text
The current time is recorded in Asia/Seoul.
If the time is between 2026-07-02 10:30 and 2026-07-02 14:30 KST, continue to Task 2.
If the time is after 2026-07-02 14:30 KST, do not send Stage 2A traffic; go to Task 6 and record recommendation value hold.
No unrelated files are staged.
```

- [ ] **Step 2: Confirm Stage 2A is still the next operation**

Run:

```bash
rg -n 'Stage 2 limited user traffic|held for fallback window|Stage 2 preflight active release model version|Stage 2 preflight readiness' docs/ops/pilot-sprint-10-operation-summary.md
rg -n 'Stage 2A observation|pause at 15|Stage 2B completion|continue only if Stage 2A' docs/ops/pilot-sprint-10-stage2-operation-plan.md
```

Expected:

```text
The operation summary says Stage 2 limited-user traffic is still held or not started.
The Stage 2 operation plan says Stage 2A pauses at 15 requests.
The Stage 2 operation plan says Stage 2B starts only after Stage 2A acceptance.
```

## Task 2: Run Final Readiness Before Stage 2A Traffic

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/pre-traffic/`

Fail closed: if `/readyz` is not reachable at `http://127.0.0.1:8002`, if
`ADMIN_BOOTSTRAP_TOKEN` is missing, or if `DATABASE_URL` is missing, do not open
Stage 2A traffic. Go directly to Task 6 and record recommendation value `hold`.

- [ ] **Step 1: Verify BGE-M3 package**

Run:

```bash
uv run python scripts/verify_bge_m3_package.py \
  --model-path "${STAGE2_MODEL_PATH}" \
  --out-dir "${STAGE2_EVIDENCE_ROOT}/stage2a/pre-traffic/bge-package" \
  --expected-sha256 "${STAGE2_MODEL_SHA}"
```

Expected:

```text
The command prints local JSON and Markdown evidence paths.
The expected SHA-256 matches.
The evidence path is under var/evidence.
```

- [ ] **Step 2: Confirm runtime readiness**

Run:

```bash
curl -sS "${STAGE2_BASE_URL}/readyz"
```

Expected:

```json
{"status":"ready","checks":{"database":"ok","alembic":"ok","pgvector":"ok"}}
```

- [ ] **Step 3: Capture pre-traffic ops evidence**

Run:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --out-dir "${STAGE2_EVIDENCE_ROOT}/stage2a/pre-traffic/ops" \
  --window-hours 1 \
  --actor-id sprint10-stage2a-pre-traffic \
  --environment "${STAGE2_ENVIRONMENT}"
```

Expected:

```text
The command prints ops-evidence.json and ops-evidence.md paths.
The active release model version is emb-bge-m3-local.
The pre-traffic request count is recorded.
No raw query text or credential material is exported.
```

- [ ] **Step 4: Confirm branch protection remains unchanged**

Run:

```bash
mkdir -p "${STAGE2_EVIDENCE_ROOT}/stage2a/pre-traffic/branch-protection"
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  > "${STAGE2_EVIDENCE_ROOT}/stage2a/pre-traffic/branch-protection/main-protection.json"
uv run python - "${STAGE2_EVIDENCE_ROOT}/stage2a/pre-traffic/branch-protection/main-protection.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
checks = payload.get("required_status_checks") or {}
contexts = set(checks.get("contexts") or [])
checks_payload = checks.get("checks") or []
apps = {item.get("context") for item in checks_payload if isinstance(item, dict)}
required = contexts | apps
if "verify" not in required and "CI / verify" not in required:
    raise SystemExit(f"missing verify required check: {sorted(required)}")
if not checks.get("strict"):
    raise SystemExit("required status checks strict mode is false")
if not (payload.get("enforce_admins") or {}).get("enabled"):
    raise SystemExit("enforce_admins is false")
print("branch protection capture verified")
PY
```

Expected:

```text
branch protection capture verified
```

## Task 3: Execute Stage 2A Observation

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/`

- [ ] **Step 1: Open Stage 2A with a 15-request cap**

Expected:

```text
The operator records that the current time is inside the approved fallback window.
The audience is limited internal pilot users only.
The cap is exactly 15 Stage 2A requests.
External or broad production users are not added.
Dify remains a pass-through HTTP caller for /v1/intent-route.
```

- [ ] **Step 2: Send or observe no more than 15 Stage 2A requests**

Expected:

```text
At most 15 Stage 2A requests are sent or observed.
Request identifiers are preserved.
Required headers are preserved.
No request payload, response payload, screenshot, workflow export, or runtime log is committed.
Traffic pauses immediately at 15 requests or earlier if a stop criterion appears.
```

- [ ] **Step 3: Capture Stage 2A checkpoint evidence**

Run:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --out-dir "${STAGE2_EVIDENCE_ROOT}/stage2a/checkpoint/ops" \
  --window-hours 1 \
  --actor-id sprint10-stage2a-checkpoint \
  --environment "${STAGE2_ENVIRONMENT}"
```

Expected:

```text
The command prints Stage 2A checkpoint ops evidence paths.
Aggregate request count, decision counts, error counts, latency values, and top route keys are available in ops-evidence.json and ops-evidence.md.
```

- [ ] **Step 4: Extract aggregate checkpoint values without raw payloads**

Run:

```bash
uv run python - "${STAGE2_EVIDENCE_ROOT}/stage2a/checkpoint/ops/ops-evidence.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
metrics = payload["runtime_metrics"]
release = payload["active_release"]
decision_counts = metrics.get("decision_counts") or {}
error_counts = metrics.get("error_counts") or {}
latency = metrics.get("latency_ms") or {}
request_count = int(metrics.get("request_count") or 0)
fallback_like = sum(int(decision_counts.get(name, 0) or 0) for name in ("fallback", "clarify", "off_topic"))
fallback_like_rate = 0 if request_count == 0 else round(fallback_like * 100 / request_count, 2)
print(f"request_count={request_count}")
print(f"error_total={sum(int(value or 0) for value in error_counts.values())}")
print(f"latency_p50_ms={latency.get('p50')}")
print(f"latency_p95_ms={latency.get('p95')}")
print(f"latency_max_ms={latency.get('max')}")
print(f"decision_counts={decision_counts}")
print(f"fallback_clarify_off_topic_rate_percent={fallback_like_rate}")
print(f"top_route_keys={metrics.get('top_route_keys') or []}")
print(f"active_model={release.get('model_version')}")
PY
```

Expected:

```text
Only aggregate values are printed.
No raw request text, raw response text, API key, bearer token, KEK material, or local state content is printed.
```

- [ ] **Step 5: Decide whether Stage 2B is allowed**

Expected acceptance:

```text
Stage 2A request count is no more than 15.
Runtime error count is 0.
Latency p95 is below 2000 ms.
Combined fallback, clarify, and off-topic rate is at or below 30 percent, or every excess case is explained as expected pilot traffic.
Risk count is 0, or every risk result has operator review before continuing.
Top route keys remain in approved IT helpdesk scope.
Active model remains emb-bge-m3-local.
Branch protection remains unchanged.
Runtime evidence remains under ignored var/ paths.
```

If every condition is met, continue to Task 4. If any condition fails, continue to Task 5.

## Task 4: Execute Stage 2B Only After Stage 2A Acceptance

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2b/`

- [ ] **Step 1: Continue with at most 35 additional requests**

Expected:

```text
Stage 2A checkpoint is accepted.
The remaining Stage 2 cap is at most 35 additional requests.
Stage 2 total count stays at or below 50.
Limited internal pilot user scope is preserved.
No external or broad production users are added.
```

- [ ] **Step 2: Capture Stage 2B final ops evidence**

Run:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --out-dir "${STAGE2_EVIDENCE_ROOT}/stage2b/final/ops" \
  --window-hours 4 \
  --actor-id sprint10-stage2b-final \
  --environment "${STAGE2_ENVIRONMENT}"
```

Expected:

```text
The command prints final Stage 2B ops evidence paths.
Aggregate metrics cover the Stage 2 operating window.
```

- [ ] **Step 3: Extract final aggregate values**

Run:

```bash
uv run python - "${STAGE2_EVIDENCE_ROOT}/stage2b/final/ops/ops-evidence.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
metrics = payload["runtime_metrics"]
release = payload["active_release"]
decision_counts = metrics.get("decision_counts") or {}
error_counts = metrics.get("error_counts") or {}
latency = metrics.get("latency_ms") or {}
request_count = int(metrics.get("request_count") or 0)
fallback_like = sum(int(decision_counts.get(name, 0) or 0) for name in ("fallback", "clarify", "off_topic"))
fallback_like_rate = 0 if request_count == 0 else round(fallback_like * 100 / request_count, 2)
print(f"request_count={request_count}")
print(f"error_total={sum(int(value or 0) for value in error_counts.values())}")
print(f"latency_p50_ms={latency.get('p50')}")
print(f"latency_p95_ms={latency.get('p95')}")
print(f"latency_max_ms={latency.get('max')}")
print(f"decision_counts={decision_counts}")
print(f"fallback_clarify_off_topic_rate_percent={fallback_like_rate}")
print(f"top_route_keys={metrics.get('top_route_keys') or []}")
print(f"active_model={release.get('model_version')}")
PY
```

Expected:

```text
Only aggregate values are printed.
No sensitive local artifact content is printed.
```

- [ ] **Step 4: Decide final Stage 2 recommendation**

Expected recommendation:

```text
Use continue limited pilot to Stage 3 planning only when Stage 2 total count is no more than 50, error rate is below 2 percent, p95 is below 2000 ms, no repeated timeout or server error branch occurred, route keys stayed in IT helpdesk scope, BGE-M3 remained active, branch protection remained unchanged, and no runtime evidence was staged.
Use hold when traffic did not run, evidence is incomplete, the window was missed, or a condition needs operator review.
Use rollback complete only after rollback was executed and readiness was restored.
Use no-go for broader traffic when a stop criterion indicates the pilot should not advance.
```

## Task 5: Stop Or Roll Back If A Criterion Fails

**Files:**

- Local-only evidence: `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/rollback/`
- Modify after decision: `docs/ops/pilot-sprint-10-operation-summary.md`

- [ ] **Step 1: Pause the HTTP caller path**

Expected:

```text
Stage 2 traffic is paused immediately.
Limited pilot users are routed to fallback or human handoff.
No additional pilot requests are sent until operator review is complete.
```

- [ ] **Step 2: Capture rollback or stop evidence**

Run:

```bash
DATABASE_URL="${DATABASE_URL}" uv run python scripts/export_ops_evidence.py \
  --base-url "${STAGE2_BASE_URL}" \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --out-dir "${STAGE2_EVIDENCE_ROOT}/rollback/ops" \
  --window-hours 1 \
  --actor-id sprint10-stage2-rollback-or-stop \
  --environment "${STAGE2_ENVIRONMENT}"
```

Expected:

```text
The command prints rollback or stop evidence paths.
Evidence remains under ignored var/evidence paths.
```

- [ ] **Step 3: Restore known-good state when runtime or release state is suspected**

Expected:

```text
Restore the prior approved application image when image state is suspected.
Activate the prior known-good release through the admin release rollback flow when release state is suspected.
Do not mutate catalog, policy, or test run records during rollback.
Confirm /readyz returns ready after rollback.
Confirm branch protection remains unchanged.
```

## Task 6: Update The Official Operation Summary

**Files:**

- Modify: `docs/ops/pilot-sprint-10-operation-summary.md`

- [ ] **Step 1: Add a Stage 2A or Stage 2 final section**

Update the summary using only aggregate values from `ops-evidence.json` and safe evidence hashes. The section must include:

```text
Stage 2A or Stage 2 status.
Operation window used.
Operation-start HEAD.
Request cap and actual aggregate request count.
Runtime error count.
Latency p50, p95, and max.
Decision counts.
Combined fallback, clarify, and off-topic rate.
Top route keys.
Active release version.
Active model version.
BGE model path and package SHA confirmation.
Dify HTTP caller boundary.
Branch protection status.
Rollback used: yes or no.
Runtime evidence committed: no.
Recommendation value.
```

- [ ] **Step 2: Choose exactly one recommendation value**

Allowed values:

```text
continue limited pilot to Stage 3 planning
hold
rollback complete
no-go for broader traffic
```

- [ ] **Step 3: Record local evidence hashes without committing evidence**

Run:

```bash
find "${STAGE2_EVIDENCE_ROOT}" -path '*ops-evidence.json' -o -path '*ops-evidence.md' -o -path '*bge-m3-package.json' -o -path '*main-protection.json' \
  | sort \
  | xargs -r sha256sum
```

Expected:

```text
Only safe local evidence paths and SHA-256 hashes are printed.
The official summary records hashes, not file contents.
```

## Task 7: Verify Secret Safety And Repo State

**Files:**

- Verify: `docs/ops/pilot-sprint-10-operation-summary.md`

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
print("secret-safe Sprint 10 Stage 2 operation summary verified")
PY
```

Expected:

```text
secret-safe Sprint 10 Stage 2 operation summary verified
```

- [ ] **Step 2: Whitespace check the official summary**

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
print("whitespace-safe Sprint 10 Stage 2 operation summary verified")
PY
```

Expected:

```text
whitespace-safe Sprint 10 Stage 2 operation summary verified
```

- [ ] **Step 3: Confirm local evidence remains untracked**

Run:

```bash
git ls-files var/evidence var/pilot
git status --short -- var/evidence var/pilot
git diff --name-only --cached
```

Expected:

```text
git ls-files var/evidence var/pilot prints no tracked evidence files.
git status --short -- var/evidence var/pilot prints no staged evidence files.
git diff --name-only --cached does not include var/evidence, var/pilot, Dify exports, screenshots, runtime logs, local state, or credential material.
```

- [ ] **Step 4: Run focused docs verification**

Run:

```bash
uv run pytest -q tests/unit/test_pilot_sprint9_closure_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
```

Expected:

```text
All selected docs contract tests pass.
```

## Completion Criteria

- If the fallback window is missed, no Stage 2A traffic is sent and the official summary records `hold`.
- If Stage 2A runs, at most 15 requests are sent or observed before the checkpoint.
- Stage 2B starts only after every Stage 2A checkpoint condition is accepted.
- If Stage 2B runs, Stage 2 total traffic remains at or below 50 requests.
- Dify remains a pass-through HTTP caller for `/v1/intent-route`.
- BGE-M3 remains active as `emb-bge-m3-local`.
- Branch protection remains unchanged.
- Runtime evidence remains local and ignored.
- Official docs contain only aggregate values, safe local paths, hashes, approvals, and decisions.
- Admin UI implementation remains outside this operation plan.

## Self-Review

- Stage 2A next action: covered by Tasks 1 through 3.
- Missed-window hold path: covered by Task 1 and Task 6.
- Stage 2B continuation gate: covered by Task 3 and Task 4.
- Stop and rollback path: covered by Task 5.
- Official summary boundary: covered by Task 6.
- Secret and evidence boundary: covered by File Boundaries and Task 7.
- Existing Stage 2 plan reuse: covered by Source Context and this plan's narrower scope.
