# Pilot Go/No Go Decision Template

Use this template for the final Sprint 7 pilot decision record.

Template path:
`docs/ops/pilot-go-no-go-decision-template.md`

Completed decision path:
`var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md`

The decision record links `release-ticket.md` and keeps evidence references,
gate results, owners, approval IDs, and launch boundaries only. It must contain
no secrets and no raw query text.

Admin UI excluded from Sprint 7.

## Decision

- Decision value: Go / No Go / Conditional Go
- Decision timestamp:
- Decision owner:
- Release ticket: release-ticket.md
- Decision summary:

Allowed decision values:

- Go
- No Go
- Conditional Go

## Decision Criteria

Choose Go only when every required gate has accepted evidence and owner
approval.

Choose Conditional Go only for approved, bounded conditions. Each condition
still needs a condition owner, approval ID, expiry, next review date, and launch
boundary impact.

Choose No Go when evidence is missing, failed, unsafe, or unapproved. Failed or
unapproved evidence cannot be converted to Conditional Go.

## Evidence Summary

- release-ticket.md:
- local rehearsal evidence:
- Dify UI dry-run evidence:
- BGE evidence status:
- branch protection evidence:
- CSV baseline freeze approval:
- release ticket review:

## Gate Results

- CI / verify:
- local rehearsal final_status PASS:
- local rehearsal secret_scan.passed true:
- Dify UI dry-run evidence:
- BGE evidence status:
- branch protection evidence:
- CSV baseline freeze approval:
- release ticket review:
- Admin UI excluded from Sprint 7:

## Conditional Go Conditions

Each Conditional Go condition requires:

- blocked gate:
- condition owner:
- approval ID:
- expiry:
- next review date:
- launch boundary impact:
- closure evidence required:

pending-host-access expires before pilot traffic and blocks closed-network pilot traffic.

## Blocked Gates

Use this section for No Go gates and for Conditional Go gates that still block a
specific launch boundary.

- blocked gate:
- blocking reason:
- owner:
- approval ID, if exception-approved:
- required evidence before unblock:

## Approval Record

- Engineering approver:
- Operations approver:
- Security approver:
- Dify owner:
- Pilot owner:
- approval ID:
- approval timestamp:

## Launch Boundary

- Pilot traffic boundary:
- Closed-network pilot traffic allowed: yes / no
- Dify pilot traffic allowed: yes / no
- pending-host-access status:
- expires before pilot traffic:
- Boundary notes:

Conditional Go cannot allow traffic across a boundary that is still blocked by
missing, failed, unsafe, or unapproved evidence.
Failed or unapproved evidence remains No Go until corrected evidence is accepted.

## Secret And Raw Query Review

- Decision record contains no secrets: yes / no
- Decision record contains no raw query text: yes / no
- release-ticket.md contains no secrets or raw query text: yes / no
- Evidence links only: yes / no
