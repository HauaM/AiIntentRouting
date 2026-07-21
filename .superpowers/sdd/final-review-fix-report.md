# Final Review Fix Report

## Status

Implemented and committed the final review fixes on
`codex/encrypted-api-key-secret-reveal`.

Implementation commit:
`c30768ac56c70c33d478acdd4071c332c62a3b1d`

## Changes

- Wired `API_KEY_SECRET_KEK_ID`, `API_KEY_SECRET_KEK_BASE64`, and
  `API_KEY_SECRET_LEGACY_KEKS_JSON` into GitHub CI, both local stack scripts,
  and the CI/local runbooks using repository placeholder KEKs only.
- Added `source=released_catalog` candidate listing from the newest release for
  the requested environment. API-key scope validation and Admin UI selectors now
  use released catalog candidates without requiring activation. Runtime setup
  guidance continues to use `active_release`.
- Added `get_api_key_by_id_for_update()` and used it for global/service revoke
  and service reveal so concurrent lifecycle operations serialize on the row.
- Extended envelope encryption with optional canonical context associated data.
  API-key secrets bind `purpose=api_key_secret`, `service_id`, and `key_id`;
  raw-text call sites retain the previous context-free associated data.
- Added explicit `Cache-Control: no-store, no-cache, must-revalidate`,
  `Pragma: no-cache`, and `Expires: 0` headers to both create endpoints and the
  reveal endpoint.
- Updated contracts, ADR/plan references, frontend types, and regression tests.
  `api_key_displayed_once` remains compatible and is documented as meaning that
  the create response includes the secret, not that create is the only reveal path.

## Changed Files

- Runtime/config: `.github/workflows/ci.yml`, `scripts/run_local_dev_stack.sh`,
  `scripts/run_local_dev_stack_macos.sh`
- Backend: `src/intent_routing/api/admin.py`,
  `src/intent_routing/db/repositories.py`,
  `src/intent_routing/security/encryption.py`,
  `src/intent_routing/security/keyring.py`,
  `src/intent_routing/security/api_key_secrets.py`
- Frontend: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`,
  its runtime setup test, `adminServices.ts` and its test, and `types/api.d.ts`
- Docs: API candidate/runtime contracts, C-3 ADR/plan, CI verification, and the
  local runbook
- Tests: focused unit/integration coverage for KEK contracts, released catalogs,
  row locking, contextual AEAD, response headers, and updated API-key flows

No file under `docs/pilot/**` was staged or committed.

## Verification

- Focused backend unit/contracts: `79 passed`, `1 warning`
- Focused backend security/docs follow-up: `42 passed`, `1 warning`
- Full backend unit suite: `481 passed`, `25 skipped`, `3 warnings`
- Focused DB integration files: `95 skipped`, because neither a usable
  `TEST_DATABASE_URL` nor local test database was available
- Focused frontend Vitest: `43 passed` across 3 files
- Full frontend Vitest: `280 passed` across 45 files
- `uv run ruff check .`: passed
- `uv run mypy src tests`: passed, 174 source files checked
- `./node_modules/.bin/tsc --noEmit`: passed
- `bash -n scripts/run_local_dev_stack.sh`: passed
- `zsh -n scripts/run_local_dev_stack_macos.sh`: passed
- `git diff --check`: passed before commit

`UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache` was used for `uv` commands
because the default user cache was not writable in the sandbox.

## Residual Concerns

- DB-backed integration assertions, including real response headers and release
  ordering through PostgreSQL, remain unexecuted locally and must run in CI.
- Startup/readiness KEK validation was not added. Existing readiness behavior does
  not validate encryption configuration, and adding a new startup validation
  subsystem would exceed the requested low-churn condition. CI and local
  entrypoints now provide the required values, while key construction still fails
  closed without a configured API-key KEK.
