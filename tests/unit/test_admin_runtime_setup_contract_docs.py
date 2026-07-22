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
        "authorized\n`system_admin` and selected-Service `service_owner` users may "
        "explicitly\nreveal/copy",
        "source=released_catalog",
        "`/api-keys` remains the selected-Service runtime setup workspace",
        "explicit Admin UI\nlive-test workflow",
        "live test automatically reveals the encrypted API Secret",
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
        "Unauthorized roles or out-of-scope actors cannot create or revoke "
        "selected-Service API keys.",
        "Reveal access denied for unauthorized roles or an out-of-scope actor",
        "Legacy key without encrypted secret material",
        "409 Conflict",
        "API key secret is unavailable; rotate or reissue this legacy key.",
        "The create response includes the raw `api_key` for the initial setup flow.",
        "`api_key` raw secret is never present in inventory",
        '"selected_key"',
        "`source=released_catalog`",
        "Runtime setup guidance continues to report the active release independently",
        "GET /admin/v1/services/{service_id}/runtime-setup",
        "future/not baseline",
        "The UI obtains the API Secret through the audited reveal endpoint",
        "Live-test HTTP request and response previews must be redacted",
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
        "Non-`system_admin` creates or revokes key",
    ):
        assert stale_phrase not in text


def test_api_key_secret_reveal_contract_is_documented() -> None:
    text = _read(CONTRACT)

    for phrase in (
        "POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal",
        "encrypted secret material",
        "The reveal allowlist is exactly `system_admin` and the selected-Service `service_owner`.",
        "`service_developer` is explicitly denied reveal access.",
        "`service_operator` is explicitly denied reveal access.",
        "`auditor` is explicitly denied reveal access.",
        "api_key.secret_revealed",
        "api_key_revealed",
        "authorization_header",
        "both `api_key` and `authorization_header`, plus any\n"
        "  response field derived from the raw secret, must be omitted or recorded only\n"
        "  as `REDACTED`.",
        "Audit state must omit `api_key`, `authorization_header`, and any response\n"
        "  field derived from the raw secret, or record each only as `REDACTED`.",
        "Outside that successful reveal response, inventory, revoke, runtime setup\n"
        "  guidance, audit logs, runtime logs, exports, and persisted or UI state must\n"
        "  omit or redact `api_key`, `authorization_header`, and any response field\n"
        "  derived from the raw secret.",
        "reveal metadata only; `api_key`, `authorization_header`, and any\n"
        "    response field derived from the raw secret must be omitted or `REDACTED`.",
        "Legacy keys without encrypted secret material cannot be revealed",
        "return `409 Conflict`",
        "API key secret is unavailable; rotate or reissue this legacy key.",
        "Operators must rotate or reissue legacy keys",
        "Revoked API key reveal returns HTTP `400` with code `INVALID_REQUEST`",
        "Revoked API key secrets cannot be revealed.",
        "issue a new API key if runtime access is still needed",
        "Expired API key reveal returns HTTP `400` with code `INVALID_REQUEST`",
        "Expired API key secrets cannot be revealed.",
        "`api_key_displayed_once` means the create response includes the secret",
        "`Cache-Control: no-store, no-cache, must-revalidate`",
        "`Pragma: no-cache`",
        "`Expires: 0`",
        "purpose + `service_id` + `key_id`",
        "`SELECT ... FOR UPDATE`",
    ):
        assert phrase in text

    for stale_phrase in (
        "The secret must be stored only as a hash/fingerprint, never plaintext.",
        "`api_key` is present only in the create response.",
        "shown only once in the create response",
        '"api_key": "irt_<one-time-secret>"',
    ):
        assert stale_phrase not in text
