# Sprint 10 Pilot Operation And Monitoring Plan

> **Operations-control document:** This companion plan controls Sprint 10 pilot operation after the Sprint 9 Go decision. It does not start traffic, does not authorize runtime changes, and does not permit committing runtime evidence.

**Goal:** Run a limited Sprint 10 pilot focused on operation, monitoring, evidence review, and rollback readiness.

**Architecture:** Sprint 10 uses the existing runtime APIs, Dify pass-through HTTP caller, closed-network BGE-M3 path, ops evidence exporter, and branch protection. Runtime evidence remains local under ignored paths, and official docs contain only aggregate outcomes, references, hashes, approvals, and decisions. Admin UI implementation is excluded.

**Tech Stack:** Markdown operations records, existing FastAPI runtime and admin APIs, Dify HTTP Request caller, BGE-M3 closed-network runtime, existing ops evidence exporter, GitHub branch protection, repository secret scan helper.

---

## Control Status

- Date/timezone: 2026-07-01, Asia/Seoul.
- Checked branch: `codex/sprint-10-pilot-ops`.
- Plan-creation base HEAD before the Sprint 10 planning docs commit: `d57a4507888c7b21642c0500093e8e06d16c4b57`.
- Sprint 9 closure merge: `075c54b5bf241686368a9ec715f727a606a65940`.
- Newer pre-plan base context: PR #14 Admin UI handbook docs merge is present in the plan-creation base and remains out of scope for Sprint 10 pilot operation.
- Later planning commits may move HEAD forward; do not require operation-start HEAD to equal the plan-creation base.
- Record the actual operation-start HEAD in the local operation index and later official summary before any live traffic.
- Proceed decision: Sprint 10 planning and operations control can proceed.
- Traffic start: requires an operator-approved window and cap.

## Sprint 9 Accepted Basis

- Sprint 9 decision: Go.
- Sprint 9 blocked gates: None.
- Pilot traffic approved: yes.
- Dify HTTP caller accepted: yes, while it remains a pass-through caller for `/v1/intent-route`.
- BGE closed-network status: measured-pass.
- Branch protection: accepted with `CI / verify`.
- CSV baseline freeze: approved.
- Admin UI implementation: excluded.
- Runtime evidence commit boundary: runtime evidence was not committed.

Official basis documents:

- `docs/ops/pilot-sprint-9-execution-closure.md`
- `docs/ops/pilot-sprint-9-go-no-go-decision.md`
- `docs/ops/pilot-sprint-9-release-ticket.md`

## Operating Scope

In scope:

- Limited pilot traffic only.
- Latency, error, fallback, risk, and route observation.
- Dify caller behavior review.
- BGE path normalcy review.
- Active release and readiness observation.
- Rollback readiness.
- Secret-safe official summary after operation, if operation is executed.

Out of scope:

- Broad production launch.
- Admin UI implementation.
- Runtime feature code.
- Admin UI handbook changes.
- Catalog, policy, baseline, or release mutation outside an approved incident or rollback action.
- Committing runtime evidence, `var/evidence`, `var/pilot`, Dify screenshots or exports, runtime logs, local state, or secrets.

## Traffic Ramp Controls

Stages 1, 2, and 3 are blocked until an operator-approved operating window and
stage cap exist. A planning-doc commit never authorizes live traffic by itself.

| stage | duration | cap | audience | promotion rule |
| --- | --- | --- | --- | --- |
| 0 | pre-window | 0 live requests | operator only | Sprint 9 basis and readiness are rechecked |
| 1 | 30 minutes | 10 requests | internal pilot operators | operator-approved window and cap exist, and no stop criteria triggered |
| 2 | 4 hours | 50 requests | limited internal pilot users | operator-approved window and cap exist, and stage 1 summary accepted |
| 3 | 1 business day | 100 requests | same limited pilot group | operator-approved window and cap exist, and stage 2 summary accepted |

Traffic controls:

