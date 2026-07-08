# Admin Phase 2 Governed Workflow Contracts

These contracts define the server-side approval and permission model required
before Admin UI Phase 2 governed workflows are enabled.

## Common Rules

- Base path: `/admin/v1`.
- Authentication: `irt_admin_session` HttpOnly cookie.
- Authorization: server-derived admin context plus selected service roles.
- Every endpoint is scoped to `service_id`; cross-service access is denied.
- Request ids, release versions, trace ids, and export ids are opaque strings.
- Timestamps are UTC ISO 8601 strings.
- Responses use the existing error envelope for validation, authorization, and
  conflict failures.
- Pagination for request lists added later must use server-side filters and
  must not expose raw query text or secret-bearing fields.

## Resource And Action Model

Resource types:

- `intent`
- `example`
- `release`
- `runtime_log`
- `raw_query`
- `export`

Action names:

- `request`
- `approve`
- `reject`
- `activate`
- `rollback`
- `decrypt`
- `export`

Permission checks are expressed as `{resource_type}:{action}` within the
service scope. Implementations may map these names to roles, but API behavior
must remain stable for Admin UI clients and audit review.

Role literals used by these contracts are `service_developer`,
`service_owner`, `service_operator`, `auditor`, and `system_admin`.

## Approval Invariants

- author cannot approve own request.
- two-person raw query approval is required before a raw query view token can
  be issued.
- audit event required for every state transition.
- Rejected requests are terminal.
- Approved requests may be activated, token-issued, or exported only by the
  endpoint dedicated to that operation.
- Decision reason is required for reject and optional for approve.

## Status Transitions

| Workflow | Allowed transitions | Required audit events |
| --- | --- | --- |
| Publish request | `pending -> approved`, `pending -> rejected`, `approved -> activated`, `activated -> rolled_back` | `publish.requested`, `publish.approved`, `publish.rejected`, `release.activated`, `release.rolled_back` |
| Raw query view | `pending -> approved`, `pending -> rejected`, `approved -> token_issued`, `token_issued -> viewed`, `token_issued -> expired` | `raw_query.requested`, `raw_query.approved`, `raw_query.rejected`, `raw_query.token_issued`, `raw_query.viewed`, `raw_query.token_expired` |
| Export | synchronous `requested -> completed` or synchronous `requested -> rejected` in the same request | `export.requested`, `export.completed`, `export.rejected` |

## Security Rules

- masked-only export: export payloads contain masked values only.
- no API key secrets in responses, exports, audit events, evidence bundles, or
  logs.
- no raw query text in exports/evidence/logs.
- no encrypted DEKs/ciphertext/KEK material in responses, exports, audit
  events, evidence bundles, or logs.
- Raw query view tokens are time-limited, single-purpose credentials and are
  stored only as hashes.
- Evidence fields may include trace id, request id, actor id, approval state,
  reason, and timestamps, but not decrypted payloads.

## POST /admin/v1/services/{service_id}/publish-requests

Creates a governed publish request for catalog, example, or release changes.

| Request field | Required | Notes |
| --- | --- | --- |
| `resource_type` | yes | `intent`, `example`, or `release`. |
| `resource_id` | yes | Intent id, example id, or release candidate id. |
| `action` | yes | `request`, `activate`, or `rollback`. |
| `target_version` | no | Catalog, policy, or release version being proposed. |
| `reason` | yes | Operator-visible justification. |

Response: `PublishRequestResponse`.

| Response field | Notes |
| --- | --- |
| `request_id` | Opaque request id. |
| `service_id` | Requested Service scope. |
| `resource_type` | Governed resource type. |
| `resource_id` | Governed resource id. |
| `action` | Requested action. |
| `status` | `pending`. |
| `requested_by` | Session actor id. |
| `requested_at` | UTC timestamp. |
| `reason` | Stored request reason. |

Authorization: `service_developer`, `service_owner`, or `system_admin` with
`intent:request`, `example:request`, or `release:request`.

Audit event: `publish.requested`.

## POST /admin/v1/services/{service_id}/publish-requests/{request_id}:approve

Approves a pending publish request.

| Request field | Required | Notes |
| --- | --- | --- |
| `reason` | no | Approval note. |

Response: `PublishRequestResponse` with `status=approved`, `decided_by`, and
`decided_at`.

Authorization: `service_owner` or `system_admin` with
`{resource_type}:approve`; intent/example/release approvals map to the requested resource type. Request author is denied.

Audit event: `publish.approved`.

## POST /admin/v1/services/{service_id}/publish-requests/{request_id}:reject

Rejects a pending publish request.

| Request field | Required | Notes |
| --- | --- | --- |
| `reason` | yes | Rejection reason shown to the requester. |

Response: `PublishRequestResponse` with `status=rejected`, `decided_by`, and
`decided_at`.

Authorization: `service_owner` or `system_admin` with
`{resource_type}:reject`; intent/example/release approvals map to the requested resource type. Request author is denied.

Audit event: `publish.rejected`.

