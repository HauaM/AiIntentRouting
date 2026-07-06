# ADR: Admin UI Workflow Candidate Contracts

## Status

Accepted

## Context

The Admin UI Phase 1 write screens need to hand operators from Intent and
Example work into policy/catalog version creation, test runs, releases, and API
key creation. Without reloadable candidate lists, operators have to copy
internal identifiers such as policy versions, catalog versions, test run ids,
release versions, intent ids, and route keys between pages.

The product direction in `docs/IntentRouting_PRD_ContextReview_20260624.md`
favors guided operations, presets, examples, and service-scoped workflows over
routine manual entry of low-level routing identifiers. The current backend can
create policy versions, catalog versions, test runs, releases, and API keys, but
it does not expose every list the Admin UI needs for selectors and next-action
handoffs.

## Decision

Model Admin UI workflow handoffs as service-scoped candidate endpoints. The
Admin UI will load policy versions, catalog versions, test runs, release
candidates, intent/route candidates, and API key inventory from the server.

Operators select candidates instead of typing internal IDs except source
objects. Source objects remain manually entered only where the operator is
creating the source identity itself, such as a new Intent ID, API key App ID, or
CSV case ID.

Phase 2 governed workflows remain disabled or informational until their explicit
approval contracts are implemented.

## Alternatives Considered

### Option 1: Keep Manual IDs With More Help Text

* Pros:
  * Smallest backend and frontend change.
  * Preserves the current create endpoints.
* Cons:
  * Operators still have to copy internal IDs across pages.
  * The UI cannot reliably prove a selected value is valid for the current
    Service.
  * Help text does not create an auditable or reloadable workflow.

### Option 2: UI-Only Local Handoff

* Pros:
  * Improves values created during the current browser session.
  * Avoids immediate backend contract work.
* Cons:
  * Breaks after refresh, login change, or direct navigation.
  * Cannot load historical candidates.
  * Risks the UI inventing history or eligibility that should come from the
    server.

### Option 3: Service-Scoped Candidate Endpoints

* Pros:
  * Reloadable and auditable.
  * Enforces Service scope and role checks server-side.
  * Matches the operator workflow from Intent Catalog through API Key creation.
  * Keeps the backend as the source of truth for release eligibility.
* Cons:
  * Requires backend contracts, integration tests, frontend service types, and UI
    refactoring.
  * Adds API surface that must be maintained with the Admin UI workflow.

## Consequences

Operators can complete the happy path without copying internal IDs. Backend APIs
become the source of truth for candidate validity, ordering, and release
eligibility. The UI must not fake history, fake pagination, live polling, or
release eligibility when backend support does not exist.

API key inventory must never return raw API key secrets. Candidate responses must
remain scoped to the selected Service except for system-admin API key inventory,
which may accept filters.

## Implementation Notes

Add read endpoints under `/admin/v1` for:

- `GET /admin/v1/services/{service_id}/policy-versions`
- `GET /admin/v1/services/{service_id}/catalog-versions`
- `GET /admin/v1/services/{service_id}/test-runs`
- `GET /admin/v1/services/{service_id}/release-candidates`
- `GET /admin/v1/services/{service_id}/intent-route-candidates`
- `GET /admin/v1/api-keys`

Normal Admin UI authentication remains the server-issued `irt_admin_session`
HttpOnly cookie. Preserve existing Phase 1 create endpoints and derive actor,
role, and Service scope from the authenticated session.

## Verification

Verify this decision with:

- docs contract tests for the ADR, API contract, and pattern kit wording.
- backend integration tests for each candidate/list endpoint.
- frontend service tests and TypeScript checks for the selector contracts.
- manual browser QA for the Intent Catalog to API Key workflow.

## Rollback Or Revisit Conditions

Revisit this decision if:

- candidate endpoints expose sensitive data.
- Service-scope authorization cannot be enforced cleanly.
- API key inventory cannot exclude secrets while remaining useful.
- the candidate contracts become too broad and need a generalized workflow
  engine.
