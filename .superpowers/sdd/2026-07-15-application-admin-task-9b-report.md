# Task 9b Report

## Changed files

- `frontend/intent-routing-console/config/config.ts`
- `frontend/intent-routing-console/src/pages/Login/index.tsx`
- `frontend/intent-routing-console/src/services/authServices.ts`
- `frontend/intent-routing-console/src/services/authServices.test.ts`
- `frontend/intent-routing-console/src/types/api.d.ts`
- `frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx`
- `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.ts`
- `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts`
- `docs/superpowers/plans/2026-07-15-application-admin-approval-rbac.md`

## Implementation summary

- Added `API.AdminAccessRequestCreateRequest` for the public admin access request payload.
- Added `submitAdminAccessRequest()` in `authServices.ts` using Umi `request` without cookie credentials, bearer auth, or trusted actor headers.
- Added the public `/admin-access-request` route and a login-page link into that flow.
- Added a standalone `AdminAccessRequest` page that does not use `AdminShell`, collects the required fields, submits the normalized payload, and shows the returned request status plus a return path to login.
- Added `toAdminAccessRequestCreateRequest()` with focused tests for payload trimming and source-level route/login wiring.
- Updated the Task 9b checklist in the implementation plan.

## Test commands and results

1. `cd frontend/intent-routing-console && pnpm vitest run src/services/authServices.test.ts src/pages/AdminAccessRequest/requestForm.test.ts`
   - PASS (`2` files, `7` tests)
2. `cd frontend/intent-routing-console && pnpm run typecheck`
   - PASS
3. `git diff --check`
   - PASS
4. `rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" <changed-files>`
   - PASS for implementation files. Matches remain only in the plan document where the verification command itself and the standing constraint text are recorded.

## Self-review

- Confirmed the public request page stays outside `AdminShell` and does not require an admin session.
- Confirmed the request wrapper targets `POST /admin-access-requests` and does not send `withCredentials`, bearer auth, or trusted headers.
- Confirmed the helper trims applicant-entered text fields while leaving the password value unchanged.
- Confirmed the login screen exposes the public request flow and the success state shows the returned request status.

## Remaining concerns

- Public applicants must enter `department_id` manually because `GET /departments` is `system_admin`-only. This is an intentional Task 9b UX limitation and should be revisited once a safe public department lookup contract exists.

## Task 9b review fix

### Changed files

- `frontend/intent-routing-console/src/services/authServices.ts`
- `frontend/intent-routing-console/src/services/authServices.test.ts`
- `frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx`
- `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts`

### Tests and results

1. `cd frontend/intent-routing-console && pnpm vitest run src/services/authServices.test.ts src/pages/AdminAccessRequest/requestForm.test.ts`
   - PASS (`2` files, `8` tests)
2. `cd frontend/intent-routing-console && pnpm run typecheck`
   - PASS
3. `git diff --check`
   - PASS
4. `rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" <changed-files>`
   - PASS

### Self-review

- Confirmed `submitAdminAccessRequest()` now explicitly sets `withCredentials: false`, overriding the app-level request default so public applicant requests do not carry `irt_admin_session`.
- Confirmed the auth service test now asserts `withCredentials: false` directly.
- Confirmed backend submission failures render through a form-level `Alert` instead of field-level validation chrome on `access_reason`.