- Treat Stage 1, Stage 2, and Stage 3 as blocked until the operator-approved window and cap are recorded.
- Do not exceed the stage cap.
- Do not add broad production users during Sprint 10.
- Keep Dify on the accepted pass-through caller path.
- Keep BGE-M3 closed-network mode active for pilot traffic.
- Keep branch protection unchanged.
- Pause traffic immediately when any stop criterion is met.

## Monitoring Controls

Observe these aggregate values at every capture point:

- Request count by stage.
- Decision counts for confident, clarify, fallback, off-topic, and risk outcomes.
- Error counts by category.
- Latency p50, p95, and maximum.
- Top approved route keys.
- Active release version.
- Readiness status.
- Operator review state for fallback, risk, and handoff outcomes.
- Dify request identifier propagation.
- Dify preservation of required request shape and decision values.
- BGE model path, provider, dimension, batch size, token limit, and route-scope normalcy.

Official docs may record only aggregate values, paths, hashes, approvals, and decisions.

## Stop Criteria

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

## Rollback Controls

Rollback is required when a stop criterion cannot be resolved inside the current stage.

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

## Evidence Controls

Local-only evidence may include:

- Stage readiness snapshots.
- Ops evidence exports.
- Dify caller operation records.
- Stage review records.
- Rollback evidence when rollback is used.

Local-only evidence must remain under ignored paths. Do not stage or commit runtime evidence, `var/evidence`, `var/pilot`, Dify screenshots or exports, runtime logs, local state, or secrets.

Official records may include:

- Local evidence root path.
- File names that are safe for official reference.
- File hashes.
- Aggregate traffic counts.
- Aggregate decision counts.
- Aggregate error counts.
- Aggregate latency metrics.
- Operator approvals and decisions.

Official records must not include:

- Runtime request payloads.
- Raw user text.
- Credential material.
- Dify screenshots or export contents.
- Runtime logs.
- Local state file contents.
- Sensitive fragments rejected by the repository secret scan.

## Official Summary Boundary

If Sprint 10 operation is executed, create `docs/ops/pilot-sprint-10-operation-summary.md` after local evidence review.

The official summary must include:

- Date/timezone.
- Git commit at operation start.
- Service identifier.
- Operating stages completed.
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

## Operator Checklist

- [ ] Confirm Sprint 9 accepted basis before the operating window.
- [ ] Record operation-start HEAD before any live traffic.
- [ ] Confirm stage 0 sends 0 live requests.
- [ ] Confirm Stage 1 remains blocked until an operator-approved window and cap exist.
- [ ] Confirm Stage 2 remains blocked until an operator-approved window and cap exist.
- [ ] Confirm Stage 3 remains blocked until an operator-approved window and cap exist.
- [ ] Confirm stage 1 cap is 10 requests after approval.
- [ ] Confirm stage 2 cap is 50 requests after approval.
- [ ] Confirm stage 3 cap is 100 requests after approval.
- [ ] Confirm Dify remains a pass-through caller.
- [ ] Confirm BGE-M3 path remains normal.
- [ ] Confirm branch protection remains unchanged.
- [ ] Confirm all runtime evidence remains local and ignored.
- [ ] Confirm Admin UI implementation remains excluded.
- [ ] Confirm official summary uses aggregate values only.

## Verification Commands

Run the repository secret scan on the two Sprint 10 planning docs:

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

Run the whitespace check that covers untracked planning docs:

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

Optional git diff whitespace check after controller staging is approved:

```bash
git diff --check -- docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md docs/ops/pilot-sprint-10-operation-monitoring-plan.md
```

Note: `git add --intent-to-add` also makes untracked docs visible to `git diff --check`, but it creates index entries. If used, clear those entries before ending a no-stage subtask, or replace them with explicit staging only after controller approval.

Confirm the Task 1 implementer did not stage or commit:

```bash
git status --short -- docs/superpowers/plans/2026-07-01-intent-routing-sprint-10.md docs/ops/pilot-sprint-10-operation-monitoring-plan.md
git diff --name-only --cached
```

Expected:

```text
Secret scan prints the Sprint 10 planning docs verification message.
Whitespace check prints the Sprint 10 planning docs verification message.
No files are staged by the Task 1 implementer.
After spec and quality approval, the controller may stage and commit only these two planning docs.
```
