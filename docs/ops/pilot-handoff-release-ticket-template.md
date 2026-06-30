# Pilot Handoff And Release Ticket Template

Use this template for the Sprint 6 pilot handoff and release ticket. It may be
copied to an evidence directory as `release-ticket.md`, so keep the filled copy
limited to evidence references, hashes, decisions, and approvals. The ticket
must contain no secrets and no raw query text.

Template path:
`docs/ops/pilot-handoff-release-ticket-template.md`

## Release Scope

- service_id:
- environment:
- release_version:
- Pilot boundary:
- Admin UI excluded from Sprint 6:
- Included operator surfaces:
- Excluded operator surfaces:

## Code And CI

- commit SHA:
- PR URL:
- CI / verify result:
- Required checks:
- Build or package reference:

Gate: go requires CI / verify pass.

## Local Rehearsal Evidence

- local rehearsal manifest:
- manifest sha256:
- final_status:
- secret_scan.passed:
- Evidence bundle path:

Gates:

- go requires local rehearsal final_status PASS.
- go requires local rehearsal secret_scan.passed true.

## Dify UI Dry-Run Evidence

- Dify workflow version identifier:
- Dify UI evidence path:
- Dify UI dry-run evidence reviewer:
- Dify evidence linked from release ticket: yes / no; the Dify UI evidence path
  points to the completed service evidence file.
- Dify condition owner, if blocked:
- Follow-up approval ID, if blocked:
- Dify smoke matrix evidence:
- Operator handoff checklist status:

Gate: go requires Dify UI evidence path and workflow version identifier.
Gate: go requires Dify UI dry-run evidence reviewer approval.
Gate: go requires the Dify UI evidence path to be linked from release-ticket.md.
Gate: blocked Dify evidence requires a condition owner and approval ID before Conditional Go.

## Closed-Network BGE Evidence

- BGE evidence status:
- Package preflight evidence:
- Benchmark evidence:
- Closed-network rehearsal evidence:
- Exception approval ID, if pending-host-access:
- Exception owner, if pending-host-access:
- Expires before pilot traffic:
- Next measurement date:
- Decision impact:

Gate: go requires BGE measured-pass before closed-network pilot traffic.
Gate: Conditional Go with pending-host-access requires exception approval ID,
exception owner, expiration before pilot traffic, and next measurement date.
Gate: measured-fail blocks pilot launch until corrected evidence passes.

## Branch Protection Evidence

- branch protection evidence:
- Protected branch:
- Required check evidence:
- Evidence type: apply / verify / rollback / operator-not-permitted
- Authorized operator:
- Operator permission result: authorized / operator-not-permitted
- Rule snapshot path: var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
- Verification output: branch protection capture verified
- Final branch protection state:
- Reviewer or approval evidence:

Gate: go requires branch protection evidence for main.
Gate: go requires authorized branch protection evidence for main.
Gate: operator-not-permitted does not satisfy pilot go/no-go.
Gate: rollback or bypass evidence must include approval ID, exact commit SHA,
workflow_dispatch rerun URL, artifact review result, and final branch
protection state.

## CSV Baseline Evidence

- CSV baseline comparison:
- Baseline file:
- Comparison report:
- Approved refresh reference, if applicable:

Gate: go requires CSV baseline comparison PASS.

## Security And Incident Rehearsal Evidence

- API key rotation overlap evidence:
- KEK rewrap dry-run evidence:
- Runtime raw-query retention dry-run evidence:
- Incident fallback drill evidence:
- Raw-query exception audit evidence, if applicable:

Security gate: ticket must not contain secrets or raw query text.

## Rollback Plan

- rollback plan:
- Trigger:
- Operator:
- Steps:
- Expected restoration point:
- Evidence to collect after rollback:
- Branch protection rollback or bypass evidence:

## Open Risks

- Risk:
- Owner:
- Mitigation:
- Decision impact:

## Go/No-Go Decision

- go/no-go:
- Decision timestamp:
- Decision owner:
- Gate summary:
- Conditions:

Required go gates:

- go requires CI / verify pass.
- go requires local rehearsal final_status PASS.
- go requires local rehearsal secret_scan.passed true.
- go requires Dify UI evidence path and workflow version identifier.
- go requires Dify UI dry-run evidence reviewer approval.
- go requires the Dify UI evidence path to be linked from release-ticket.md.
- blocked Dify evidence requires a condition owner and approval ID before Conditional Go.
- go requires CSV baseline comparison PASS.
- go requires branch protection evidence for main.
- go requires authorized branch protection evidence for main.
- operator-not-permitted does not satisfy pilot go/no-go.
- rollback or bypass evidence must include approval ID, exact commit SHA,
  workflow_dispatch rerun URL, artifact review result, and final branch
  protection state.
- go requires BGE measured-pass before closed-network pilot traffic.
- Conditional Go with pending-host-access requires exception approval ID,
  exception owner, expiration before pilot traffic, and next measurement date.
- measured-fail blocks pilot launch until corrected evidence passes.
- Admin UI excluded from Sprint 6.
- ticket must not contain secrets or raw query text.

## Approvals

- Engineering approver:
- Operations approver:
- Security approver:
- Dify owner:
- Pilot owner:
