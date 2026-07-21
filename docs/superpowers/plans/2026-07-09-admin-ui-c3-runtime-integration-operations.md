# Admin UI C-3 Runtime Integration And Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the backend/API/DB/Admin UI/docs/test contract for C-3 so a scoped API key can be created from known Service candidates, handed to Dify/client setup safely, exercised through runtime evidence, and audited without exposing raw secrets.

**Architecture:** Build on the authorization-first C flow: C-1 registers/selects a Service, C-2 assigns Service roles, developers validate and release, then C-3 creates a selected-Service runtime key and provides client setup guidance. Runtime authentication stays API-key based for `/v1/intent-route`; normal Admin UI requests stay account-session based through `irt_admin_session` and Umi `request`. API-key secrets are generated once, stored only as hashes/fingerprints, never returned by inventory, runtime logs show `query_masked`, and audit logs remain append-only evidence.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy ORM, Alembic, pytest, React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design ProComponents, Vitest, Umi `request`, `irt_admin_session` HttpOnly cookie, Bearer API key only for runtime client calls.

---

## Scope Of This Session

This document is the deliverable for the current session.

Do not implement backend, database, frontend, test, or ADR code in this session.

Plan path selected:

- `docs/superpowers/plans/2026-07-09-admin-ui-c3-runtime-integration-operations.md`

This filename is the best fit because it follows the existing `docs/superpowers/plans/YYYY-MM-DD-feature.md` convention and exactly names the C-3 slice.

## Required Context Read

- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md`
- `docs/superpowers/plans/2026-07-08-admin-ui-c1-service-onboarding.md`
- `docs/superpowers/plans/2026-07-08-admin-ui-c2-service-membership-roles.md`
- `docs/IntentRouting_PRD_v0.2_20260624.md`
- `docs/api/admin-workflow-candidate-contracts.md`
- `docs/api/openapi-runtime-examples.md`
- `docs/integrations/dify-http-request-node.md`
- `docs/integrations/dify-handoff-checklist.md`
- `docs/integrations/dify-branching-playbook.md`
- `src/intent_routing/api/admin.py`
- `src/intent_routing/api/runtime.py`
- `src/intent_routing/api/dependencies.py`
- `src/intent_routing/db/models.py`
- `src/intent_routing/db/repositories.py`
- `src/intent_routing/security/api_keys.py`
- `src/intent_routing/routing/engine.py`
- `frontend/intent-routing-console/src/models/adminSession.ts`
- `frontend/intent-routing-console/src/pages/Services/index.tsx`
- `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- `frontend/intent-routing-console/src/services/adminServices.ts`
- `frontend/intent-routing-console/src/types/api.d.ts`
- `docs/AdminUI_Handbook/v04/examples/AdminShell.tsx`
- `docs/AdminUI_Handbook/v04/examples/ServiceScopeBar.tsx`
- `docs/AdminUI_Handbook/v04/examples/RuntimeLogsTable.tsx`
- `docs/AdminUI_Handbook/v04/examples/AuditLogsTable.tsx`
- `docs/AdminUI_Handbook/v04/examples/ConfirmActionButton.tsx`
- `docs/AdminUI_Handbook/v04/examples/FutureFeatureNotice.tsx`
- `docs/AdminUI_Handbook/v04/examples/adminServices.ts`

## Current State

- C-1 is implemented on `/services`: `system_admin` can create a Service, refresh `/me/services`, select the new Service, and move to Intent Catalog.
- C-2 plan and ADR update direction are merged to `main` in PR #30, main commit `8da9c59 docs: plan C-2 service membership contract`.
- C-2 approved direction:
  - update the existing RBAC ADR instead of creating a new C-2 ADR.
  - put selected-Service membership controls inside `/services`.
  - allow only `system_admin` to grant/revoke roles in the C-2 baseline.
  - keep `service_owner` delegation as a future increment.
  - do not start C-2 implementation yet.
- Current backend already has global API-key endpoints:
  - `GET /admin/v1/api-keys`
  - `POST /admin/v1/api-keys`
  - `POST /admin/v1/api-keys/{key_id}:revoke`
- Current backend already stores API-key scope fields:
  - `environment`
  - `app_id`
  - `service_id`
  - `allowed_intents`
  - `allowed_route_keys`
  - `status`
  - `expires_at`
  - `revoked_at`
  - `key_hash`
  - `key_fingerprint`
- Current backend already returns `api_key` only from create response and excludes it from inventory.
- Current runtime API `/v1/intent-route` authenticates with:
  - `Authorization: Bearer <api_key>`
  - `X-Key-Id`
  - `X-App-Id`
  - `X-Service-Id`
  - optional `X-Request-Id`
- Current runtime auth rejects wrong service/app/environment/secret/status/expiry before routing and passes `allowed_intents` and `allowed_route_keys` to `RoutingEngine`.
- Current runtime tests already cover masked runtime logs, runtime errors, route-scope unauthorized decisions, and append-only audit evidence for raw query access.
- Current Admin UI already has `/api-keys`, using selected Service context, candidate selectors, one-time secret alert, inventory without raw secret, and revoke confirmation.
- C-3 implementation must remain contract-first now that endpoint shape, service scoping, setup guidance, optional validation, docs contract, and ADR path have been approved as one C-3 contract.

## C-3 Backend Contract Draft

### Endpoint Candidate Decision

Recommended endpoint shape for future C-3 implementation:

- Add Service-scoped API-key lifecycle endpoints:
  - `GET /admin/v1/services/{service_id}/api-keys`
  - `POST /admin/v1/services/{service_id}/api-keys`
  - `POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke`
- Keep the existing global endpoints during transition:
  - `GET /admin/v1/api-keys`
  - `POST /admin/v1/api-keys`
  - `POST /admin/v1/api-keys/{key_id}:revoke`
- Update Admin UI C-3 to call the Service-scoped endpoints only.

Why this shape:

- It matches the project API pattern for selected-Service resources.
- It removes `service_id` from the create body, so the UI cannot accidentally post a key for a different Service than the selected one.
- It lets the backend reject key revocation if `{key_id}` belongs to another Service.
- It keeps current CLI/scripts/global system-admin inventory compatible during migration.

Alternative endpoint candidates to document but not choose by default:

- Keep only global `/api-keys`.
  - Smaller change.
  - Weaker selected-Service contract and easier to misuse from UI.
- Create `/admin/v1/runtime-setup/api-keys`.
  - Groups runtime setup actions.
  - Breaks the established `/services/{service_id}/...` Admin API pattern.

### API Key Lifecycle Schemas

`GET /admin/v1/services/{service_id}/api-keys`

Query:

```json
{
  "environment": "prod",
  "status": "active",
  "limit": 50
}
```

Response:

```json
[
  {
    "key_id": "key_live_012345",
    "key_fingerprint": "sha256:<digest>:9AbC",
    "environment": "prod",
    "app_id": "dify-platform",
    "service_id": "it-helpdesk",
    "allowed_intents": ["it_api_timeout"],
    "allowed_route_keys": ["it.api_timeout.manual_lookup"],
    "status": "active",
    "expires_at": "2026-10-07T00:00:00Z",
    "revoked_at": null,
    "created_by": "admin-user",
    "created_at": "2026-07-09T00:00:00Z"
  }
]
```

