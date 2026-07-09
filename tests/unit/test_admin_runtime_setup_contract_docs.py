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
        "no browser runtime sample call with the secret",
        "Runtime Logs show `query_masked` by default",
        "Audit Logs remain append-only evidence",
        "without a required DB migration",
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
        "`api_key` is present only in the create response",
        "`api_key` raw secret is never present in inventory",
        '"selected_key"',
        "`source=active_release`",
        "GET /admin/v1/services/{service_id}/runtime-setup",
        "future/not baseline",
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
        "no required migration",
        "optional hardening",
    ):
        assert phrase in text
