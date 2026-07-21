from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md"
CONTRACT = ROOT / "docs/api/admin-runtime-setup-contracts.md"


def _read(path: Path) -> str:
    assert path.exists(), f"{path} must exist"
    return path.read_text(encoding="utf-8")


def test_c3_runtime_setup_adr_records_accepted_decisions() -> None:
    text = _read(ADR)

    for section in (
        "## Status",
        "Accepted",
        "## Context",
        "## Decision",
        "## Alternatives Considered",
        "## Consequences",
        "## Implementation Notes",
        "## Verification",
        "## Rollback or Revisit Conditions",
    ):
        assert section in text

    for phrase in (
        "C-3 Runtime Integration And Operations is part of the authorization-first onboarding flow",
        "GET /admin/v1/services/{service_id}/api-keys",
        "POST /admin/v1/services/{service_id}/api-keys",
        "POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke",
        "global `/admin/v1/api-keys` endpoints remain transitional",
        "irt_admin_session",
        "never X-Admin-Token",
        "Authorization: Bearer <api_key>",
        "X-Key-Id",
        "X-App-Id",
        "X-Service-Id",
        "X-Request-Id",
        "displayed once on create and never returned",
        "source=active_release",
        "`/api-keys` remains the selected-Service runtime setup workspace",
        "explicit Admin UI\nlive-test workflow",
        "operator manually enters an API Secret",
        "Runtime Logs show `query_masked` by default",
        "Audit Logs remain append-only evidence",
        "0011_api_key_optional_expiry",
        "TEST_DATABASE_URL",
        "Alembic revision mismatch",
    ):
        assert phrase in text


def test_c3_runtime_setup_contract_doc_defines_admin_api_and_runtime_guidance() -> None:
    text = _read(CONTRACT)

    for section in (
        "## Common Rules",
        "## Service-Scoped API Key Lifecycle",
        "## Intent-Route Candidate Scope Contract",
        "## GET /admin/v1/services/{service_id}/runtime-setup",
        "## Admin UI Runtime Live Test",
        "## Optional Metadata-Only Validation Endpoint",
        "## Dify And Client Setup Fields",
        "## Error Cases",
        "## Audit Events",
        "## DB And Schema Impact",
    ):
        assert section in text

    for phrase in (
        "Normal browser Admin UI requests use `irt_admin_session`",
        "must not send `X-Admin-Token`",
        "must not send `X-Actor-Id`",
        "must not send `X-Actor-Roles`",
        "must not send `X-Service-Scope`",
        "GET /admin/v1/services/{service_id}/api-keys",
        "POST /admin/v1/services/{service_id}/api-keys",
        "POST /admin/v1/services/{service_id}/api-keys/{key_id}:revoke",
        "C-3 key lifecycle create/list/revoke is available to `system_admin` and the\n"
        "  selected Service's authorized `service_owner`.",
        "`service_developer`, `service_operator`, and `auditor` cannot create or "
        "revoke\n  API keys.",
        "`api_key` is present only in the create response",
        "`api_key` raw secret is never present in inventory",
        '"selected_key"',
        "`source=active_release`",
        "GET /admin/v1/services/{service_id}/runtime-setup",
        "future/not baseline",
        "The operator must manually input the API Secret",
        "Authorization: Bearer {{intent_routing_api_key}}",
        "X-Key-Id",
        "X-App-Id",
        "X-Service-Id",
        "X-Request-Id",
        "`query`",
        "Timeout: 8 seconds",
        "confident",
        "unauthorized",
        "408, 5xx, and timeout",
        "api_key.created",
        "api_key.revoked",
        "runtime_setup.guidance_generated",
        "0011_api_key_optional_expiry",
        "`api_keys.expires_at` is nullable",
        "optional hardening",
    ):
        assert phrase in text

    for stale_phrase in (
        "C-3 baseline key lifecycle create/list/revoke requires `system_admin`",
        "Future delegation to `service_owner` or `service_operator`",
    ):
        assert stale_phrase not in text