Security rule: `api_key` raw secret is never present in this response.

`POST /admin/v1/services/{service_id}/api-keys`

Request:

```json
{
  "environment": "prod",
  "app_id": "dify-platform",
  "allowed_intents": ["it_api_timeout"],
  "allowed_route_keys": ["it.api_timeout.manual_lookup"],
  "expires_in_days": 90
}
```

Response:

```json
{
  "key_id": "key_live_012345",
  "api_key": "irt_<one-time-secret>",
  "api_key_displayed_once": true,
  "key_fingerprint": "sha256:<digest>:9AbC",
  "environment": "prod",
  "app_id": "dify-platform",
  "service_id": "it-helpdesk",
  "allowed_intents": ["it_api_timeout"],
  "allowed_route_keys": ["it.api_timeout.manual_lookup"],
  "status": "active",
  "expires_at": "2026-10-07T00:00:00Z",
  "revoked_at": null,
  "created_by": "admin-user",
  "created_at": "2026-07-09T00:00:00Z"
}
```

Security rules:

- `api_key` is present only in this create response.
- `api_key` is not persisted as plaintext.
- `api_key` is not inserted into audit log `before_state` or `after_state`.
- Inventory and revoke responses never include `api_key`.
- UI keeps the secret only in current component state and clears it on selected-Service change, refresh, navigation, logout, and successful revoke.

`POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke`

Response:

```json
{
  "key_id": "key_live_012345",
  "key_fingerprint": "sha256:<digest>:9AbC",
  "environment": "prod",
  "app_id": "dify-platform",
  "service_id": "it-helpdesk",
  "allowed_intents": ["it_api_timeout"],
  "allowed_route_keys": ["it.api_timeout.manual_lookup"],
  "status": "revoked",
  "expires_at": "2026-10-07T00:00:00Z",
  "revoked_at": "2026-07-09T01:00:00Z",
  "created_by": "admin-user",
  "created_at": "2026-07-09T00:00:00Z"
}
```

### Allowed Intent/Route Candidate Contract

Use the existing candidate endpoint as the C-3 baseline:

- `GET /admin/v1/services/{service_id}/intent-route-candidates`

Query:

```json
{
  "source": "released_catalog",
  "environment": "prod"
}
```

Response:

```json
[
  {
    "intent_id": "it_api_timeout",
    "display_name": "API timeout incident",
    "route_key": "it.api_timeout.manual_lookup",
    "status": "active",
    "source": "released_catalog"
  }
]
```

C-3 rule:

- API key scope selectors must load known candidates from this endpoint.
- The C-3 UI must not ask operators to type manual `intent_id` or `route_key` scope strings.
- C-3 create endpoint must reject `allowed_intents` or `allowed_route_keys` that are not present in the selected candidate source.
- C-3 baseline should use `source=released_catalog` so keys cannot be scoped to unreleased draft routes and do not require activation.
- If no release exists, candidate response can be `[]`, but key creation must block with an explicit error that a released catalog is required for scoped runtime setup.

### Runtime Setup/Guidance Endpoint

Recommended new read endpoint:

- `GET /admin/v1/services/{service_id}/runtime-setup`

Query:

```json
{
  "environment": "prod",
  "app_id": "dify-platform",
  "key_id": "key_live_012345"
}
```

Response:

```json
{
  "service_id": "it-helpdesk",
  "environment": "prod",
  "runtime_endpoint": "/v1/intent-route",
  "recommended_timeout_seconds": 8,
  "active_release": {
    "release_version": "rel-it-helpdesk-20260709-001",
    "policy_version": "pol-it-helpdesk-20260709-001",
    "intent_catalog_version": "cat-it-helpdesk-20260709-001",
    "test_run_id": "tr-it-helpdesk-20260709-001"
  },
  "selected_key": {
    "key_id": "key_live_012345",
    "key_fingerprint": "sha256:<digest>:9AbC",
    "app_id": "dify-platform",
    "status": "active",
    "expires_at": "2026-10-07T00:00:00Z",
    "allowed_intents": ["it_api_timeout"],
    "allowed_route_keys": ["it.api_timeout.manual_lookup"]
  },
  "headers_template": {
    "Authorization": "Bearer {{intent_routing_api_key}}",
    "X-Key-Id": "key_live_012345",
    "X-App-Id": "dify-platform",
    "X-Service-Id": "it-helpdesk",
    "X-Request-Id": "{{workflow_run_id}}",
    "Content-Type": "application/json"
  },
  "body_template": {
    "query": "{{user_query}}",
    "channel": "chat",
    "user_context": {
      "workflow_run_id": "{{workflow_run_id}}"
    }
  },
  "dify_variable_mapping": [
    {
      "field": "Authorization",
      "source": "Secret variable intent_routing_api_key"
    },
    {
      "field": "X-Key-Id",
      "source": "Secret or environment variable intent_routing_key_id"
    },
    {
      "field": "X-App-Id",
      "source": "Literal approved app_id"
    },
    {
      "field": "X-Service-Id",
      "source": "Workflow variable service_id"
    },
    {
      "field": "X-Request-Id",
      "source": "workflow_run_id"
    }
  ],
  "checklist": [
    "Dify secret variable masks intent_routing_api_key.",
    "Timeout is 8 seconds.",
    "408, 5xx, and timeout branches use fallback or human handoff without automatic retry loops.",
    "Downstream nodes preserve trace_id, request_id, route_key, and release_version."
  ],
  "docs": [
    "docs/integrations/dify-http-request-node.md",
    "docs/integrations/dify-handoff-checklist.md",
    "docs/api/openapi-runtime-examples.md"
  ],
  "warnings": []
}
```

Rules:

- The endpoint never returns the raw API key secret.
- `key_id` is optional; if omitted, response returns endpoint/body/header template and active release status without key-specific metadata.
- If `key_id` is supplied, it must belong to the same `{service_id}` and `environment`.
- The endpoint is read-only guidance, not a runtime proxy.
- The endpoint should audit only explicit bundle generation/export actions, not every page read, unless security review requires read audit for key metadata.

### Optional Sample Runtime Validation Endpoint

Recommended baseline: do not call `/v1/intent-route` from the browser in C-3.

Reason:

- Browser sample calls would keep the raw API key secret in frontend memory beyond the one-time display path.
- They would mix Admin UI session-cookie auth and runtime Bearer auth in one browser workflow.
- They add CORS, logging, and accidental-secret-copy risk without being required to prove the setup contract.

If product later requires in-console validation, use a server-side metadata preflight endpoint first:

- `POST /admin/v1/services/{service_id}/runtime-setup:validate`

Request:

```json
{
  "environment": "prod",
  "key_id": "key_live_012345",
  "expected_intent_id": "it_api_timeout",
  "expected_route_key": "it.api_timeout.manual_lookup"
}
```

Response:

```json
{
  "service_id": "it-helpdesk",
  "environment": "prod",
  "key_id": "key_live_012345",
  "active_release_found": true,
  "key_active": true,
  "key_environment_matches": true,
  "key_app_id": "dify-platform",
  "intent_allowed": true,
  "route_key_allowed": true,
  "result": "pass",
  "warnings": []
}
```

