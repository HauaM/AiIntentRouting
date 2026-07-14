# Task 5 Report

## Cause

Task 5 required a new Admin UI surface for organization directory management:
trimmed request helpers, a routed page for departments and organization users,
system-admin-gated mutating controls, and navigation wiring that follows the
existing AdminShell and ProTable patterns.

## Solution

- Added `directoryForms.test.ts` first and verified the expected red state when
  `directoryForms.ts` did not exist.
- Implemented `directoryForms.ts` with the required trim helpers from the brief.
- Added the `/organization-directory` route and `Users & Departments` nav item
  with `TeamOutlined`.
- Built `OrganizationDirectory` as a compact tabbed AdminShell page with:
  - Departments and Users ProTables
  - create/edit modals for both resources
  - `ConfirmActionButton` deactivation actions
  - `system_admin` gating with a read-only info alert for unauthorized users
  - organization-directory service calls only for department/user data

## Changed Files

- `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`
- `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`
- `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
- `frontend/intent-routing-console/config/config.ts`
- `frontend/intent-routing-console/src/components/AdminShell.tsx`
- `.superpowers/sdd/task-5-report.md`

## Verification

- `cd frontend/intent-routing-console && pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts`
  - failed first because `directoryForms.ts` was missing
- `cd frontend/intent-routing-console && pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts src/services/adminServices.test.ts`
  - passed: 19 tests
- `cd frontend/intent-routing-console && pnpm run typecheck`
  - passed with exit code 0
- Forbidden dependency/header search on changed frontend files
  - no matches for React Query, axios, trusted admin headers, or `Authorization: Bearer`

## Unverified / Remaining Risk

- No browser smoke test was run, so the final check is limited to tests,
  typechecking, and source inspection.

## Fix 2026-07-14: Review follow-up

### Cause

- The page rendered the unauthorized info banner but still mounted
  organization-directory tables and option loaders, which could trigger
  `system_admin`-only department/user API requests for non-system-admin
  sessions.
- Department selectors and the Users-tab department filter only searched within
  the first `listDepartments({ limit: 100 })` response, so later department
  number/name searches could not reach departments outside that initial slice.

### Solution

- Added helper coverage for the `system_admin` access gate and server-backed
  department option search params in `directoryForms.test.ts`.
- Added `canAccessOrganizationDirectory` and
  `toDepartmentOptionSearchParams` in `directoryForms.ts`.
- Gated the entire Organization Directory surface for `system_admin`; when the
  session is authenticated but unauthorized, the page now renders only a
  concise info `Alert`.
- Switched both department Select entry points to remote search behavior using
  `listDepartments({ query, limit: 100 })` with `filterOption={false}` and
  `onSearch`, while keeping an initial useful options load for authorized
  sessions.

### Changed Files

- `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`
- `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`
- `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`

### Verification

- `cd frontend/intent-routing-console && pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts`
  - failed first with:
    - `canAccessOrganizationDirectory is not a function`
    - `toDepartmentOptionSearchParams is not a function`
- `cd frontend/intent-routing-console && pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts src/services/adminServices.test.ts`
  - passed: 2 files, 21 tests
- `cd frontend/intent-routing-console && pnpm run typecheck`
  - passed with exit code 0
- `rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|server pagination|live polling|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope" frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
  - exited with code 1 (no matches)

### Unverified / Remaining Risk

- No browser smoke test was run in this fix pass, so the unauthorized render
  path and remote-search interaction were verified through helper tests,
  typecheck, and source inspection rather than a live UI session.
