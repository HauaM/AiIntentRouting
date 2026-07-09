# Admin Runtime Setup Contracts

This document defines the accepted C-3 runtime setup contract for Admin API and
Admin UI implementation. Optional validation remains future/not baseline unless
explicitly marked otherwise.

## Common Rules

- Base path: `/admin/v1`.
- Selected Service is the Service returned by `/me/services` and chosen in the
  Admin UI Service picker.
- Normal browser Admin UI requests use `irt_admin_session`, Umi `request`, and
  `withCredentials: true`.
- Normal browser Admin UI requests must not send `X-Admin-Token`.
- Normal browser Admin UI requests must not send `X-Actor-Id`.
- Normal browser Admin UI requests must not send `X-Actor-Roles`.
- Normal browser Admin UI requests must not send `X-Service-Scope`.
- Runtime clients do not use the Admin UI session cookie. They call
  `/v1/intent-route` with Bearer API-key authentication.
- The raw API key secret is shown only once in the create response.
- `api_key` raw secret is never present in inventory, revoke responses,
  runtime setup guidance, audit log state, runtime logs, or exported evidence.
- Key metadata may include `key_id`, `key_fingerprint`, `environment`,
  `app_id`, `service_id`, `allowed_intents`, `allowed_route_keys`, `status`,
  `expires_at`, `revoked_at`, `created_by`, and `created_at`.
- C-3 baseline key lifecycle create/list/revoke requires `system_admin`.
- Future delegation to `service_owner` or `service_operator` requires a
  separate approved decision.

The existing global `/admin/v1/api-keys` endpoints remain transitional for
scripts and backward compatibility. New Admin UI C-3 work should use the
Service-scoped endpoints in this document.

## Service-Scoped API Key Lifecycle

### GET /admin/v1/services/{service_id}/api-keys

Lists API key inventory for the selected Service without exposing the raw
secret.

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

Rules:

- `api_key` raw secret is never present in inventory.
- Response is scoped to `{service_id}`.
- `limit` is 1 to 100 and defaults to 50.

### POST /admin/v1/services/{service_id}/api-keys

Creates a runtime API key for the selected Service. The Service ID comes from
the path and must not be duplicated in the body.

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

Rules:

- `api_key` is present only in the create response.
- The secret must be generated with at least 256-bit randomness.
- The secret must be stored only as a hash/fingerprint, never plaintext.
- Audit state must omit `api_key` or record it only as `REDACTED`.
- UI state must clear the one-time secret on selected-Service change, refresh,
  navigation, logout, and successful revoke.
- Allowed scope must be validated against active-release candidates.

### POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke

Revokes an API key owned by the selected Service.

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

Rules:

- The key must belong to `{service_id}`.
- Revoke responses never return `api_key`.
- Revoke should be idempotent unless a later API decision chooses conflict
  semantics.

## Intent-Route Candidate Scope Contract

C-3 API key scope selectors use the existing candidate endpoint:

`GET /admin/v1/services/{service_id}/intent-route-candidates`

Query:

```json
{
  "source": "active_release",
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
    "source": "active_release"
  }
]
```

Rules:

- The C-3 baseline uses `source=active_release`.
- Admin UI selectors must not ask operators to type manual `intent_id` or
  `route_key` scope strings.
- Create must reject `allowed_intents` or `allowed_route_keys` not returned by
  the selected candidate source.
- If no active release exists, key creation must fail with an explicit active
  release requirement.

## GET /admin/v1/services/{service_id}/runtime-setup