Rules:

- This endpoint must not accept or return `api_key`.
- This endpoint does not exercise semantic routing for a raw user query.
- This endpoint validates metadata readiness only.
- A true runtime smoke stays in docs/scripts/manual QA until a separate ADR approves browser/server-driven runtime validation.

### Authorization Rules

C-3 baseline authorization:

- All Admin C-3 endpoints require authenticated session context from `irt_admin_session`.
- Normal browser UI requests must use Umi `request`; they must not send:
  - `X-Admin-Token`
  - `X-Actor-Id`
  - `X-Actor-Roles`
  - `X-Service-Scope`
- API-key lifecycle create/list/revoke requires global `system_admin` in the C-3 baseline.
- Service-scoped endpoints must check the requested `{service_id}` exists.
- Service-scoped revoke must check the key belongs to the requested `{service_id}`.
- Runtime setup guidance with key inventory metadata requires `system_admin` in the C-3 baseline.
- Runtime logs remain readable by `system_admin`, `service_operator`, and `auditor` per existing `_require_runtime_log_access`.
- Runtime metrics remain readable by `system_admin` and `service_operator`.
- Audit logs remain readable by `system_admin` and `auditor`.
- Future delegation to `service_owner` or `service_operator` for key lifecycle requires a separate approved decision.

Runtime API authorization:

- `/v1/intent-route` continues to use Bearer API key auth, not `irt_admin_session`.
- Runtime request must include matching `X-Key-Id`, `X-App-Id`, and `X-Service-Id`.
- Runtime environment must match `INTENT_ROUTING_ENVIRONMENT` and key `environment`.
- A key for Service A cannot call Service B.
- A key for app A cannot be used as app B.
- A revoked, expired, disabled, wrong-secret, or wrong-environment key returns authentication failure.
- A key that authenticates but attempts a disallowed route/intent must not execute the route; existing engine behavior returns `decision=unauthorized` for forbidden candidate scope.

### Audit Events

Required C-3 audit events:

- `api_key.created`
  - `actor_id`: authenticated Admin session actor.
  - `service_id`: key Service.
  - `target_type`: `api_key`.
  - `target_id`: `key_id`.
  - `before_state`: `null`.
  - `after_state`: key metadata with `"api_key": "REDACTED"` or no `api_key` field.
- `api_key.revoked`
  - `actor_id`: authenticated Admin session actor.
  - `service_id`: key Service.
  - `target_type`: `api_key`.
  - `target_id`: `key_id`.
  - `before_state`: previous key metadata with no raw secret.
  - `after_state`: revoked key metadata with no raw secret.
- `runtime_setup.guidance_generated` only if C-3 adds an explicit "copy/export setup bundle" action.
  - `target_type`: `runtime_setup`.
  - `target_id`: `{service_id}:{environment}:{app_id}:{key_id_or_none}`.
  - `after_state`: runtime endpoint, selected key metadata, active release metadata, docs references, and checklist status, with no raw secret.
- `runtime_setup.validation_checked` only if the optional metadata preflight endpoint is approved.
  - `target_type`: `runtime_setup_validation`.
  - `target_id`: `{service_id}:{environment}:{key_id}`.
  - `after_state`: pass/fail booleans and warnings, with no raw secret and no raw query.

Existing evidence that remains part of C-3:

- Runtime calls write `runtime_logs` with `query_masked` and trace fields.
- Raw query decrypt remains governed and audited through existing Phase 2 paths.
- Audit Logs are append-only; Admin UI must not expose edit/delete controls.

### Error Cases

| Case | Expected status/result | Error code/result | Notes |
| --- | --- | --- | --- |
| Missing/invalid `irt_admin_session` cookie for Admin endpoint | 401 | `AUTHENTICATION_FAILED` | Browser cannot fall back to trusted headers |
| Trusted headers without session for Admin C-3 endpoints | 401 | `AUTHENTICATION_FAILED` | Preserve `/me/services` contract |
| Non-`system_admin` creates/revokes key | 403 | `SERVICE_SCOPE_DENIED` | C-3 baseline |
| No selected/accessible Service in UI | UI blocked | n/a | Show AdminSessionRequired or Services guidance |
| Service missing | 404 | existing not-found envelope | Do not leak key inventory |
| Key missing | 404 | existing not-found envelope | Revoke/detail |
| Key belongs to another Service | 404 or 403 | `SERVICE_SCOPE_DENIED` preferred | Avoid cross-Service key disclosure |
| Candidate source has no active release | 422 for create | `INVALID_REQUEST` | Require active release for runtime-scoped key |
| `allowed_intents` includes unknown candidate | 422 | `INVALID_REQUEST` | Reject manual/internal ID entry |
| `allowed_route_keys` includes unknown candidate | 422 | `INVALID_REQUEST` | Reject manual/internal ID entry |
| `environment` does not match selected Service environment | 422 | `INVALID_REQUEST` | Baseline single environment per Service |
| `expires_in_days` outside policy | 422 | validation error | Prod default 90, max 180 recommended unless exception policy exists |
| Duplicate active key with same service/environment/app/scope | 201 or 409 | decision needed | Recommended: allow multiple active keys for rotation; no uniqueness constraint |
| Revoke already revoked key | 200 idempotent or 409 | decision needed | Recommended: idempotent 200 with current revoked metadata |
| Runtime wrong service/app/key | 401/403 | `AUTHENTICATION_FAILED` or `SERVICE_SCOPE_DENIED` | Existing runtime auth contract |
| Runtime disallowed candidate route | HTTP 200 | `decision=unauthorized` | Existing engine behavior |
| Runtime active release missing | 404 | `ACTIVE_RELEASE_NOT_FOUND` | Existing runtime behavior |

## DB And Schema Impact

### Existing Schema Sufficiency

Existing `api_keys` schema is sufficient for the C-3 baseline if candidate validation is enforced at API-time:

- `key_id`
- `key_hash`
- `key_fingerprint`
- `environment`
- `app_id`
- `service_id`
- `allowed_intents`
- `allowed_route_keys`
- `status`
- `expires_at`
- `revoked_at`
- `created_by`
- `created_at`

No raw secret column exists. That matches the PRD rule that API-key raw secrets must not be stored.

Existing `runtime_logs` schema is sufficient for C-3 evidence:

- `trace_id`
- `request_id`
- `app_id`
- `service_id`
- `release_version`
- `policy_version`
- `intent_catalog_version`
- `decision`
- `intent_id`
- `route_key`
- `error_code`
- `http_status`
- `latency_ms`
- `query_masked`
- encrypted raw query fields

Existing `audit_logs` schema is sufficient for append-only C-3 evidence:

- `event_type`
- `actor_id`
- `service_id`
- `trace_id`
- `target_type`
- `target_id`
- `before_state`
- `after_state`
- `created_at`

### Migration Recommendation

Baseline C-3 can proceed without a required migration if the team accepts API-level validation.

Recommended optional hardening migration before production:

- Add `ck_api_keys_status` check constraint:

