# ADR: Admin UI C-3 Runtime Integration And API Key Scope

## Status

Accepted

## Context

AiIntentRouting targets closed-network financial-sector runtime integration.
The PRD describes Service onboarding, API-key issuance, Dify/client setup,
runtime API calls, masked runtime logs, and audit evidence as one verifiable
operating flow.

Existing ADRs already cover account-session authentication, Service-scoped
RBAC, authorization-first Admin UI onboarding, and workflow candidate endpoints.
C-3 now needs a dedicated decision record because it crosses Admin UI placement,
Admin API contract shape, runtime client authentication, one-time API-key
secret handling, Dify/client guidance, runtime evidence, audit evidence, and
optional DB hardening.

Approved C-3 recommendations are recorded in
`docs/superpowers/plans/2026-07-09-admin-ui-c3-runtime-integration-operations.md`.
This ADR records those approved decisions before implementation begins.

## Decision

C-3 Runtime Integration And Operations is part of the authorization-first onboarding flow.
It follows C-1 Service onboarding and C-2 Service membership so a selected
Service can move from validated release to runtime client setup and operational
evidence.

Service-scoped Admin API key lifecycle endpoints are the future UI contract:

- `GET /admin/v1/services/{service_id}/api-keys`
- `POST /admin/v1/services/{service_id}/api-keys`
- `POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke`

The existing global `/admin/v1/api-keys` endpoints remain transitional for
scripts and backward compatibility during the migration:

- `GET /admin/v1/api-keys`
- `POST /admin/v1/api-keys`
- `POST /admin/v1/api-keys/{key_id}:revoke`

Normal browser Admin UI requests use the `irt_admin_session` cookie and Umi
request, never X-Admin-Token, X-Actor-Id, X-Actor-Roles, or X-Service-Scope.
Those trusted headers remain reserved for controlled bootstrap, break-glass, or
internal automation paths.

Runtime clients call `/v1/intent-route` with `Authorization: Bearer <api_key>`
plus `X-Key-Id`, `X-App-Id`, `X-Service-Id`, and `X-Request-Id`. Runtime API
authentication remains separate from Admin UI session-cookie authentication.

The prior C-3 baseline displayed once on create and never returned the raw
secret after issuance.
The raw API key secret is displayed on create. After
`docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md`, authorized
`system_admin` and selected-Service `service_owner` users may explicitly
reveal/copy the encrypted secret through an audited service-scoped endpoint.
Inventory, revoke, runtime setup guidance, audit logs, runtime logs, and
exports still never embed raw `api_key`. Key inventory and evidence may show only metadata such as `key_id`,
`key_fingerprint`, `app_id`, `service_id`, `environment`, `status`, scope,
expiry, creator, and timestamps.

Allowed intents and route keys are selected from known candidate/list
endpoints. API key scope uses `source=released_catalog` so a key can be issued
from the newest environment release without requiring runtime activation, while
runtime setup guidance continues to display `active_release` independently.

`/api-keys` remains the selected-Service runtime setup workspace. `/services`
may later add only a compact next-step panel that points the user to
`/api-keys` after C-2 role assignment and release readiness are complete.

The C-3 baseline uses checklist/docs client guidance plus an explicit Admin UI
live-test workflow. The live test automatically reveals the encrypted API Secret
through the audited service-scoped reveal endpoint, then uses it only for the
single `/v1/intent-route` request. The UI must not display, persist, store, or
reuse the revealed raw secret in UI state. The secret must not be written to
local storage, inventory responses, runtime setup guidance, audit state,
runtime logs, or exported evidence.

Runtime Logs show `query_masked` by default and must not expose raw query text
in baseline runtime setup views. Audit Logs remain append-only evidence for API
key lifecycle, runtime setup bundle generation if added, and any future
metadata-only validation event.

Baseline C-3 mostly uses existing `api_keys`, `runtime_logs`, and `audit_logs`
fields if candidate validation is enforced at API time. The accepted no-expiry
API key option requires Alembic revision `0011_api_key_optional_expiry`, which
makes `api_keys.expires_at` nullable. Optional hardening constraints and indexes
remain documented for later review.

## Alternatives Considered

### Option 1: Update Existing ADRs Only

* Pros:
  * Fewer ADR files.
  * Keeps C-flow documents compact.
* Cons:
  * Spreads runtime client auth, one-time secret, Admin API scope, Dify setup,
    and operational evidence across unrelated ADRs.
  * Makes future C-3 implementation harder to audit.

### Option 2: Create This Dedicated C-3 ADR

* Pros:
  * Gives future implementers one record for API-key scope, runtime setup,
    Admin UI placement, secret handling, logs, audit, and validation boundaries.
  * Matches the ADR trigger because C-3 affects external API contracts,
    authentication and authorization, DB hardening choices, and core workflow.
* Cons:
  * Adds another ADR that must be kept aligned if the C-3 contract changes.

### Option 3: Defer ADR Until Implementation

* Pros:
  * Fastest if C-3 implementation is delayed.
