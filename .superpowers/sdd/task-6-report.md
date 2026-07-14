# Task 6 Report

## Cause

Task 6 required final verification guardrails to prove the new organization
directory does not become an authorization source, plus a frontend audit for
forbidden client-side auth assumptions.

## Solution

- Added an integration regression in
  `tests/integration/test_organization_directory_api.py` that seeds a real
  admin session cookie for an `admin_users.organization_user_id` linked to a
  `users` row with `use_yn = 'N'` and verifies `/admin/v1/auth/me` returns
  `401 AUTHENTICATION_FAILED`.
- Added the OpenAPI route registration assertions for organization directory
  endpoints in `tests/unit/test_admin_auth_api_contract.py`.
- Made one tiny supporting test fix in
  `tests/unit/test_organization_directory_schema.py` so required backend
  verification can clean up organization-directory rows in foreign-key-safe
  order when reusing the shared DB.

## Changed Files

- `tests/integration/test_organization_directory_api.py`
- `tests/unit/test_admin_auth_api_contract.py`
- `tests/unit/test_organization_directory_schema.py` (supporting cleanup fix)

## Verification

- Backend:
  `TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/unit/test_organization_directory_schema.py tests/unit/test_admin_auth_api_contract.py tests/integration/test_organization_directory_api.py tests/unit/test_admin_sessions.py -q`
  -> `47 passed, 1 warning`
- Frontend guardrail search:
  `rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|admin_yn|adminYn" frontend/intent-routing-console/src`
  -> matches only in test files:
  `src/models/adminSession.test.ts`, `src/pages/ApiKeys/runtimeSetup.test.ts`
- Frontend focused tests:
  `pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts src/services/adminServices.test.ts`
  -> `21 passed`
- Frontend typecheck:
  `pnpm run typecheck`
  -> exit code `0`

## Unverified / Remaining Risk

- Manual browser QA from the brief was not executed in this task.
- The backend suite still emits an existing `StarletteDeprecationWarning` from
  `fastapi.testclient`; it is non-blocking for this verification pass.