```sql
status in ('active', 'revoked', 'expired')
```

- Add `ix_api_keys_service_environment_status_created_at`:

```text
(service_id, environment, status, created_at desc, key_id)
```

- Add `ix_api_keys_fingerprint` if operators frequently search by fingerprint.
- Add `ix_audit_logs_service_created_at` if append-only evidence review becomes slow.

Do not add a table for `allowed_intents` and `allowed_route_keys` in C-3 baseline. Those values are release snapshot scope, not a stable FK to current draft Intent rows.

Create a migration only if one of these becomes mandatory:

- DB-level status constraints are required before implementation.
- API-key inventory performance must be proven at scale.
- per-key rotation window metadata is required outside audit logs.
- exception approvals for >180-day keys must be persisted.
- key scope must bind to a specific `release_version`.
- environment-specific Service records replace the current single `services.environment` model.

### Local Verification Risk From C-1

Carry this risk into C-3:

- C-1 backend integration verification skipped locally when `TEST_DATABASE_URL` was not configured.
- C-1 local stack script failed because of an Alembic revision mismatch.
- `scripts/run_local_dev_stack.sh` runs `uv run alembic upgrade head`, so C-3 manual browser QA can be blocked until the local DB revision mismatch is repaired.
- C-3 implementation must include a preflight task:
  - fix/reset the local dev DB revision state before manual QA, or
  - record backend integration/manual stack QA as unverified with exact commands and failure output.

## Admin UI Screen And Flow

### Recommended UI Direction

Recommended C-3 UI: keep `/api-keys` as the primary runtime setup workspace, and add a compact next-step/runtime setup handoff panel to `/services` after C-2 is implemented.

Why:

- `/services` is already the C-1 entry point and future C-2 membership panel location.
- Putting all C-3 forms inside `/services` would make it too dense.
- The current `/api-keys` page already uses selected-Service context and candidate selectors.
- `/api-keys` can become "Runtime Setup" without losing the existing API-key inventory route.
- The ServiceScopeBar already keeps selected Service visible across the app.

UI shape:

- `/services`
  - Keep C-1 create/select Service.
  - Future C-2 membership panel remains there.
  - Add C-3 next-step panel only after C-2/contract approval:
    - selected Service
    - environment
    - active release readiness
    - link/button to `/api-keys`
    - no key creation controls in this panel.
- `/api-keys`
  - Primary C-3 workspace.
  - Rename visible page title to `Runtime Setup` or keep `API Keys` with a `Runtime setup` panel.
  - Show selected Service, environment, active release status, and known scope candidates.
  - Create scoped key with candidate multi-selects.
  - Show raw secret once.
  - Show inventory with key id, fingerprint, app, status, expiry, and scope counts/details.
  - Provide Dify/client setup guidance from the backend guidance contract.
  - Revoke with `ConfirmActionButton`.
- `/runtime-logs`
  - Keep masked `query_masked` table and drawer.
  - Do not expose raw query in baseline C-3.
- `/audit-logs`
  - Keep append-only evidence wording.
  - Do not add edit/delete controls.

### UI Alternatives

Option A: attach full C-3 runtime setup panel to `/services`.

- Pros: one onboarding page after Service creation and membership.
- Cons: `/services` becomes dense; key lifecycle, Dify guidance, inventory, and C-2 membership compete for space.
- Impact: modifies existing Services page heavily.

Option B: keep `/api-keys` as selected-Service runtime setup workspace plus `/services` next-step panel.

- Pros: uses existing route and code, keeps Services page focused, preserves selected Service context, easiest migration.
- Cons: user moves to another page for C-3.
- Impact: refactor/harden existing `/api-keys` page and add a small `/services` link panel.
- Recommended.

Option C: create `/services/:serviceId/runtime-setup`.

- Pros: clean deep links and future page ownership.
- Cons: more routing and direct URL validation; must still derive service access from `/me/services`; duplicates existing `/api-keys`.
- Impact: new route/page, more tests, likely later migration from `/api-keys`.

### C-1 To C-2 To C-3 Flow

1. `system_admin` logs in with `irt_admin_session`.
2. `system_admin` opens `/services`.
3. `system_admin` creates or selects a Service.
4. Admin UI refreshes `/me/services`.
5. C-2 baseline: `system_admin` assigns Service roles inside selected-Service membership panel.
6. `service_developer` configures Intents, examples, policy/catalog versions, and test runs for the assigned Service.
7. `system_admin` creates and activates a Release.
8. `system_admin` opens `/api-keys` for the selected Service.
9. UI loads active-release intent/route candidates.
10. `system_admin` creates a scoped API key for environment, app_id, allowed intents, and allowed route keys.
11. UI shows the raw secret once and clears it after navigation/refresh/selected-Service change.
12. UI shows inventory without raw secret.
13. UI shows Dify/client setup guidance using key id, app id, service id, endpoint, headers, body, timeout, branch checklist, and docs links.
14. Client/Dify calls `/v1/intent-route`.
15. Operator/auditor reviews masked Runtime Logs and append-only Audit Logs.
16. Wrong service/key/scope failures are traced by runtime errors or unauthorized decisions.

## Future Implementation File Structure

Backend:

- Modify: `src/intent_routing/api/admin.py`
  - Add Service-scoped API-key request/response endpoint variants.
  - Add runtime setup guidance response models.
  - Add optional metadata validation response models only if approved.
  - Add candidate validation for allowed intents/route keys.
  - Add Service/key ownership checks on revoke.
- Modify: `src/intent_routing/db/repositories.py`
  - Add `list_api_keys_for_service` only if the existing `list_api_keys` cannot express the Service-scoped path clearly.
  - Add `get_api_key_for_service`.
  - Keep raw secret out of repository return values.
- Modify only if hardening migration is approved: `src/intent_routing/db/models.py`
  - Add API-key check/index declarations matching the Alembic migration.
- Add migration only if approved:
  - `migrations/versions/<revision>_harden_api_key_inventory_indexes.py`

Frontend:

- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
  - Add Service-scoped API key request types if they differ from current global types.
  - Add `RuntimeSetupGuidance`.
  - Add `RuntimeSetupValidationResult` only if optional validation is approved.
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Add `createServiceApiKey`.
  - Add `listServiceApiKeys`.
  - Add `revokeServiceApiKey`.
  - Add `fetchRuntimeSetupGuidance`.
  - Add `validateRuntimeSetup` only if approved.
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
  - Verify paths, methods, payloads, and no trusted headers.
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
  - Add `canManageRuntimeSetup` and `canReadRuntimeEvidence` if the UI needs clearer role gates than `canManageApiKeys`.
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
  - Prove C-3 role helpers use server-derived roles only.
- Create: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts`
  - Extract payload normalization, candidate validation, generated guidance display helpers, and secret-clearing logic from React.
- Create: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`
  - Test helper behavior.
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
  - Switch to Service-scoped endpoints.
  - Add backend guidance panel.
  - Clear one-time secret on service/environment/key context changes.
  - Keep inventory raw-secret-free.
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
  - Add compact C-3 next-step panel only after C-2/contract approval.
