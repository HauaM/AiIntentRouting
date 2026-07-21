# Task 4 Report: Backend Create And Reveal Endpoint

Status: DONE_WITH_CONCERNS

Implemented encrypted API key secret persistence on create and the service-scoped
audited reveal endpoint. Reveal is restricted to `system_admin` and selected-Service
`service_owner`, with the specified missing, cross-service, revoked, expired, and
legacy-secret responses.

## Files Changed

- `src/intent_routing/api/admin.py`
- `tests/unit/test_admin_api_key_helpers.py`
- `tests/integration/test_admin_runtime_setup_api.py`

## Verification

Commands run:

```bash
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py -q -rs
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_api_key_helpers.py tests/unit/test_api_key_secret_encryption.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py -q -rs
git diff --check -- src/intent_routing/api/admin.py tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run ruff check src/intent_routing/api/admin.py tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py
```

Results:

```text
First focused test run: 9 passed, 9 skipped, 1 warning in 0.45s
Full focused test run: 10 passed, 12 skipped, 1 warning in 0.40s
Ruff: All checks passed!
git diff --check: passed with no output
```

Exact skip output from the full focused test run:

```text
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:355: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:448: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:503: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:569: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:592: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:632: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:672: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:760: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_runtime_setup_api.py:803: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_api_key_inventory_flow.py:118: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_api_key_inventory_flow.py:165: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
SKIPPED [1] tests/integration/test_admin_api_key_inventory_flow.py:186: DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL.
```

## Self-Review Notes

- Confirmed create-time encryption stores the encrypted envelope while preserving
  the hash and fingerprint used for authentication.
- Confirmed reveal requires API-key-management access, checks service ownership
  before decryption, rejects revoked, expired, and legacy keys, and emits the
  redacted `api_key.secret_revealed` audit event.
- Database-backed endpoint paths remain unverified locally because the database
  URL required by those integration fixtures was not configured.

## Review Fixes: 2026-07-22

Addressed the Task 4 review findings:

- The legacy/no-encrypted-material response now exactly matches the documented
  contract in both the primary guard and the defensive endpoint branch:
  `API key secret is unavailable; rotate or reissue this legacy key.`
- Reveal audits now use a dedicated metadata-only payload. It excludes the API
  key, authorization header, fingerprint, hash, and all secret-derived fields.
- Unit and integration coverage now asserts exact revoked, expired, and legacy
  reveal messages. The reveal integration test also asserts the persisted audit
  payload contains only safe metadata.

Verification run:

```bash
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_api_key_helpers.py tests/unit/test_api_key_secret_encryption.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py -q -rs
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run ruff check src/intent_routing/api/admin.py tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py
git diff --check -- src/intent_routing/api/admin.py tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py
```

Results: `12 passed, 12 skipped, 1 warning`. The 12 skipped tests are
database-backed integration cases that require `TEST_DATABASE_URL` or an
explicit `DATABASE_URL`. Ruff passed and `git diff --check` produced no output.
