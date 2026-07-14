# Task 2 Report: Backend Permission Summary API

## Status

Implemented and committed-ready. The accepted ADR at
`docs/adr/2026-07-14-central-iam-permission-management-console.md` already
covers this central IAM API direction, so no new ADR was created.

## TDD Evidence

RED attempt 1:

```bash
uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

Result: `3 skipped, 1 warning`. This was not useful RED evidence because the
local shell has no `TEST_DATABASE_URL` or `DATABASE_URL`, so DB-backed tests
skipped.

RED confirmed after adding no-DB route/helper contract tests:

```bash
uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

Result: `3 failed, 3 skipped, 1 warning`.

Expected failures:

- `GET /admin/v1/permission-management/admin-users` returned `404` instead of
  `200`.
- Non-`system_admin` request returned `404` instead of `403`.
- `IntentRoutingRepository` did not expose
  `list_permission_admin_user_summaries`.

GREEN:

```bash
uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

Result: `3 passed, 3 skipped, 1 warning`.

## Files Changed

- `src/intent_routing/api/admin.py`
- `src/intent_routing/db/repositories.py`
- `tests/integration/test_permission_management_api.py`
- `tests/unit/test_permission_management_repository.py`
- `.superpowers/sdd/task-2-report.md`

## Implementation Summary

- Added immutable repository summary records for permission management.
- Added `IntentRoutingRepository.list_permission_admin_user_summaries(...)`.
- Added `GET /admin/v1/permission-management/admin-users`.
- Added response models for Admin user identity/status, sorted global roles,
  linked organization user and department metadata, service roles with service
  display names, last-active-system-admin status, and derived risk flags.
- Supported query params: `query`, `status`, `global_role`,
  `organization_link`, `organization_use_yn`, and `limit` with 1..200 API
  validation.
- Kept the endpoint read-only and protected by `require_admin_session_context`,
  `admin_context_from_session_record`, `_require_system_admin(context)`, and
  `get_admin_session`.
- Did not add users authorization flags, columns, migrations, or write behavior
  changes to existing endpoints.

## Verification

```bash
uv run ruff check src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py
```

Result: `All checks passed!`

```bash
uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

Result: `3 passed, 3 skipped, 1 warning`.

## Concerns

- DB-backed API/repository behavior tests are present, but skipped locally
  because no DB URL is configured in this shell. They should run in an
  environment with `TEST_DATABASE_URL` or `DATABASE_URL`.
- Pytest emits an existing `StarletteDeprecationWarning` from
  `fastapi.testclient`.
- `ruff format --diff` still wants to reflow unrelated legacy wrapping in
  `admin.py` and `repositories.py`; that broad churn was intentionally not
  applied.

## Review Fix

### Cause

- The original DB-backed evidence was weak because the target tests skipped
  without a DB URL.
- The repository test had a loose
  `[] or ["single_active_system_admin"]` assertion, so it did not prove the
  exact count-sensitive risk behavior.
- The forbidden response-field check did not include `admin_yn` or `adminYn`.
- Once the DB-backed tests actually ran, the repository fixture also exposed a
  duplicate department number in test data.

### Solution

- Added a DB-independent repository helper test that verifies
  `active_system_admin_count=1` sets both `is_last_active_system_admin` and
  `single_active_system_admin`, while `active_system_admin_count=2` clears both.
- Removed the loose risk-flag OR assertions from broad DB-backed tests.
- Added `admin_yn` and `adminYn` to the forbidden API response-field check.
- Split the disabled test user's department number so the DB-backed repository
  test can run cleanly against Postgres.

### Verification

```bash
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run alembic upgrade head
```

Result: migration command completed successfully. A prior attempt with only
`TEST_DATABASE_URL` failed because Alembic reads `DATABASE_URL`.

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

Result: `7 passed, 1 warning`.

```bash
uv run ruff check tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py
```

Result: `All checks passed!`

### Concerns

- Pytest still emits the existing `StarletteDeprecationWarning` from
  `fastapi.testclient`.