- Modify only if route decision changes:
  - `frontend/intent-routing-console/config/config.ts`
  - `frontend/intent-routing-console/src/components/AdminShell.tsx`

Docs/tests:

- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
  - Mark C-3 contract and future implementation status accurately.
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
  - Add C-3 runtime setup/API-key scope rules.
- Modify: `docs/api/admin-workflow-candidate-contracts.md`
  - Update API-key inventory wording if Service-scoped endpoints are added.
- Create: `docs/api/admin-runtime-setup-contracts.md`
  - Document C-3 guidance and optional validation contracts.
- Modify: `docs/integrations/dify-http-request-node.md`
  - Link Admin UI guidance once implemented.
- Modify: `docs/integrations/dify-handoff-checklist.md`
  - Add Admin UI evidence checklist.
- Create accepted C-3 ADR from the approved decision.
- Modify: `tests/unit/test_admin_ui_handbook_docs_contract.py`
  - Add C-3 wording contract checks.
- Add: `tests/unit/test_admin_runtime_setup_contract_docs.py`
  - Require C-3 API contract doc and ADR linkage.

## TDD Plan

### Task 0: Approved Decision Baseline

- [x] Confirm the ADR path decision in the Human Decision Protocol section.
- [x] Confirm the UI placement decision.
- [x] Confirm the sample runtime validation decision.
- [x] Confirm that the optional API-key DB hardening migration is out of scope for C-3 baseline.
- [ ] Confirm whether to repair local Alembic/dev DB before C-3 manual browser QA.

### Task 1: Backend API Contract Tests

**Files:**

- Modify: `tests/integration/test_admin_api_key_inventory_flow.py`
- Modify: `tests/integration/test_admin_catalog_api.py`
- Add: `tests/integration/test_admin_runtime_setup_api.py`

- [ ] Add tests for Service-scoped key lifecycle:
  - `GET /admin/v1/services/{service_id}/api-keys` returns inventory without `api_key`.
  - `POST /admin/v1/services/{service_id}/api-keys` returns `api_key` once.
  - `POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke` revokes only a key belonging to that Service.
  - `POST /admin/v1/services/{other_service_id}/api-keys/{key_id}:revoke` fails.
- [ ] Add tests for candidate validation:
  - create with released-catalog candidates succeeds.
  - create with unknown `allowed_intents` fails.
  - create with unknown `allowed_route_keys` fails.
  - create with no active release fails if C-3 baseline requires active release.
- [ ] Add tests for guidance endpoint:
  - response includes endpoint, headers template, body template, active release, key metadata, Dify variable mapping, docs links, and checklist.
  - response excludes raw secret.
  - key metadata is returned only when key belongs to selected Service.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_api_key_inventory_flow.py tests/integration/test_admin_runtime_setup_api.py -q
```

Expected before implementation: fails for new C-3 Service-scoped/guidance endpoints.

### Task 2: API-Key Security Unit Tests

**Files:**

- Modify: `tests/unit/test_api_keys.py`

- [ ] Add unit tests proving `check_scope` denies mismatched `app_id`.
- [ ] Add unit tests proving `check_scope` denies disallowed `intent_id`.
- [ ] Add unit tests proving `check_scope` denies disallowed `route_key`.
- [ ] Add unit tests proving empty allowed lists mean no additional intent/route restriction within matching app/service.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_api_keys.py -q
```

Expected: pass after tests and any required implementation alignment.

### Task 3: Runtime Integration Tests

**Files:**

- Modify: `tests/integration/test_runtime_api.py`

- [ ] Add or confirm tests for:
  - key from Service A cannot call Service B.
  - key for app A cannot call app B.
  - key with allowed route A returns `decision=unauthorized` for route B.
  - key with allowed intent A returns `decision=unauthorized` for intent B.
  - revoked key returns authentication failure.
  - runtime failure logs include `query_masked` and never return raw query in Admin masked endpoints.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_runtime_api.py -q
```

Expected: pass or skip only if local integration DB is unavailable. If skipped, record exact skip reason.

### Task 4: Repository And Migration Tests

**Files:**

- Modify if needed: `tests/unit/test_account_auth_schema_contract.py`
- Modify if needed: `tests/integration/test_admin_api_key_inventory_flow.py`
- Add migration tests only if migration is approved.

- [ ] If no migration is selected, add a docs/test assertion explaining existing schema sufficiency.
- [ ] If migration is selected, add tests/assertions for:
  - `ck_api_keys_status`.
  - `ix_api_keys_service_environment_status_created_at`.
  - no raw secret column exists.
  - inventory order remains newest first.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_account_auth_schema_contract.py tests/integration/test_admin_api_key_inventory_flow.py -q
```

Expected: pass after migration/schema work, or pass with docs-only existing-schema assertion if no migration.

### Task 5: Frontend Service Wrapper Tests

**Files:**

- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`

- [ ] Add failing tests for:
  - `listServiceApiKeys('svc/admin', { environment: 'prod' })`
  - `createServiceApiKey('svc/admin', payload)`
  - `revokeServiceApiKey('svc/admin', 'key/a')`
  - `fetchRuntimeSetupGuidance('svc/admin', params)`
  - optional `validateRuntimeSetup` only if approved.
- [ ] Assert wrappers call Umi `request` with encoded Service/key IDs.
- [ ] Assert wrappers do not pass `headers` containing trusted Admin headers.

Expected wrapper paths:

```text
GET /services/svc%2Fadmin/api-keys
POST /services/svc%2Fadmin/api-keys
POST /services/svc%2Fadmin/api-keys/key%2Fa:revoke
GET /services/svc%2Fadmin/runtime-setup
```

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts
```

Expected before implementation: fails because new wrappers do not exist.

### Task 6: Admin Session Role Helper Tests

**Files:**

- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`

- [ ] Add `canManageRuntimeSetup`.
- [ ] Add `canReadRuntimeEvidence` only if page-level gates need it.
- [ ] Prove `system_admin` can manage runtime setup/API keys.
- [ ] Prove service-scoped roles cannot create/revoke API keys in C-3 baseline.
- [ ] Prove `service_operator`/`auditor` can still read their existing evidence pages only through server-derived selected Service roles.
- [ ] Prove helpers ignore legacy/trusted header values.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/models/adminSession.test.ts
```

Expected before implementation: fails because new helpers do not exist.

### Task 7: Page/Form Helper Tests

**Files:**

- Create: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`
- Create: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts`

- [ ] Test API-key payload normalization:
  - trims `app_id`.
  - uses selected Service environment.
  - emits candidate-selected intents/routes only.
  - rejects values not present in candidate list.
  - applies default `expires_in_days=90`.
  - rejects prod expiry greater than 180 days unless an exception contract is approved.
- [ ] Test one-time secret state behavior helpers:
  - clears secret on selected-Service change.
  - clears secret on explicit dismiss.
  - does not copy raw secret into inventory rows.
- [ ] Test guidance helpers:
  - render `Authorization` as a Dify secret-variable placeholder.
  - include `X-Key-Id`, `X-App-Id`, `X-Service-Id`, `X-Request-Id`.
  - include body `query` and `user_context.workflow_run_id`.
  - include timeout 8 seconds.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/pages/ApiKeys/runtimeSetup.test.ts
