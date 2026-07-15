# Task 4 Report: Auth Eligibility For `application_admin`

## Scope

- Task source: `/home/haua/workspace/AiIntentRouting/.superpowers/sdd/2026-07-15-application-admin-task-4-brief.md`
- Related checklist/decision log: `/home/haua/workspace/AiIntentRouting/.superpowers/sdd/2026-07-15-application-admin-review-checklist-decision-log.md`
- Goal: require an Admin login role (`system_admin` or `application_admin`) for login eligibility, add explicit auth coverage for `application_admin`, and ensure existing session validation fails after role revocation.

## TDD Evidence

### RED

1. First targeted run without DB env:

```bash
uv run pytest tests/integration/test_admin_account_auth_api.py::test_application_admin_can_login_without_service_roles tests/integration/test_admin_account_auth_api.py::test_admin_user_without_access_role_cannot_login tests/integration/test_admin_account_auth_api.py::test_auth_me_rejects_existing_session_after_application_admin_role_revocation -q
```

- Result: skipped by `tests/conftest.py` because `TEST_DATABASE_URL` / `DATABASE_URL` was unset.

2. First targeted run with documented local test DB env:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_account_auth_api.py::test_application_admin_can_login_without_service_roles tests/integration/test_admin_account_auth_api.py::test_admin_user_without_access_role_cannot_login tests/integration/test_admin_account_auth_api.py::test_auth_me_rejects_existing_session_after_application_admin_role_revocation -q
```

- Result: initial failure was a test setup defect (`NameError: uuid4 is not defined`).
- Action: added the missing `uuid4` import, then reran.

3. Second targeted RED run:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_account_auth_api.py::test_application_admin_can_login_without_service_roles tests/integration/test_admin_account_auth_api.py::test_admin_user_without_access_role_cannot_login tests/integration/test_admin_account_auth_api.py::test_auth_me_rejects_existing_session_after_application_admin_role_revocation -q
```

- Result: `test_admin_user_without_access_role_cannot_login` failed with `assert 200 == 401`.
- Interpretation: active Admin users without `system_admin` or `application_admin` were still login-eligible. This is the intended Task 4 behavior gap.

### GREEN

1. Focused rerun after repository/auth changes:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_account_auth_api.py::test_application_admin_can_login_without_service_roles tests/integration/test_admin_account_auth_api.py::test_admin_user_without_access_role_cannot_login tests/integration/test_admin_account_auth_api.py::test_auth_me_rejects_existing_session_after_application_admin_role_revocation -q
```

- Result: `3 passed`.

2. Full auth integration file:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_account_auth_api.py -q
```

- First result: one failure in startup provisioning because `configure_startup_system_admin(...)` still created `admin_users` without `admin_access_reason`.
- Action: updated startup provisioning to pass an explicit reason.
- Final rerun result: `7 passed, 1 warning`.

## Changes Made

### 1. Auth integration tests

File: `/home/haua/workspace/AiIntentRouting/tests/integration/test_admin_account_auth_api.py`

- Added `test_application_admin_can_login_without_service_roles`.
- Added `test_admin_user_without_access_role_cannot_login`.
- Added `test_auth_me_rejects_existing_session_after_application_admin_role_revocation`.
- Added missing `admin_access_reason` values to existing `create_admin_user(...)` calls in this file.
- Added missing `uuid4` import required by the new tests.

### 2. Login eligibility query

File: `/home/haua/workspace/AiIntentRouting/src/intent_routing/db/repositories.py`

- Updated `get_login_eligible_admin_user_by_email(...)` to:
  - join `admin_user_roles`,
  - require `role in ADMIN_LOGIN_ROLES`,
  - preserve the existing active-admin and active-linked-organization-user checks,
  - return a distinct Admin user row.

This keeps `application_admin` as Admin UI access only. It does not change service-scoped authorization, which still comes only from `user_service_roles`.

### 3. Auth creation paths requiring `admin_access_reason`

Files:

- `/home/haua/workspace/AiIntentRouting/src/intent_routing/api/admin_auth.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/security/admin_provisioning.py`

- Added explicit `admin_access_reason` for bootstrap-created system admins.
- Added explicit `admin_access_reason` for startup-provisioned system admins.

### 4. Plan tracking

File: `/home/haua/workspace/AiIntentRouting/docs/superpowers/plans/2026-07-15-application-admin-approval-rbac.md`

- Updated only the Task 4 checklist items from unchecked to checked as the work completed.

## Self-Review

- `application_admin` login is now explicitly covered and works without any service roles.
- A role-less active Admin user now fails login with 401.
- Existing session validation still re-reads persisted roles on `/auth/me`; removing `application_admin` causes the old cookie to fail with 401.
- `_current_user_response(...)` already returned sorted `global_roles` and excluded password/session token hashes; the new tests and existing auth responses still respect that behavior.
- No service scope was granted through `application_admin`; Task 4 only changes Admin UI login eligibility.

## Files Changed

- `/home/haua/workspace/AiIntentRouting/tests/integration/test_admin_account_auth_api.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/db/repositories.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/api/admin_auth.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/security/admin_provisioning.py`
- `/home/haua/workspace/AiIntentRouting/docs/superpowers/plans/2026-07-15-application-admin-approval-rbac.md`

## Concerns

- Full verification for this task is limited to `tests/integration/test_admin_account_auth_api.py`, per the brief. I did not broaden into other auth- or provisioning-adjacent files once this target file was green.