## POST /admin/v1/services/{service_id}/runtime-logs/{trace_id}/raw-query-view-requests

Creates a two-person approval request to view a raw query for a runtime trace.

| Request field | Required | Notes |
| --- | --- | --- |
| `reason` | yes | Incident, audit, or support reason. |
| `ticket_ref` | no | Safe ticket id or URL. |

Response: `RawQueryViewRequestResponse`.

| Response field | Notes |
| --- | --- |
| `request_id` | Opaque request id. |
| `service_id` | Requested Service scope. |
| `trace_id` | Runtime trace id. |
| `resource_type` | `raw_query`. |
| `action` | `decrypt`. |
| `status` | `pending`. |
| `requested_by` | Session actor id. |
| `requested_at` | UTC timestamp. |
| `reason` | Stored request reason. |

Authorization: `service_operator`, `auditor`, `service_owner`, or `system_admin`
with `raw_query:request`.

Audit event: `raw_query.requested`.

## POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:approve

Approves a pending raw query view request.

| Request field | Required | Notes |
| --- | --- | --- |
| `reason` | no | Approval note. |

Response: `RawQueryViewRequestResponse` with `status=approved`, `decided_by`,
and `decided_at`.

Authorization: `auditor`, `service_owner`, or `system_admin` with
`raw_query:approve`; request author is denied.

Audit event: `raw_query.approved`.

## POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:reject

Rejects a pending raw query view request.

| Request field | Required | Notes |
| --- | --- | --- |
| `reason` | yes | Rejection reason shown to the requester. |

Response: `RawQueryViewRequestResponse` with `status=rejected`, `decided_by`,
and `decided_at`.

Authorization: `auditor`, `service_owner`, or `system_admin` with
`raw_query:reject`; request author is denied.

Audit event: `raw_query.rejected`.

## POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:issue-token

Issues a short-lived token for an approved raw query view request.

| Request field | Required | Notes |
| --- | --- | --- |
| `ttl_seconds` | no | Defaults to 300; maximum 900. |

Response: `RawQueryTokenResponse`.

| Response field | Notes |
| --- | --- |
| `request_id` | Approved request id. |
| `token` | Returned once; stored only as a hash. |
| `expires_at` | UTC expiry timestamp. |

Authorization: requester or `system_admin` with `raw_query:decrypt`, after
two-person approval. Token issuance is denied for pending, rejected, expired,
or cross-service requests.

Audit event: `raw_query.token_issued`.

Token consumption happens through the existing
`POST /admin/v1/services/{service_id}/runtime-logs/{trace_id}:decrypt-raw-query`
endpoint, not through a new governed endpoint heading. The decrypt request must
include `raw_query_view_token`; token consumption writes `raw_query.viewed`, requires token hash/expiry/request/trace/service validation, and denies direct decrypt without an approved token in Phase 2.

## GET /admin/v1/services/{service_id}/releases/{release_version}/diff

Returns a release diff for approval review and rollback decisions.

Query:

- `compare_to`: optional release version; defaults to active release for the
  service environment.

Response: `ReleaseDiffResponse`.

| Response field | Notes |
| --- | --- |
| `service_id` | Requested Service scope. |
| `release_version` | Candidate release version. |
| `compare_to` | Baseline release version. |
| `policy_version_diff` | Policy version and threshold changes. |
| `catalog_version_diff` | Intent and example summary changes. |
| `model_version_diff` | Embedding or scoring model changes. |
| `test_run_diff` | Gate, risk, and pass-rate changes. |
| `rollback_target` | Safe rollback candidate, if available. |

Authorization: `service_developer`, `service_owner`, `auditor`, or `system_admin`
with `release:request` or `release:approve`.

Audit event: read-only diff access does not change state; implementations may
write `release.diff_viewed` for traceability.

## POST /admin/v1/services/{service_id}/exports

Creates a synchronous masked export for audit or operational review.

| Request field | Required | Notes |
| --- | --- | --- |
| `resource_type` | yes | `intent`, `example`, `release`, `runtime_log`, or `export`. |
| `format` | yes | `csv` or `jsonl`. |
| `filters` | no | Server-side filters; ignored fields are rejected. |
| `reason` | yes | Export justification. |

Response: `ExportResponse`. The first contract is synchronous: `POST /exports`
records `export.requested` and then returns `completed` with masked export
content or fails/rejects in the same request. No async polling/download endpoint
exists in this first contract.

| Response field | Notes |
| --- | --- |
| `export_id` | Opaque export id. |
| `service_id` | Requested Service scope. |
| `resource_type` | Exported resource type. |
| `status` | `completed` or `rejected` from the same request. |
| `format` | Export format. |
| `content` | Inline masked export content for completed exports. |
| `rejection_reason` | Reason when the request is rejected. |
| `requested_by` | Session actor id. |
| `requested_at` | UTC timestamp. |

Authorization: `auditor`, `service_owner`, or `system_admin` with
`export:export`.

Audit events: `export.requested`, then `export.completed` or
`export.rejected`.