```

Expected before implementation: fails because helper file does not exist.

### Task 8: Runtime Setup UI

**Files:**

- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
- Modify only if route decision changes: `frontend/intent-routing-console/config/config.ts`
- Modify only if route decision changes: `frontend/intent-routing-console/src/components/AdminShell.tsx`

- [ ] Switch `/api-keys` to Service-scoped wrapper calls.
- [ ] Keep selected Service and environment from `adminSession`/`ServiceScopeBar`.
- [ ] Load `source=released_catalog` scope candidates.
- [ ] Disable create when there is no active-release candidate source.
- [ ] Show raw secret only in the create success alert.
- [ ] Clear raw secret on selected-Service change and page remount.
- [ ] Show inventory without raw secret.
- [ ] Add Dify/client guidance panel from `fetchRuntimeSetupGuidance`.
- [ ] Use `ConfirmActionButton` for revoke.
- [ ] Add compact `/services` next-step panel only if UI option B is approved.
- [ ] Do not add React Query, axios, fake server pagination, fake live polling, or invented workflow states.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/ApiKeys/runtimeSetup.test.ts
```

Expected after implementation: pass.

### Task 9: Docs Contract Tests

**Files:**

- Modify: `tests/unit/test_admin_ui_handbook_docs_contract.py`
- Add: `tests/unit/test_admin_runtime_setup_contract_docs.py`
- Create: `docs/api/admin-runtime-setup-contracts.md`
- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Modify: `docs/integrations/dify-http-request-node.md`
- Modify: `docs/integrations/dify-handoff-checklist.md`

- [ ] Require docs to state:
  - one-time raw API-key secret display.
  - inventory excludes raw secret.
  - allowed intents/routes come from candidates.
  - browser Admin UI requests use `irt_admin_session`, not trusted headers.
  - Runtime Logs show `query_masked`.
  - Audit Logs remain append-only.
  - sample runtime validation baseline is checklist/docs unless approved otherwise.
  - local Alembic/DB verification risk is carried forward.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_workflow_candidate_contract_docs.py -q
```

Expected after docs update: pass.

### Task 10: ADR

**Files:**

- Create or modify ADR path selected by Human Decision Protocol.

- [ ] If recommended option is approved, create:
  - `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`
- [ ] Include:
  - runtime/client API-key scope.
  - Service-scoped Admin API lifecycle endpoints.
  - raw secret one-time display.
  - candidate-selected allowed intents/routes.
  - Dify/client guidance contract.
  - no browser trusted headers.
  - no browser runtime sample call in baseline.
  - masked runtime logs.
  - append-only audit evidence.
  - local validation risk.
- [ ] Verify ADR has Status, Context, Decision, Alternatives, Consequences, Implementation Notes, Verification, and Rollback/Revisit Conditions.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "Runtime Integration|API key scope|query_masked|append-only|trusted headers" docs/adr docs/api docs/AdminUI_Handbook/v04
```

Expected after ADR/docs work: matches only accepted documentation text, not implementation shortcuts.

### Task 11: Final Verification For Future C-3 Implementation

Backend:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_api_keys.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py -q
uv run pytest tests/integration/test_admin_api_key_inventory_flow.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_runtime_api.py tests/integration/test_trace_audit_logs.py -q
```

Frontend:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/ApiKeys/runtimeSetup.test.ts
corepack pnpm typecheck
```

Docs:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_workflow_candidate_contract_docs.py -q
```

Forbidden-pattern scan:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/ApiKeys frontend/intent-routing-console/src/pages/Services frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/models/adminSession.ts frontend/intent-routing-console/config/config.ts
```

Expected: no frontend implementation matches. Documentation references to forbidden headers are allowed only when explicitly saying normal browser Admin UI must not use them. Runtime client guidance may include `Authorization: Bearer` only as Dify/client setup text, never as Admin UI request auth.

Local stack:

```bash
cd /home/haua/workspace/AiIntentRouting
./scripts/run_local_dev_stack.sh
```

Expected: pass only after the known local Alembic/dev DB mismatch is resolved.

## Security And Authorization Validation

C-3 cannot be accepted unless tests prove all of these:

- API-key raw secret is generated with at least 256-bit randomness.
- API-key raw secret is not persisted in DB.
- API-key raw secret is not present in inventory responses.
- API-key raw secret is not present in revoke responses.
- API-key raw secret is not present in audit log state.
- API-key raw secret is shown once in the UI and cleared from page state on navigation/refresh/selected-Service change.
- API-key create scope uses selected Service, environment, app_id, allowed intents, and allowed route keys.
- Allowed intents and route keys come from candidate endpoints.
- Manual internal ID entry is not used for scope selection.
- Key for Service A cannot call Service B.
- Key for app A cannot call app B.
- Key for route A cannot execute route B.
- Key for intent A cannot execute intent B.
- Revoked/expired/wrong-environment key cannot authenticate.
- User without accessible Service cannot open runtime setup.
- Non-`system_admin` cannot create/revoke API keys in C-3 baseline.
- Browser Admin UI requests use `irt_admin_session` cookie and Umi `request`.
- Browser Admin UI requests do not send trusted Admin headers.
- Runtime Logs show `query_masked` by default.
- Runtime Log list/detail endpoints never return raw query fields.
- Audit Logs remain append-only evidence.

## Manual QA Scenarios

Prerequisites:

- Local stack starts successfully, or backend/API verification runs against a configured local test DB with `TEST_DATABASE_URL`.
- Known accounts exist:
  - one `system_admin`.
  - one user with no Service access.
  - later C-2 users if role-specific read-path QA is included.
- A selected Service has:
  - active Intents.
  - approved examples.
  - policy/catalog versions.
  - a passing test run.
  - an active Release for the Service environment.

Scenario 1: `system_admin` creates scoped API key.

1. Log in as `system_admin`.
2. Open `/services`.
3. Select Service `c3-helpdesk`.
4. Confirm Service environment is shown.
5. Open `/api-keys`.
6. Confirm candidates load from active release.
7. Enter `app_id=dify-platform`.
8. Select allowed intent(s) from candidate selector.
9. Select allowed route key(s) from candidate selector.
10. Create API key.
11. Confirm raw secret appears once.
12. Copy key id and secret for manual Dify/client setup.

Scenario 2: secret one-time display and inventory safety.

1. Refresh `/api-keys`.
2. Confirm raw secret is no longer visible.
3. Confirm inventory shows key id, fingerprint, app id, status, expiry, and scope.
4. Confirm inventory does not show `api_key` or `irt_...` secret.
5. Change selected Service and return.
6. Confirm raw secret remains unavailable.

Scenario 3: Dify/client setup guidance.

1. Open the runtime setup guidance panel.
2. Confirm it shows `/v1/intent-route`.
3. Confirm headers include placeholders:
   - `Authorization: Bearer {{intent_routing_api_key}}`
   - `X-Key-Id`
   - `X-App-Id`
   - `X-Service-Id`
   - `X-Request-Id`
