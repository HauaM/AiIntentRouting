# Task 1: ADR And Contract Update

## Status

DONE

## Commit

- `822ab21 docs: record encrypted api key secret reveal contract`
- No implementation files or commits were changed after this commit.

## What Was Implemented

- Added the accepted ADR for AES-256-GCM envelope-encrypted API-key secret material and audited service-scoped reveal.
- Documented `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`, its response shape, authorization rules, legacy-key behavior, and `api_key.secret_revealed` audit event.
- Updated the prior C-3 ADR to point to the new reveal decision while preserving metadata-only inventory, revoke, runtime guidance, log, audit, and export behavior.
- Updated the Admin UI Pattern Kit, onboarding flow, E2E checklist, and Theme & UX guide with `Secret 보기/복사`, encrypted secret material, audited reveal, and redacted audit-state requirements.
- Added documentation contract assertions for the Admin API contract and v04 Admin UI handbook.

## RED Evidence

Command:

```text
uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q

10 passed in 0.02s
```

Result before documentation changes: `2 failed, 8 passed`.

The two new tests failed because the reveal endpoint and audited UI reveal language were not yet documented.

## GREEN Evidence

The same focused command passed after the documentation updates:

```text
10 passed in 0.02s
```

## Files Changed

- `docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md`
- `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`
- `docs/api/admin-runtime-setup-contracts.md`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- `docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md`
- `docs/THEME_AND_UX_GUIDE_v1.md`
- `tests/unit/test_admin_runtime_setup_contract_docs.py`
- `tests/unit/test_admin_ui_handbook_docs_contract.py`

## Self-Review

- Confirmed the commit contains exactly the nine permitted Task 1 files.
- Confirmed the existing unrelated pilot and frontend changes remain unstaged.
- Confirmed the stored commit subject and Korean commit body with `git log -1 --pretty=format:%B`.
- Confirmed the new ADR includes status, context, decision, alternatives, consequences, implementation notes, verification, and rollback/revisit conditions.
- No frontend or backend implementation behavior was changed.

## Concerns

- Pre-existing unrelated changes remain in the worktree and were intentionally not staged or modified.
- The docs contract tests verify documentation only; backend, frontend, migration, and runtime implementation behavior remain outside Task 1 and unverified here.

## Re-review Fix Report

- Replaced stale one-time-only and hash/fingerprint-only API-key rules with the
  actual boundary: no plaintext storage, no automatic UI-state replay, and no
  raw `api_key` in inventory, revoke, runtime setup, logs, audit, or exports.
- Updated the E2E checklist to allow only explicit audited reveal/copy by
  authorized `system_admin` and selected-Service `service_owner` users.
- Added negative documentation-contract assertions so the stale hash-only and
  impossible-re-fetch wording cannot return.

Verification:

```text
uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q

10 passed in 0.02s
```

## Review Fix Report

- Added the exact reveal allowlist (`system_admin` and selected-Service `service_owner`) and explicit reveal denials for `service_developer`, `service_operator`, and `auditor`.
- Documented legacy-key reveal failure as `409 Conflict` with an unavailable message and operator recovery by rotating or reissuing the key.
- Added positive and negative documentation-test assertions for the authorization and legacy-key contracts.

Verification:

```text
uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
10 passed in 0.02s
```

## Re-Review Fix Report: Secret-Derived Field Redaction

- Updated `docs/api/admin-runtime-setup-contracts.md` so audit, log, export,
  persisted-state, and UI-state surfaces must omit or redact both
  `api_key` and `authorization_header`, plus any response field derived from
  the raw secret.
- Clarified that the successful reveal response is the only response surface
  allowed to return those raw secret-derived fields.
- Added the same explicit redaction/omission requirement to the
  `api_key.secret_revealed` audit event and runtime live-test state rules.
- Updated the Admin API documentation contract test to assert the named fields,
  derived-field rule, and reveal-response exception.

Verification:

```text
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
10 passed in 0.02s
```

## Re-Review Fix Report: Authorization And Reveal Error Contracts

- Replaced the stale `Non-system_admin` create/revoke error case with
  unauthorized-role and out-of-scope cases that preserve selected-Service
  `service_owner` authorization.
- Added documented `403` reveal denial and legacy-key `409 Conflict` cases,
  including the rotate-or-reissue recovery message.
- Narrowed the UX prohibition to automatic or unaudited redisplay while
  explicitly allowing audited `Secret 보기/복사` for authorized roles.
- Clarified that creation displays and copies the initial raw secret and that
  later copying uses the audited reveal endpoint.
- Extended the docs contract tests to assert these cases and reject the stale
  non-`system_admin` wording.

Verification:

The exact command initially could not initialize the default uv cache because
the sandbox denied access to `/Users/jaeyoon/.cache/uv`. The same requested
pytest command passed with a writable temporary uv cache:

```text
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
10 passed in 0.01s
```

Additional verification:

```text
git diff --check
```

## Re-Review Fix Report: Revoked And Expired Reveal Error Contracts

- Documented revoked API-key reveal as HTTP `400` with code `INVALID_REQUEST`,
  the required `Revoked API key secrets cannot be revealed.` message, and
  recovery by issuing a new API key when runtime access is still needed.
- Documented expired API-key reveal as HTTP `400` with code `INVALID_REQUEST`,
  the required `Expired API key secrets cannot be revealed.` message, and the
  same issue-a-new-key recovery.
- Preserved legacy/no-encrypted-material reveal as HTTP `409 Conflict` with
  rotate-or-reissue recovery.
- Added documentation contract assertions for both lifecycle-specific cases.

Verification:

The exact requested command could not initialize the default uv cache because
the sandbox denied access to `/Users/jaeyoon/.cache/uv`. The prescribed
writable-cache fallback passed:

```text
UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
10 passed in 0.02s
```

Additional verification:

```text
git diff --check
```
