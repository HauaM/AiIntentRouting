# Intent Routing Sprint 10 Pilot Operation And Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operate the Sprint 10 limited pilot after the Sprint 9 Go decision, prove monitoring and rollback controls, and produce only secret-safe official records.

**Architecture:** Sprint 10 is an operations and monitoring sprint, not a runtime feature sprint. Existing runtime APIs, the Dify pass-through HTTP caller, the closed-network BGE-M3 path, the ops evidence exporter, and branch protection remain the execution surface. Runtime evidence stays local under ignored paths; official docs record only aggregate outcomes, evidence references, hashes, approvals, and decisions. Admin UI implementation is excluded.

**Tech Stack:** Markdown operations docs, existing FastAPI runtime and admin APIs, existing Dify HTTP Request caller, closed-network BGE-M3 runtime, existing ops evidence exporter, Git and GitHub branch protection, repository secret scan helper.

---

## Scope

Sprint 10 official direction is **Pilot Operation & Monitoring**.

In scope:

- Run a limited pilot traffic ramp only after operator approval.
- Monitor latency, errors, fallback drift, route scope, Dify caller behavior, active release, and BGE path normalcy.
- Pause or roll back when stop criteria are met.
- Keep runtime evidence local and ignored by git.
- Produce a secret-safe official summary if pilot operation is executed.

Out of scope:

- Broad production launch.
- Admin UI implementation.
- Runtime feature changes.
- Catalog, policy, baseline, or release mutation outside an approved incident or rollback action.
- Committing runtime evidence, `var/evidence`, `var/pilot`, Dify screenshots or exports, runtime logs, local state, or secrets.

Task 1 boundary:

- This task creates or updates only this plan and the companion operations-control plan.
- The Task 1 implementer does not stage files, commit files, or create runtime evidence.
- After spec and quality approval, the controller may stage and commit these two secret-safe planning docs only.
- No live traffic task is authorized by a planning-doc commit.

## Sprint 9 Basis

The Sprint 10 plan is based on these accepted Sprint 9 records:

- Sprint 9 decision: Go.
- Sprint 9 blocked gates: None.
- Pilot traffic approved: yes.
- Dify HTTP caller accepted: yes, while it remains a pass-through caller for `/v1/intent-route`.
- BGE closed-network status: measured-pass.
- Branch protection: accepted with `CI / verify`.
- CSV baseline freeze: approved.
- Admin UI implementation: excluded.
- Runtime evidence commit boundary: runtime evidence was not committed.

Source documents:

- `docs/ops/pilot-sprint-9-execution-closure.md`
- `docs/ops/pilot-sprint-9-go-no-go-decision.md`
- `docs/ops/pilot-sprint-9-release-ticket.md`

## Repo State At Plan Creation

- Date/timezone: 2026-07-01, Asia/Seoul.
- Checked branch: `codex/sprint-10-pilot-ops`.
- Plan-creation base HEAD before the Sprint 10 planning docs commit: `d57a4507888c7b21642c0500093e8e06d16c4b57`.
- Sprint 9 closure merge: `075c54b5bf241686368a9ec715f727a606a65940`.
- Newer pre-plan base context: PR #14 Admin UI handbook docs merge is present in the plan-creation base and remains out of scope for Sprint 10 pilot operation.
- Later planning commits may move HEAD forward; do not require operation-start HEAD to equal the plan-creation base.
- Record the actual operation-start HEAD in the local operation index and later official summary before any live traffic.
- Working-tree boundary for Task 1: only the two Sprint 10 planning docs may be changed.

## File Boundaries

Task 1 write scope:

- `docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md`
- `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`

Future official summary boundary:

- `docs/ops/pilot-sprint-10-operation-summary.md` may be created only after operation evidence is reviewed and summarized.
- The summary must contain aggregate values and references only.
- The summary must state Admin UI implementation is excluded.
- The summary must state runtime evidence was not committed.

Never commit:

- Runtime evidence.
- `var/evidence`.
- `var/pilot`.
- Dify screenshots.
- Dify workflow exports.
- Runtime logs.
- Local state.
- Secrets or credential material.
- Raw request or response payload dumps.

## Traffic Ramp

Sprint 10 remains limited pilot traffic. It is not broad production traffic.
Stages 1, 2, and 3 are blocked until an operator-approved operating window and
stage cap exist. A planning-doc commit never authorizes live traffic by itself.

