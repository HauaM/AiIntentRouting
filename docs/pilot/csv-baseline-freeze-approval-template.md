# CSV Baseline Freeze Approval Template

Template path: `docs/pilot/csv-baseline-freeze-approval-template.md`

Use this template when the pilot launch keeps the checked-in CSV baseline frozen
instead of accepting a policy-approved refresh. The completed copy should be
stored with launch evidence and linked from `release-ticket.md`.

## Target Baseline

- Baseline file: docs/pilot/it-helpdesk-pilot-baseline.json
- Pilot CSV: standard 50-row CSV
- Preset: balanced
- Baseline status: frozen

The checked-in baseline remains docs/pilot/it-helpdesk-pilot-baseline.json.
The baseline freezes the standard 50-row CSV for the balanced preset.

## Current Comparison Evidence

- CSV baseline comparison:
- Comparison evidence path:
- Comparison result: CSV baseline comparison PASS
- `allowed_new_failures: 0`
- `allowed_new_reviews: 0`

allowed_new_failures: 0 remains in force.
allowed_new_reviews: 0 remains in force.
Go requires CSV baseline comparison PASS.

## Freeze Decision

- Refresh status: refresh not approved
- Freeze decision:
- Accepted behavior change: none; if behavior changed, stop and attach a policy-approved refresh approval instead.
- Blocking issue, if any:

Use this freeze approval only when current behavior matches the checked-in
baseline. Do not use this freeze approval to accept changed behavior; if
behavior changed, stop and attach a policy-approved refresh approval instead.

## Reviewers

- Freeze approval ID:
- Release owner:
- QA or security reviewer:
- Review timestamp:

Freeze approval requires an approval ID, release owner approval, and QA or security reviewer approval.

## Release Ticket Link

- Release ticket path: release-ticket.md
- Completed freeze approval evidence path:
- Linked from release-ticket.md: yes / no

## Secret And Raw Query Review

- Raw query review: no raw query text
- Secret-bearing field review: no secret-bearing fields
- Reviewer:

The record must not contain raw query text or secret-bearing fields.
