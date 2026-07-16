# ADR: Test Run Replay Source Access

## Status

Accepted

## Context

The Admin Console Test Runs workflow needs to support failure investigation,
editing, and replay of a prior CSV dataset. Test case queries and memos are
stored in `test_cases`, while normal Test Run result responses expose only a
masked query. Returning reconstructed CSV content therefore crosses the existing
raw-text boundary and requires an explicit authorization and audit decision.

The related product requirements are `TC-029`, `TC-030`, and PRD section `8.1
CSV 테스트 목적`.

## Decision

Expose a service-scoped replay-source read endpoint only to `system_admin` and
the target Service's `service_owner`. The endpoint reconstructs CSV from stored
TestCase rows and never adds raw query content to Test Run history, summary,
result, or audit-log responses.

Every successful replay-source read is audited with metadata only. A replayed
Test Run uses the existing create endpoint with an optional source Test Run ID;
successful replay creation is also audited without raw content. Normal Test Run
creation and masked result access retain their existing catalog-access roles.

Add an opaque trace ID to each Test Result so result evidence can be referenced
without exposing raw source content or claiming a runtime log exists.

## Alternatives Considered

### Option 1: Owner-only raw source access

* Pros: Supports editable replay while limiting raw-text exposure and providing
  an audit trail.
* Cons: Service developers must ask an owner to load historical source content.

### Option 2: All catalog editors can access raw source

* Pros: Fastest developer iteration.
* Cons: Broadens exposure of queries and memos beyond the minimum operational
  role and weakens the existing masked-result boundary.

### Option 3: Server-side replay without returning raw source

* Pros: Minimizes raw-text exposure.
* Cons: Prevents editing failed cases before replay and does not satisfy the
  approved improvement workflow.

## Consequences

Owners can reconstruct and edit historical test datasets without copying an
internal ID or retaining the original local file. The reconstructed CSV is
semantically equivalent but not byte-for-byte identical. Raw test content
becomes a maintained Admin API security boundary and requires authorization,
audit, and negative integration tests.

Existing test case storage remains unchanged; this decision does not add raw
text to Test Results or Audit Logs. A future requirement to grant developers
access or introduce approval must revisit this ADR.

## Implementation Notes

* Add an owner-only replay-source endpoint below the service-scoped Test Run
  resource.
* Serialize stored TestCase rows through the standard CSV writer.
* Add a dedicated owner-or-system-admin permission guard.
* Audit successful source reads and successful replays using metadata only.
* Add `trace_id` to Test Result persistence and response contracts.
* Keep normal browser authentication on the `irt_admin_session` HttpOnly cookie.

## Verification

* Positive API tests for system-admin and target-Service owner access.
* Negative tests for developer, operator, auditor, unrelated owner, and
  cross-Service access.
* Audit assertions proving raw query, memo, and CSV text are absent.
* Migration and API contract tests for unique non-null Test Result trace IDs.
* Frontend role-gate and service-request tests.

## Rollback or Revisit Conditions

Revisit or disable the endpoint if reconstructed source appears in logs, audit
payloads, error messages, caches, or unrelated role responses; if test dataset
storage becomes encrypted or retention-controlled; or if an approval workflow
becomes a product requirement.