| stage | duration | cap | audience | promotion rule |
| --- | --- | --- | --- | --- |
| 0 | pre-window | 0 live requests | operator only | Sprint 9 basis and readiness are rechecked |
| 1 | 30 minutes | 10 requests | internal pilot operators | operator-approved window and cap exist, and no stop criteria triggered |
| 2 | 4 hours | 50 requests | limited internal pilot users | operator-approved window and cap exist, and stage 1 summary accepted |
| 3 | 1 business day | 100 requests | same limited pilot group | operator-approved window and cap exist, and stage 2 summary accepted |

Traffic rules:

- Treat Stage 1, Stage 2, and Stage 3 as blocked until the operator-approved window and cap are recorded.
- Do not exceed the current stage cap.
- Do not add external or broad production users during Sprint 10.
- Keep Dify attached to the accepted pass-through HTTP caller path only.
- Keep the closed-network BGE-M3 path active for pilot traffic.
- Keep branch protection unchanged.
- Pause traffic immediately when any stop criterion is observed.

## Stop And Rollback Criteria

Pause traffic immediately when any item below is observed:

- Dify no longer behaves as a pass-through caller.
- Dify omits request identifier propagation.
- Dify rewrites request body fields, required headers, or decision values.
- Latency p95 exceeds two times the accepted Sprint 9 BGE measured benchmark p95 for two consecutive snapshots.
- Latency p95 exceeds 2000 ms in any snapshot.
- Error rate is at least 2 percent in a stage.
- Repeated timeout or server error branch occurs in the same stage.
- Authentication, service-scope, active-release, or request-shape error appears after stage configuration is locked.
- Combined fallback, clarify, and off-topic decisions exceed 30 percent without a documented pilot-case explanation.
- Any risk decision lacks operator review before advancement.
- A route key falls outside approved IT helpdesk pilot scope.
- BGE model path is missing, writable, wrong dimension, wrong provider, or shows catalog scope leakage.
- Branch protection is changed or bypassed outside an approved incident record.
- Runtime evidence is staged or prepared for commit.

Rollback action order:

1. Pause the Dify workflow path that sends pilot traffic.
2. Route pilot users to the approved fixed fallback or human handoff path.
3. Capture immediate local ops evidence under the ignored rollback evidence path.
4. Restore the prior approved application image when the image is suspected.
5. Start the prior image with the approved operator-managed environment.
6. Activate the prior known-good release version through the admin release rollback flow.
7. Do not mutate catalog, policy, or test run records during rollback.
8. Confirm readiness and branch protection after rollback.
9. Write a secret-safe official rollback summary with evidence paths and hashes only.

## Local-Only Evidence Boundary

Runtime evidence can be generated only under ignored local paths and must not be staged or committed.

Allowed local-only evidence classes:

- Stage readiness snapshots.
- Ops evidence exports.
- Dify caller operation records.
- Stage review records.
- Rollback evidence when rollback is used.

Official docs may reference:

- Local evidence root path.
- File names that are safe for official reference.
- File hashes.
- Aggregate request counts.
- Aggregate decision counts.
- Aggregate error counts.
- Aggregate latency metrics.
- Operator decisions and approvals.

Official docs must not include:

- Runtime request payloads.
- Raw user text.
- Credential material.
- Dify screenshots or export contents.
- Runtime logs.
- Local state file contents.
- Any forbidden sensitive fragment caught by the repository secret scan.

## Official Summary Boundary

If Sprint 10 operation is executed, create a later official summary with these fields only:

- Date/timezone.
- Git commit at operation start.
- Service identifier.
- Stages completed.
- Traffic caps and actual aggregate counts.
- Dify workflow version identifier.
- Active release version.
- BGE status summary.
- Aggregate latency, error, fallback, risk, and route observations.
- Evidence root path and file hashes only.
- Rollback used: yes or no.
- Admin UI implementation: excluded.
- Runtime evidence committed: no.
- Recommendation value: continue limited pilot, hold, rollback complete, or no-go for broader traffic.

The official summary must not inline runtime evidence or reproduce sensitive local artifacts.

## Task 1: Confirm Sprint 9 Basis And Repo State

**Files:**

- Read: `docs/ops/pilot-sprint-9-execution-closure.md`
- Read: `docs/ops/pilot-sprint-9-go-no-go-decision.md`
- Read: `docs/ops/pilot-sprint-9-release-ticket.md`
- Modify: `docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md`
- Modify: `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`