4. Confirm body maps `query` and `user_context.workflow_run_id`.
5. Confirm timeout guidance is 8 seconds.
6. Confirm branch guidance covers confident, clarify, fallback, off_topic, risk, unauthorized, 401, 403, 422, 408, 5xx, and timeout.
7. Confirm guidance contains no raw secret unless it is the immediate one-time create success panel.

Scenario 4: allowed intent/route candidates.

1. Try to type a manual route key not present in candidates.
2. Confirm the UI prevents it.
3. If direct API is tested, post unknown `allowed_route_keys`.
4. Confirm backend rejects with validation error.

Scenario 5: wrong service/key/scope runtime failure.

1. Call `/v1/intent-route` with correct key and selected Service.
2. Confirm successful response or expected routing decision.
3. Call with same key but wrong `X-Service-Id`.
4. Confirm 403 scope failure.
5. Call with wrong `X-App-Id`.
6. Confirm 403 scope failure.
7. Call with revoked key.
8. Confirm 401 authentication failure.
9. Call with a query that maps to a route outside allowed route keys.
10. Confirm `decision=unauthorized` and no route execution.

Scenario 6: runtime logs and audit evidence.

1. Open `/runtime-logs`.
2. Confirm runtime entries show `query_masked`.
3. Confirm detail drawer does not expose raw query.
4. Open `/audit-logs`.
5. Confirm `api_key.created` exists with key id/fingerprint and no raw secret.
6. Revoke key from `/api-keys`.
7. Confirm `api_key.revoked` exists with before/after state and no raw secret.
8. Confirm Audit Logs table has no edit/delete controls.

Scenario 7: service-less or unauthorized user.

1. Log in as a user with no accessible Services.
2. Confirm `/api-keys` does not expose key inventory or create controls.
3. Attempt direct Admin API key lifecycle call.
4. Confirm 401 or 403.

## ADR Judgment

### Current Assessment

C-3 meets the ADR Trigger.

It affects:

- external runtime API contract.
- API-key authentication and authorization scope.
- Admin API contract.
- DB schema constraints/indexes if hardening is approved.
- Dify/client integration workflow.
- runtime evidence and audit evidence.
- core onboarding workflow.

Existing ADR coverage:

- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
  covers account login and Service-scoped Admin RBAC.
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
  covers the C-1/C-2/C-3 authorization-first onboarding model.
- `docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md`
  covers candidate/list endpoints, including intent-route candidates and API-key inventory.

Recommendation:

- Create a new C-3 ADR before implementation because C-3 crosses Admin UI, runtime API-key auth, Dify/client setup, runtime evidence, audit evidence, and optional DB hardening. Updating only the RBAC ADR would hide runtime-client security decisions inside an Admin-user authorization record.

### Human Decision Protocol: ADR Path

1. Related requirement/spec ID

- `docs/IntentRouting_PRD_v0.2_20260624.md`, sections `5.1 서비스 온보딩 흐름`, `5.3 Runtime API 흐름`, `9.1 호출 시스템 인증`, `9.2 API Key 정책`, `9.3 관리 사용자 권한`, `10.4 Runtime Log 필수 필드`, and `13. 성공 기준`
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md`
- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`, section `C-3: Runtime Integration And Operations`

2. Why this decision is needed now

- C-3 decides how scoped API keys are created, how runtime clients are configured, how secrets are displayed, how runtime scope failures behave, and how evidence is audited. Those decisions affect security and external client integration before implementation starts.

3. Plain explanation for beginners

- An ADR is the project's memory for important decisions. C-3 is not just a screen. It decides how real client systems like Dify get keys and call the runtime API. Future developers need one place that says what is allowed, what is forbidden, and why.

4. Options A/B/C

- A: Update existing ADRs only.
- B: Create a new C-3 Runtime Integration And API Key Scope ADR.
- C: Defer ADR changes until implementation starts.

5. Pros, cons, and impact scope

- A pros: fewer ADR files, keeps C-flow docs compact.
- A cons: runtime API-key and Dify/client decisions get scattered across RBAC and workflow-candidate ADRs.
- A impact: docs only, lower immediate overhead, higher future lookup cost.
- B pros: one clear record for API-key scope, runtime setup, one-time secret display, evidence, and validation boundaries.
- B cons: adds another ADR to maintain.
- B impact: docs first; implementation later follows the new ADR.
- C pros: fastest if implementation is not starting soon.
- C cons: weak audit trail for security/API/DB/client workflow decisions.
- C impact: leaves implementation dependent on this plan only.

6. Recommended option and why

- Recommended: B. C-3 crosses runtime client auth, Admin API contract, operational evidence, and Dify setup. A dedicated ADR is clearer than stretching the RBAC ADR.

7. Safe default if the user does not answer

- Current session: user approved the recommendation, so create the accepted C-3 ADR and proceed with C-3 implementation.
- Future session without this approval context: keep implementation paused, create the C-3 ADR as `Proposed`, and ask for approval before code changes.

8. Newly introduced project terms

- Runtime setup: the steps and configuration a client system needs to call `/v1/intent-route`.
- API-key scope: the service, environment, app, intents, and route keys a key is allowed to use.
- Fingerprint: a safe identifier derived from the secret that helps operators recognize a key without seeing the secret.
- One-time secret display: showing the API-key raw secret only in the create response and never again.
- Runtime evidence: traceable runtime logs that show masked query, decision, route, release, and errors.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

### Human Decision Protocol: Admin API Endpoint Shape

1. Related requirement/spec ID

- `docs/IntentRouting_PRD_v0.2_20260624.md`, sections `5.1 서비스 온보딩 흐름` and `9.2 API Key 정책`
- `docs/api/admin-workflow-candidate-contracts.md`, section `GET /admin/v1/api-keys`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`, sections `API Rules` and `Workflow candidate selectors`

2. Why this decision is needed now

- The current API-key endpoints are global. C-3 is selected-Service runtime setup. The team must decide whether to keep the global endpoints for UI writes or add Service-scoped endpoints before implementation.

3. Plain explanation for beginners

- If the URL contains the Service ID, the server can naturally check that the key belongs to that Service. If the Service ID is only in the body or query string, the UI and backend have more room to accidentally disagree.

4. Options A/B/C

- A: Keep only global `/admin/v1/api-keys` endpoints.
- B: Add Service-scoped `/admin/v1/services/{service_id}/api-keys` endpoints and keep global endpoints for transition.
- C: Add separate `/admin/v1/runtime-setup/api-keys` endpoints.

5. Pros, cons, and impact scope

- A pros: smallest backend change, existing UI wrappers already work.
- A cons: weaker selected-Service contract, create body still carries `service_id`.
- A impact: minimal API changes, more reliance on frontend discipline.
- B pros: strongest fit with existing Service-scoped Admin API, easier wrong-Service revoke denial, UI cannot post mismatched body service.
- B cons: adds endpoint variants and transition work.
- B impact: backend API, frontend wrappers, docs, tests.
- C pros: groups runtime setup concepts under one area.
- C cons: diverges from project `/services/{service_id}/...` route style.
- C impact: new API namespace and more docs.

6. Recommended option and why

- Recommended: B. It is the clearest contract for selected-Service C-3 while preserving current global endpoints for scripts and compatibility.

7. Safe default if the user does not answer

- Keep implementation paused. If implementation is later requested without a fresh decision, use B and add Service-scoped endpoints before changing the UI.

8. Newly introduced project terms

- Service-scoped endpoint: an API path where `{service_id}` is part of the URL.
- Transition endpoint: an older endpoint kept temporarily so existing scripts or tests do not break.
- Wrong-Service revoke: trying to revoke a key through a Service URL that does not own that key.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

### Human Decision Protocol: Admin UI Placement

1. Related requirement/spec ID

- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`, sections `C-1`, `C-2`, and `C-3`
- `docs/superpowers/plans/2026-07-08-admin-ui-c1-service-onboarding.md`
- `docs/superpowers/plans/2026-07-08-admin-ui-c2-service-membership-roles.md`
- `frontend/intent-routing-console/src/pages/Services/index.tsx`
- `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`