* Cons:
  * Leaves security-sensitive API and client integration decisions only in a
    plan file.
  * Increases the chance that frontend, backend, docs, and tests drift before
    implementation begins.

### Option 4: Keep Only Global API-Key Endpoints

* Pros:
  * Smallest backend API change.
  * Preserves the existing global endpoint wrappers.
* Cons:
  * Weaker selected-Service contract.
  * Create bodies still carry `service_id`, which makes wrong-Service UI/API
    mismatches easier.

### Option 5: Create A Separate Runtime Setup API Namespace

* Pros:
  * Groups runtime setup concepts under one area.
* Cons:
  * Diverges from the existing `/admin/v1/services/{service_id}/...` Admin API
    route style.
  * Adds extra routing and documentation surface.

### Option 6: Browser Runtime Sample Call

* Pros:
  * Gives immediate in-console feedback after key creation.
* Cons:
  * Extends raw secret lifetime in browser state.
  * Mixes Admin session-cookie auth and runtime Bearer auth in one browser
    workflow.
  * Adds CORS, logging, and accidental secret-copy risk.

## Consequences

C-3 implementation must treat selected Service as part of the Admin API URL for
future key lifecycle writes and reads. Backend tests must reject wrong-Service
revoke attempts and must prove create/list/revoke never expose the raw secret
outside the create response.

The Admin UI must use server-derived session identity and selected Service
state. It must not reintroduce trusted actor headers or manual internal ID
entry for runtime key scope. It must load allowed intents and route keys from
candidate endpoints, baseline `source=released_catalog`.

Runtime client documentation remains explicit about Bearer API-key calls to
`/v1/intent-route`, while Admin UI code remains explicit about
`irt_admin_session` and Umi request. This separation is a security boundary.

Operators get safer baseline guidance at the cost of less in-console runtime
validation. A later metadata-only validation endpoint can be added if operators
need readiness feedback without placing the raw secret back into browser-driven
runtime calls.

Existing database tables can support the baseline, but API-time validation and
tests become more important until optional DB hardening is accepted.

## Implementation Notes

Future backend work should add the Service-scoped key lifecycle endpoints and
keep the existing global endpoints during transition. The Service-scoped create
request should take `{service_id}` from the path, not from the body.

Future Admin UI work should refactor `/api-keys` into the selected-Service
runtime setup workspace and keep `/services` focused on Service onboarding and
membership, with only a compact next-step panel later.

Runtime setup guidance should be read-only and should include endpoint, header
template, body template, timeout, Dify variable mapping, branch checklist, docs
links, active release metadata, and API-key inventory metadata when a `key_id`
is supplied. It must not return `api_key`.

If a future validation endpoint is needed, prefer
`POST /admin/v1/services/{service_id}/runtime-setup:validate` as a
metadata-only preflight. It must not accept or return a raw secret and must not
execute a semantic routing call with a raw user query unless a separate ADR
approves that behavior.

Optional DB hardening to revisit later:

- Index active API keys by `(service_id, environment, app_id, status)`.
- Add a partial index for active, non-revoked keys if query volume requires it.
- Add JSONB validation or check constraints for scope arrays only if API-time
  validation proves insufficient.
- Do not add tables for `allowed_intents` and `allowed_route_keys` in the C-3
  baseline because scope values come from release snapshots, not mutable draft
  Intent rows.

## Verification

This documentation gate is verified by docs contract tests:

- `uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py -q`
- `uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_admin_workflow_candidate_contract_docs.py tests/unit/test_admin_runtime_setup_contract_docs.py -q`

Future implementation verification must add backend, frontend, and runtime
tests proving:

- Service-scoped create/list/revoke endpoints enforce `{service_id}`.
- Raw `api_key` is present only in create response.
- Inventory, revoke, runtime setup guidance, audit logs, and runtime logs never
  return the raw secret.
- Candidate scope comes from `source=released_catalog`.
- Normal Admin UI browser requests use `irt_admin_session` and do not send
  trusted headers.
- Runtime clients use Bearer key plus key/app/service/request headers.
- Runtime Logs show `query_masked` by default.
- Audit Logs remain append-only evidence.

Local verification risk is carried forward from C-1: previous C-1 backend
integration was skipped without `TEST_DATABASE_URL`, and the local stack failed
because of an Alembic revision mismatch. Future C-3 browser QA must either
repair that local Alembic/dev DB mismatch or report the local stack as
unverified with exact command output.

## Rollback or Revisit Conditions

Revisit this decision if:

- security review requires browser or server-side runtime validation before
  client handoff.
- Service-scoped Admin API endpoints cannot preserve backward compatibility
  with scripts.
- `service_owner` or `service_operator` delegation for key lifecycle becomes a
  baseline requirement.
- API-time candidate validation is insufficient and DB constraints or new scope
  tables become mandatory.
- Dify/client integration changes away from Bearer API-key authentication.
- local stack/Alembic issues block C-3 manual QA long enough to change the
  verification strategy.