- [ ] **Step 1: Confirm current git state**

Run:

```bash
git status --short --branch
git rev-parse HEAD
git log --oneline -5
```

Expected:

```text
Plan-creation base HEAD is recorded as d57a4507888c7b21642c0500093e8e06d16c4b57.
Sprint 9 closure merge 075c54b is present in recent history.
Only the two Sprint 10 Task 1 docs are changed by this task.
The future operation-start HEAD will be recorded later and may differ after the planning docs commit.
```

- [ ] **Step 2: Confirm Sprint 9 official basis**

Run:

```bash
rg -n 'Decision value: Go|Blocked Gates|Pilot traffic approved|Dify HTTP caller evidence is accepted|BGE closed-network: measured-pass|Branch protection: accepted|CSV baseline freeze: approved|Admin UI implementation: excluded' \
  docs/ops/pilot-sprint-9-execution-closure.md \
  docs/ops/pilot-sprint-9-go-no-go-decision.md \
  docs/ops/pilot-sprint-9-release-ticket.md
```

Expected:

```text
The Sprint 9 docs confirm Go, no blocked gates, pilot traffic approval, Dify acceptance, BGE measured-pass, branch protection acceptance, CSV freeze approval, and Admin UI exclusion.
```

## Task 2: Maintain Sprint 10 Official Planning Docs

**Files:**

- Modify: `docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md`
- Modify: `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`

- [ ] **Step 1: Keep the formal plan header intact**

Expected:

```text
The implementation plan starts with the required agentic-worker header, goal, architecture, and tech stack.
```

- [ ] **Step 2: Keep operations-control plan aligned**

Expected:

```text
The companion operations-control plan records the same Sprint 9 basis, traffic ramp, stop criteria, rollback criteria, local-only evidence boundary, official summary boundary, and Admin UI exclusion.
```

- [ ] **Step 3: Keep forbidden evidence out of official docs**

Expected:

```text
Official docs prohibit committing runtime evidence, var/evidence, var/pilot, Dify screenshots or exports, runtime logs, local state, and secrets.
The Task 1 implementer leaves files unstaged and uncommitted; the controller may commit reviewed planning docs after approval with no runtime evidence staged.
```

## Task 3: Run Controlled Pilot Ramp

**Files:**

- Read: `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`
- Local-only evidence: ignored paths under `var/evidence`
- Local-only state: ignored paths under `var/pilot`

- [ ] **Step 1: Confirm hard live-traffic authorization gate**

Expected:

```text
Stage 1, Stage 2, and Stage 3 remain blocked until an operator-approved operating window and stage cap are recorded.
The planning docs commit is not treated as live traffic authorization.
```

- [ ] **Step 2: Stage 0 pre-window check**

Expected:

```text
No live requests are sent.
Sprint 9 basis, readiness, active release, BGE path, Dify caller boundary, and branch protection are rechecked.
The operation-start HEAD is recorded before live traffic authorization.
```

- [ ] **Step 3: Stage 1 operator traffic**

Expected:

```text
Blocked until an operator-approved Stage 1 window and cap exist.
At most 10 pilot requests are sent to internal pilot operators.
No stop criteria are triggered before promotion.
```

- [ ] **Step 4: Stage 2 limited user traffic**

Expected:

```text
Blocked until an operator-approved Stage 2 window and cap exist.
At most 50 pilot requests are sent to limited internal pilot users.
Stage 1 aggregate review is accepted before promotion.
```

- [ ] **Step 5: Stage 3 one-business-day traffic**

Expected:

```text
Blocked until an operator-approved Stage 3 window and cap exist.
At most 100 pilot requests are sent to the same limited pilot group.
Stage 2 aggregate review is accepted before promotion.
```

## Task 4: Apply Stop And Rollback Controls

**Files:**

- Read: `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`
- Local-only evidence when used: ignored rollback evidence path under `var/evidence`

- [ ] **Step 1: Check stop criteria at every stage**

Expected:

```text
Latency, error rate, fallback drift, route scope, risk review, Dify caller behavior, BGE path, active release, and branch protection remain within accepted bounds.
```

- [ ] **Step 2: Roll back when required**

Expected:

```text
Dify pilot traffic is paused, users are routed to fallback or handoff, local rollback evidence is captured, the prior known-good release is activated when needed, and official rollback notes contain references and hashes only.
```

## Task 5: Produce Official Summary After Operation

**Files:**

- Create only after operation: `docs/ops/pilot-sprint-10-operation-summary.md`
- Read local-only evidence under ignored paths

- [ ] **Step 1: Draft aggregate-only summary**

Expected:

```text
The summary records stage caps, actual aggregate counts, decision summary, BGE status, Dify caller status, rollback status, Admin UI exclusion, runtime evidence commit boundary, and one final recommendation value.
```

- [ ] **Step 2: Verify summary boundary**

Expected:

```text
The summary contains no runtime payloads, raw user text, credential material, Dify screenshots or export contents, runtime logs, local state contents, or forbidden sensitive fragments.
```

## Task 6: Verify Planning Docs

**Files:**

- Verify: `docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md`
- Verify: `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`

- [ ] **Step 1: Run repository secret scan on the two planning docs**

Run:

```bash
uv run python - docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md docs/ops/pilot-sprint-10-operation-monitoring-plan.md <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory
with TemporaryDirectory() as tmpdir:
    result = scan_evidence_directory(Path(tmpdir), extra_paths=[Path(path) for path in sys.argv[1:]])
expected = SecretScanResult(passed=True, findings=[])
if result != expected:
    raise SystemExit(result)
print('secret-safe Sprint 10 planning docs verified')
PY
```

Expected:

```text
secret-safe Sprint 10 planning docs verified
```

- [ ] **Step 2: Run whitespace check that covers untracked planning docs**

Run:

```bash
uv run python - docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md docs/ops/pilot-sprint-10-operation-monitoring-plan.md <<'PY'
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
print("whitespace-safe Sprint 10 planning docs verified")
PY
```

Expected:

```text
whitespace-safe Sprint 10 planning docs verified
```

- [ ] **Step 3: Optional git diff whitespace check after staging is approved**

Run only when the controller is ready to stage reviewed planning docs:

```bash
git diff --check -- docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md docs/ops/pilot-sprint-10-operation-monitoring-plan.md
```

Expected:

```text
No output for tracked or staged content.
```

Note: `git add --intent-to-add` also makes untracked docs visible to `git diff --check`, but it creates index entries. If used, clear those entries before ending a no-stage subtask, or replace them with explicit staging only after controller approval.

- [ ] **Step 4: Confirm Task 1 implementer does not stage or commit**

Run:

```bash
git status --short -- docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md docs/ops/pilot-sprint-10-operation-monitoring-plan.md
git diff --name-only --cached
```

Expected:

```text
The two Task 1 docs may be modified or untracked.
No staged files are left by the Task 1 implementer.
After spec and quality approval, the controller may stage and commit only these two planning docs.
```

## Completion Criteria

- Sprint 10 official implementation plan exists at `docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md`.
- Sprint 10 operations-control plan exists at `docs/ops/pilot-sprint-10-operation-monitoring-plan.md`.
- Both docs state Admin UI implementation is excluded.
- Both docs prohibit committing runtime evidence, `var/evidence`, `var/pilot`, Dify screenshots or exports, runtime logs, local state, and secrets.
- Sprint 9 basis is recorded as Go, no blocked gates, pilot traffic approved, Dify HTTP caller accepted, BGE measured-pass, branch protection accepted, and CSV freeze approved.
- Planning docs pass repository secret scan and the whitespace check that covers untracked docs.
- Task 1 implementer ends without staging, committing, or creating runtime evidence.
- After review approval, the controller may commit only the two secret-safe planning docs, with no runtime evidence staged.

## Self-Review

Spec coverage:

- Formal superpowers header: covered at the top of this plan.
- Goal, architecture, tech stack: covered at the top of this plan.
- Task checkboxes: covered in Tasks 1 through 6.
- Traffic ramp and hard operator approval gate: covered in Traffic Ramp and Task 3.
- Stop and rollback criteria: covered in Stop And Rollback Criteria and Task 4.
- Local-only evidence boundary: covered in Local-Only Evidence Boundary.
- Official summary boundary: covered in Official Summary Boundary and Task 5.
- Verification commands, including untracked-doc whitespace checking: covered in Task 6.
- Admin UI exclusion and evidence commit prohibition: covered in Scope, File Boundaries, and Completion Criteria.