2. Why this decision is needed now

- C-3 can be placed in `/services`, `/api-keys`, or a new runtime setup route. The route choice affects page density, QA flow, and how C-1/C-2/C-3 handoffs are tested.

3. Plain explanation for beginners

- Users need a place to create a runtime key and see Dify setup instructions. We need to decide whether that belongs on the Service page, the existing API Keys page, or a new page.

4. Options A/B/C

- A: Put full C-3 runtime setup inside `/services`.
- B: Use existing `/api-keys` as the selected-Service runtime setup page and add a small `/services` next-step panel.
- C: Create `/services/:serviceId/runtime-setup`.

5. Pros, cons, and impact scope

- A pros: all onboarding steps in one place.
- A cons: Services page becomes crowded with C-1 creation, C-2 membership, and C-3 runtime setup.
- A impact: large Services page change.
- B pros: uses existing route/code, keeps Services focused, keeps selected Service visible through ServiceScopeBar.
- B cons: one extra navigation step.
- B impact: moderate refactor of `/api-keys`, small `/services` panel.
- C pros: clean long-term deep link for one Service runtime setup.
- C cons: duplicates existing `/api-keys` and adds direct URL Service validation work.
- C impact: new route/page and broader routing tests.

6. Recommended option and why

- Recommended: B. It preserves the C-flow handoff while avoiding a crowded Services page and reuses the current `/api-keys` implementation.

7. Safe default if the user does not answer

- Keep implementation paused. If implementation is later requested without a fresh decision, use B.

8. Newly introduced project terms

- Runtime setup workspace: the main page where key creation, inventory, and client guidance live.
- Next-step panel: a small handoff panel that points users to the next C-flow screen.
- Deep link: a URL that directly opens a resource-specific setup page.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

### Human Decision Protocol: Runtime Sample Validation

1. Related requirement/spec ID

- `docs/IntentRouting_PRD_v0.2_20260624.md`, sections `5.3 Runtime API 흐름`, `6.8 내부 오류 응답 형식`, and `13. 성공 기준`
- `docs/integrations/dify-http-request-node.md`
- `docs/integrations/dify-handoff-checklist.md`
- `docs/api/openapi-runtime-examples.md`

2. Why this decision is needed now

- C-3 must decide whether the Admin UI should make a sample `/v1/intent-route` runtime call from the browser, provide checklist/docs guidance only, or add a server-side preflight endpoint.

3. Plain explanation for beginners

- A browser sample call feels convenient, but it means the web page handles the raw API key secret. A checklist is safer but less automatic. A server-side preflight can check metadata without using the raw secret.

4. Options A/B/C

- A: Checklist/docs guidance only for C-3 baseline.
- B: Browser calls `/v1/intent-route` using the one-time secret.
- C: Add server-side metadata preflight endpoint without raw secret or raw query.

5. Pros, cons, and impact scope

- A pros: safest baseline, reuses existing Dify docs/scripts, avoids browser secret lifetime and CORS issues.
- A cons: less convenient; user must run Dify/manual smoke outside the Admin UI.
- A impact: docs/UI guidance only.
- B pros: most convenient immediate confirmation.
- B cons: browser handles runtime Bearer secret, mixes Admin session and runtime auth, increases leak/CORS/logging risk.
- B impact: frontend/runtime security review and tests.
- C pros: validates readiness without raw secret and gives UI feedback.
- C cons: does not prove a real Dify runtime call; adds backend contract.
- C impact: backend endpoint, tests, audit event if accepted.

6. Recommended option and why

- Recommended: A for C-3 baseline. Add C as a later increment if operators need in-console readiness checks. Avoid B unless a future ADR explicitly accepts browser runtime calls.

7. Safe default if the user does not answer

- Keep implementation paused. If implementation is later requested without a fresh decision, use A and do not add browser runtime sample calls.

8. Newly introduced project terms

- Browser runtime call: frontend JavaScript directly calls `/v1/intent-route` with the runtime API key.
- Metadata preflight: a server-side Admin endpoint that checks key/release/scope readiness without executing a real user query.
- CORS: browser security rules controlling cross-origin HTTP calls.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

## Acceptance Criteria For Future C-3 Implementation

- `system_admin` can create a scoped API key from the selected Service.
- Key scope includes selected Service, environment, app_id, allowed intents, and allowed route keys.
- Allowed intents and route keys are selected from known candidates, not typed manually.
- Raw API-key secret is shown once and never returned in inventory, revoke, guidance, audit, or logs.
- API-key inventory shows key id, fingerprint, app, Service, environment, status, expiry, and scope metadata.
- Dify/client guidance shows endpoint, headers, body, timeout, variable mapping, decision branch checklist, and docs links.
- Admin UI does not call `/v1/intent-route` from the browser in the baseline.
- Runtime API rejects wrong service/app/key/environment/status/secret.
- Runtime route/intent scope cannot execute outside the key's allowed candidates.
- Runtime Logs show `query_masked` by default.
- Audit Logs remain append-only and record key lifecycle evidence.
- Normal Admin UI requests use `irt_admin_session` cookie and Umi `request`.
- Normal Admin UI requests do not send trusted Admin headers.
- React Query, axios, fake server pagination, fake live polling, and invented workflow states are not introduced.
- C-1/C-2/C-3 flow is documented and manually QA-able.
- Local DB/Alembic risk is resolved or explicitly reported as unverified with exact commands.

## Self-Review Checklist

- C-3 backend contract includes endpoint candidates, setup guidance endpoint decision, candidate contract, optional validation endpoint, schemas, authorization, audit events, and error cases.
- DB section explains existing schema sufficiency and optional migration triggers.
- Admin UI section compares `/services`, `/api-keys`, and `/services/:serviceId/runtime-setup`.
- TDD plan covers backend tests, frontend service wrapper tests, `adminSession` helper tests, page/form helper tests, docs contract tests, and runtime tests.
- Security section covers raw secret handling, cross-Service/scope denial, service-less access, browser trusted-header non-use, masked runtime logs, and append-only audit logs.
- Manual QA covers scoped key creation, one-time secret, Dify guidance, candidate selection, wrong scope runtime failure, runtime logs, and audit logs.
- ADR judgment follows the Human Decision Protocol and recommends a dedicated C-3 ADR.
- No implementation code is included in this session.
