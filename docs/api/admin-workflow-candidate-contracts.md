# Admin Workflow Candidate Contracts

These endpoints support Admin UI workflow selectors. They return service-scoped,
reloadable candidates so operators do not manually type internal ids during
normal workflow handoffs.

## Common Rules

- Base path: `/admin/v1`.
- Authentication: `irt_admin_session` HttpOnly cookie.
- Authorization: server-derived admin context and selected Service roles.
- Service-scoped endpoints must only return candidates for the requested
  `service_id`.
- API key inventory must never return the raw `api_key` secret.
- Responses are ordered newest first unless specified otherwise.
- `limit` parameters are integers from 1 to 100 and default to 50.
- Phase 2 governed workflows remain disabled or informational until their
  approval contracts exist.

## GET /admin/v1/services/{service_id}/policy-versions

Lists policy versions available to the selected Service.

Query:

- `limit`: integer, 1 to 100, default 50.

Response: `PolicyVersionResponse[]`.

Each item includes:

- `policy_version`
- `service_id`
- `threshold_preset`
- `threshold_value`
- `clarify_margin`
- `min_candidate_score`
- `fallback_score`
- `risk_policy`
- `off_topic_policy`
- `created_by`
- `created_at`

Authorization: catalog access for the Service.

## GET /admin/v1/services/{service_id}/catalog-versions

Lists catalog versions available to the selected Service.

Query:

- `limit`: integer, 1 to 100, default 50.
- `status`: optional `active` or `inactive`. When omitted, both active and
  inactive versions are returned.

Response: `CatalogVersionListItemResponse[]`.

Each item includes:

- `intent_catalog_version`
- `display_version`
- `service_id`
- `model_version`
- `vector_index_version`
- `description`
- `status`
- `reproducibility_status`
- `released`
- `release_count`
- `source_catalog_version`
- `intent_count`
- `example_count`
- `embedding_count`
- `created_by`
- `created_at`
- `activated_at`
- `deactivated_at`

Authorization: catalog access for the Service.

## GET /admin/v1/services/{service_id}/test-runs

Lists validation runs available as workflow history and release-candidate input.

Query:

- `gate_passed`: optional boolean.
- `risk_passed`: optional boolean. `true` means `risk_pass_rate == 1.0`.
- `limit`: integer, 1 to 100, default 50.

Response: `TestRunListItemResponse[]`.

Each item includes:

- `test_run_id`
- `service_id`
- `test_dataset_version`
- `source_filename`
- `policy_version`
- `intent_catalog_version`
- `model_version`
- `vector_index_version`
- `threshold_preset`
- `threshold_value`
- `pass_rate`
- `review_rate`
- `risk_pass_rate`
- `gate_passed`
- `block_reasons`
- `recommendations`
- `created_by`
- `created_at`

Authorization: catalog access for the Service.

## GET /admin/v1/services/{service_id}/release-candidates

Lists test runs that can be considered for release creation.

Query:

- `environment`: optional release-owned environment: `dev`, `qa`, or `prod`.
  Omitted values default to `dev`.
- `limit`: integer, 1 to 100, default 50.

Response: `ReleaseCandidateResponse[]`.

Each item includes:

- `test_run_id`
- `service_id`
- `environment`
- `policy_version`
- `intent_catalog_version`
- `test_dataset_version`
- `source_filename`
- `threshold_preset`
- `pass_rate`
- `risk_pass_rate`
- `gate_passed`
- `eligible`
- `block_reasons`
- `already_released`
- `existing_release_version`
- `created_at`

Authorization: catalog access for reading; release creation remains
`system_admin`.

## GET /admin/v1/services/{service_id}/intent-route-candidates

Lists known intent and route candidates for API key scope selection.

Query:

- `source`: `current_catalog` or `active_release`, default `current_catalog`.
- `environment`: optional string for active release lookup.

Response: `IntentRouteCandidateResponse[]`.

Each item includes:

- `intent_id`
- `display_name`
- `route_key`
- `status`
- `source`

Authorization: catalog access for `current_catalog`; release access for
`active_release` snapshot.

## GET /admin/v1/api-keys

The global inventory endpoint remains transitional for scripts and older Admin
UI references. C-3 Admin UI work should prefer
`GET /admin/v1/services/{service_id}/api-keys`.

Lists API key inventory for administrative review without exposing the key
secret.

Query:

- `service_id`: optional string.
- `environment`: optional string.
- `status`: optional string.
- `limit`: integer, 1 to 100, default 50.

Response: `ApiKeyResponse[]`.

Each item includes:

- `key_id`
- `key_fingerprint`
- `app_id`
- `service_id`
- `environment`
- `status`
- `allowed_intents`
- `allowed_route_keys`
- `expires_at`
- `created_by`
- `created_at`
- `revoked_at`

Security rule: response excludes `api_key` secret.

Authorization: `system_admin`.