Returns read-only Dify/client setup guidance for the selected Service. This
endpoint is guidance, not a runtime proxy.

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
    "docs/integrations/dify-branching-playbook.md",
    "docs/api/openapi-runtime-examples.md"
  ],
  "warnings": []
}
```

Rules:

- The endpoint never returns the raw API key secret.
- `key_id` is optional. If omitted, return endpoint/body/header template and
  active release status without key-specific metadata.
- If `key_id` is supplied, `selected_key` contains key metadata only. The key
  must belong to the same `{service_id}` and `environment`.
- Page reads do not need audit events unless security review requires read
  audit for key metadata.
- Explicit copy/export bundle actions may write
  `runtime_setup.guidance_generated`.

## Optional Metadata-Only Validation Endpoint

`POST /admin/v1/services/{service_id}/runtime-setup:validate` is future/not baseline.
C-3 baseline uses checklist/docs guidance only and does not make a browser
runtime sample call with the one-time secret.

Potential request:

```json
{
  "environment": "prod",
  "key_id": "key_live_012345",
  "expected_intent_id": "it_api_timeout",
  "expected_route_key": "it.api_timeout.manual_lookup"
}
```

Potential response:

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

Rules if later approved:

- Must not accept or return `api_key`.
- Must not execute semantic routing for a raw user query.
- Must validate metadata readiness only.
- May write `runtime_setup.validation_checked`.

## Dify And Client Setup Fields

Runtime clients call:

```http
POST /v1/intent-route
Authorization: Bearer {{intent_routing_api_key}}
X-Key-Id: {{intent_routing_key_id}}
X-App-Id: dify-platform
X-Service-Id: {{service_id}}
X-Request-Id: {{workflow_run_id}}
Content-Type: application/json
```

Body:

```json
{
  "query": "{{user_query}}",
  "channel": "chat",
  "user_context": {
    "workflow_run_id": "{{workflow_run_id}}"
  }
}
```

The `query` body field maps to the client or Dify user input variable.

Timeout: 8 seconds.

Branch checklist:

- `confident`: route by `route_key` and preserve `trace_id`, `request_id`,
  `route_key`, and `release_version`.
- `clarify`: show `clarify_question` and candidate choices.
- `fallback`: return approved fallback or human handoff.
- `off_topic`: return the Service-scope message and stop Service-specific
  routing.
- `risk`: block or security-handoff with `trace_id`.
- `unauthorized`: do not execute a business route.
- `401`, `403`, and `422`: treat as configuration errors.
- `408, 5xx, and timeout`: use client fallback or human handoff with no
  automatic retry loop.

## Error Cases

| Case | Expected result | Code or note |
| --- | --- | --- |
| Missing or invalid `irt_admin_session` | 401 | `AUTHENTICATION_FAILED` |
| Trusted headers without session | 401 | Browser cannot fall back to trusted headers |
| Non-`system_admin` creates or revokes key | 403 | `SERVICE_SCOPE_DENIED` baseline |
| No selected or accessible Service in UI | UI blocked | Show session or Services guidance |
| Service missing | 404 | Do not leak key inventory |
| Key missing | 404 | Revoke/detail |
| Key belongs to another Service | 403 or 404 | Prefer no cross-Service disclosure |
| Candidate source has no active release | 422 | Active release required for scoped runtime setup |
| Unknown `allowed_intents` | 422 | Reject manual/internal ID entry |
| Unknown `allowed_route_keys` | 422 | Reject manual/internal ID entry |
| Invalid `environment` | 422 | Must match Service/environment policy |
| `expires_in_days` outside policy | 422 | Prod default 90, max 180 recommended |
| Duplicate active key with same scope | 201 | Allow rotation unless later policy changes |
| Already revoked key | 200 | Idempotent current revoked metadata recommended |
| Runtime wrong key/app/service/environment | 401 or 403 | Existing runtime auth contract |
| Runtime disallowed route/intent | HTTP 200 | `decision=unauthorized` |
| Runtime active release missing | 404 | `ACTIVE_RELEASE_NOT_FOUND` |

## Audit Events

Required C-3 audit events:

- `api_key.created`
  - Actor: authenticated Admin session actor.
  - Service: key `service_id`.
  - Target: `target_type=api_key`, `target_id=key_id`.
  - State: metadata only, with no raw secret.
- `api_key.revoked`
  - Actor: authenticated Admin session actor.
  - Service: key `service_id`.
  - Target: `target_type=api_key`, `target_id=key_id`.
  - State: previous and revoked metadata only, with no raw secret.

Conditional future events:

- `runtime_setup.guidance_generated`
  - Only if C-3 adds an explicit copy/export setup bundle action.
  - State includes runtime endpoint, selected key metadata, active release
    metadata, docs references, and checklist status, with no raw secret.
- `runtime_setup.validation_checked`
  - Only if the optional metadata preflight endpoint is approved.
  - State includes pass/fail booleans and warnings, with no raw secret and no
    raw query.

Existing evidence that remains part of C-3:

- Runtime calls write `runtime_logs` with `query_masked` and trace fields.
- Raw query decrypt remains governed and audited through Phase 2 paths.
- Audit Logs remain append-only evidence; Admin UI must not expose edit/delete
  controls.

## DB And Schema Impact

Baseline C-3 has no required migration. Existing schema is sufficient if
candidate scope is validated at API time:

- `api_keys` already stores `key_hash`, `key_fingerprint`, `environment`,
  `app_id`, `service_id`, `allowed_intents`, `allowed_route_keys`, `status`,
  `expires_at`, `revoked_at`, `created_by`, and `created_at`.
- `runtime_logs` already stores trace, request, app, Service, release, decision,
  route, error, latency, and `query_masked` fields.
- `audit_logs` already stores append-only actor, Service, target, before/after
  state, trace, and timestamp evidence.

Future optional hardening for later:

- Add an index on `api_keys(service_id, environment, app_id, status)`.
- Add a partial index for active, non-revoked keys if inventory or auth lookup
  performance requires it.
- Consider JSONB validation or check constraints for `allowed_intents` and
  `allowed_route_keys` if API-time validation is not enough.
- Do not add a separate scope table in the C-3 baseline because allowed intent
  and route values come from active release snapshots, not stable draft rows.
