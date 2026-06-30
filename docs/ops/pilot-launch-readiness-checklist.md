# Pilot Launch Readiness Checklist

Pilot Launch Readiness & Evidence Closure

This checklist is the Sprint 7 launch readiness gate after Sprint 6 evidence
bundle review. Complete this checklist before marking pilot readiness as go.
Admin UI excluded from Sprint 7 pilot launch readiness.

## Scope

Use `docs/ops/pilot-launch-readiness-checklist.md` to close launch evidence for
the API-only pilot path. The checklist covers local rehearsal regeneration,
Dify UI dry-run evidence, closed-network BGE evidence status, branch protection
evidence, CSV baseline freeze approval, release ticket review, and the pilot
go/no-go decision record.

The filled release ticket path is var/evidence/${SERVICE_ID}/release-ticket.md.
The pilot go/no-go decision record path is var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md.

Launch closure must keep evidence references only: no secrets, no raw query text,
and no pasted runtime payload material.

## Evidence Closure Order

1. Regenerate or review local rehearsal evidence.
2. Complete Dify UI dry-run evidence and record the Dify workflow version identifier.
3. Complete closed-network BGE measured evidence or record pending-host-access exception approval.
4. Capture branch protection evidence for main and CI / verify.
5. Record CSV baseline freeze approval or policy-approved refresh approval.
6. Dry-fill the release ticket and run secret-scan review commands.
7. Write the pilot go/no-go decision record.

Do not skip this order. Earlier evidence may feed later approvals, and the final
pilot go/no-go decision record must reflect every unresolved condition.

## Local Rehearsal Regeneration

Confirm local rehearsal regeneration before release ticket dry-fill:

- Use the Sprint 6 bundle review in `docs/ops/pilot-evidence-bundle-checklist.md`
  as the evidence quality bar.
- Regenerate the rehearsal when the checked-in pilot catalog, policy, CSV cases,
  or baseline changed after the last bundle.
- Record the rehearsal manifest path, final status, manifest hash, and
  secret-scan status in `release-ticket.md`.
- If review reuses an existing bundle, record who approved reuse and why the
  bundle still covers the launch candidate.

Local rehearsal go requires the manifest to show PASS and its review commands to
show no secrets and no raw query text.

## Dify UI Dry-Run Closure

Complete Dify UI dry-run evidence after local rehearsal review:

- Confirm the Dify workflow version identifier is recorded.
- Confirm Dify UI dry-run evidence references are attached or linked in the
  release ticket without screenshots or exports committed to the repository.
- Confirm request headers, service ID, app ID, key ID, and request ID are
  documented by reference only.
- Confirm Dify decision evidence matches the pilot route expectations.

If the Dify UI dry-run is incomplete, the go/no-go decision must be No Go or
Conditional Go with an owner, approval ID, blocking impact, and explicit closure
condition.

## Closed-Network BGE Closure

Record BGE evidence status before closed-network pilot traffic:

- `measured-pass` means package preflight, benchmark, closed-network rehearsal,
  offline runtime, and secret scan are complete and accepted.
- `measured-fail` blocks go until the failure is corrected and evidence is
  regenerated.
- `pending-host-access` may be carried only with pending-host-access exception
  approval, an owner, an approval ID, and a blocking impact in the pilot
  go/no-go decision record.

Go requires BGE measured-pass before real closed-network traffic. Conditional Go
may cover only documented access timing, not a failed measurement.

## Branch Protection Closure

Capture branch protection evidence for `main` and CI / verify:

- Record the source of the rule or ruleset evidence.
- Confirm required status checks include CI / verify.
- Confirm direct pushes and unreviewed changes are blocked by policy.
- Attach only references or sanitized review notes to the release ticket.

If branch protection evidence is missing, keep the launch decision as No Go or
Conditional Go with explicit approval and impact.

## CSV Baseline Freeze Closure

Record CSV baseline freeze approval before final launch review:

- Confirm the checked-in baseline is the approved pilot baseline.
- Record CSV baseline freeze approval in the release ticket.
- If the baseline changed, record the policy-approved refresh approval instead.
- Confirm the launch candidate did not bypass the required balanced gate.

Any unexplained baseline drift blocks go.

## Release Ticket Review

Dry-fill `release-ticket.md` only after the closure items above have evidence:

- Record local rehearsal regeneration or approved reuse.
- Record Dify UI dry-run evidence and Dify workflow version identifier.
- Record BGE evidence status and any pending-host-access exception approval.
- Record branch protection evidence for `main` and CI / verify.
- Record CSV baseline freeze approval or policy-approved refresh approval.
- Run the documented secret-scan review commands and record that they printed no
  findings.

The release ticket must contain references only. It must contain no secrets and
no raw query text.

## Go/No-Go Decision

Write the pilot go/no-go decision record after release ticket review. Allowed
decision values are Go, Conditional Go, and No Go.

Go requires accepted evidence for local rehearsal, Dify UI dry-run,
closed-network BGE, branch protection, CSV baseline freeze, release ticket
secret-scan review, and approval ownership.

Conditional Go is allowed only when each remaining condition has an owner, an approval ID, and a blocking impact recorded in the go/no-go decision record.

No Go is required when a required evidence item is missing, failed, unsafe to
attach, or not approved by the responsible owner.

## Failure Handling

When a closure item fails:

- Stop launch approval and keep the decision as No Go until evidence is fixed.
- Regenerate local rehearsal evidence when the failure affects runtime,
  readiness, Dify matrix, CSV baseline, ops evidence, or secret-scan output.
- Re-run the relevant review commands after every evidence update.
- Update the release ticket and pilot go/no-go decision record with the latest
  status and owner.

Do not convert a failed measurement into Conditional Go unless the approved
policy explicitly allows the exception and the record names the blocking impact.

## Files That Must Not Be Committed

Do not commit runtime evidence or local-only pilot material:

- `var/evidence`
- `var/pilot`
- secret-suffixed JSON state files
- screenshots, exports, local logs, or runtime evidence bundles
- generated API keys, bearer tokens, KEK values, encrypted payload material, or
  raw query text

Store these materials only in the approved evidence location and attach sanitized
references to the release ticket.
