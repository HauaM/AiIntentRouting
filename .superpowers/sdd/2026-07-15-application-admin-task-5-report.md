## Scope

Implemented Task 5 only: Admin access request API coverage for public request creation plus `system_admin` review actions (`list`, `approve`, `reject`) in the Admin backend. Kept changes scoped to the API, repository helpers, and the integration test file named in the brief.

## Files Read

- `/home/haua/workspace/AiIntentRouting/.superpowers/sdd/2026-07-15-application-admin-task-5-brief.md`
- `/home/haua/workspace/AiIntentRouting/.superpowers/sdd/2026-07-15-application-admin-review-checklist-decision-log.md`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/api/admin.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/db/repositories.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/db/models.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/security/admin_passwords.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/security/admin_auth.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/api/admin_dependencies.py`
- `/home/haua/workspace/AiIntentRouting/tests/integration/test_admin_user_management_api.py`

## RED/GREEN Test Evidence

### RED

Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_user_management_api.py::test_admin_access_request_approval_creates_user_admin_user_and_application_admin tests/integration/test_admin_user_management_api.py::test_non_system_admin_cannot_approve_admin_access_request -q
```

Result:

- Exit code: `1`
- `2 failed`
- Failure mode:
  - `POST /admin/v1/admin-access-requests` returned `404` instead of `201`
  - `GET /admin/v1/admin-access-requests` returned `404` instead of `403`

### GREEN (targeted)

Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_user_management_api.py::test_admin_access_request_approval_creates_user_admin_user_and_application_admin tests/integration/test_admin_user_management_api.py::test_non_system_admin_cannot_approve_admin_access_request -q
```

Result:

- Exit code: `0`
- `2 passed`

### Full task file verification

Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_user_management_api.py -q
```

Result:

- Exit code: `0`
- `8 passed, 1 warning`
- Warning: existing `StarletteDeprecationWarning` from `fastapi.testclient` / `httpx`

### Pre-commit diff hygiene

Command:

```bash
git diff --check
```

Result:

- Exit code: `0`
- No whitespace or conflict-marker issues reported

## Changes Made

### API

- Added request/decision/response schemas for admin access requests.
- Added public `POST /admin/v1/admin-access-requests` with:
  - active department validation
  - immediate password hashing
  - duplicate guards for existing org users/admin users
  - pending-request uniqueness handled as `409`
  - `admin_access_request.created` audit event
- Added `GET /admin/v1/admin-access-requests` restricted to `system_admin`.
- Added `POST /admin/v1/admin-access-requests/{request_id}/approve` restricted to `system_admin` with:
  - row-locked pending-request read
  - one-transaction creation of `users`, `admin_users`, and `admin_user_roles(application_admin)`
  - password hash cleared from the request on approval
  - `admin_access_request.approved` audit event
  - `admin_user.global_role_granted` audit event for `application_admin`
- Added `POST /admin/v1/admin-access-requests/{request_id}/reject` restricted to `system_admin` with:
  - row-locked pending-request read
  - password hash cleared from the request on rejection
  - `admin_access_request.rejected` audit event
- Included department summary data in `AdminAccessRequestResponse`.
- Expanded managed-admin request role validation to accept `application_admin`.

### Repository

- Exposed a public row-lock helper for admin access requests.
- Updated approval helper to accept the locked request plus created record IDs.
- Updated rejection helper to operate on the locked request object.
- Added organization-user lookup by `user_number`.
- Added a conservative default `admin_access_reason` for non-request admin-user creation paths so existing managed/admin bootstrap test flows still satisfy the non-null schema.

### Tests

- Added RED/GREEN integration coverage for public request creation and approval.
- Added authorization coverage proving non-`system_admin` callers cannot list/review requests.
- Added rejection coverage proving pending password hashes are cleared.
- Updated cleanup helper to remove `admin_access_requests` rows and recover cleanly from rolled-back sessions.
- Adjusted existing integration tests to respect the single-`system_admin` invariant by:
  - using `application_admin` for non-owner role mutation coverage
  - reusing the canonical `system_admin` when asserting “cannot disable/revoke own last system admin”

## Self-Review

- Approval path now creates only `application_admin` and does not attach service roles or service permissions.
- Approval/rejection clear `admin_access_requests.password_hash` and populate decision metadata.
- Review actions use a locked pending request, and late/duplicate decisions are surfaced as `409` rather than uncaught `500`s.
- Audit events requested by the brief are emitted on create/approve/reject and on the approval-time global role grant.
- Response payload includes department summary without an extra API round-trip.

## Concerns

- Integrity error mapping is intentionally coarse-grained at the API layer (`409` with stable messages) rather than constraint-name-specific. It satisfies the task behavior but could be made more granular later if UI copy needs exact duplicate reasons.
- I did not add dedicated concurrency tests for simultaneous approve/reject races in this task file; the implementation follows the required row-lock pattern, but that race is only covered indirectly by the repository/API design in this patch.
