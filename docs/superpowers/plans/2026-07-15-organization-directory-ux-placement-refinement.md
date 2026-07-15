# Organization Directory UX Placement Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine `/organization-directory` so component placement clearly reads as an organization user and department directory, while keeping `/permission-management` as the central IAM surface.

**Architecture:** Keep the current backend API contracts and Umi `request` service functions. Extract small pure helpers for AdminShell route visibility and directory table filter params, then use those helpers from `AdminShell` and `OrganizationDirectory`. Replace the current ProTable search area with compact single-line toolbars, keep create/edit modals, and visually separate the compact Admin Access shortcut from the organization user form fields.

**Tech Stack:** React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design ProComponents, Vitest, Umi `request`, `irt_admin_session` browser session cookie.

## Global Constraints

- Do not change backend endpoints or service function contracts in `frontend/intent-routing-console/src/services/adminServices.ts`.
- Do not introduce React Query, `@tanstack/react-query`, axios, `Authorization: Bearer`, `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope`.
- Normal browser Admin UI requests continue to use Umi `request`, `withCredentials`, and the server-issued `irt_admin_session` HttpOnly cookie.
- `/organization-directory` remains a `system_admin`-only organization directory surface for `departments` and `users` metadata.
- `/permission-management` remains the central IAM surface for Admin accounts, global roles, Service roles, permission audit history, and permission risk review.
- Keep the user edit modal's compact Admin Access section, but do not add Service role assignment, permission history, or risk findings to that modal.
- Do not fake server pagination, compound filters, live polling, approval workflow state, or backend readiness.
- Use single-line table toolbars for the department and organization user filters because each tab has no more than three simple supported filters.
- Preserve `ConfirmActionButton` for activation, deactivation, Admin account status changes, and `system_admin` grant/revoke actions.
- Do not modify `.env` or unrelated backend test files.

---

## File Structure

- Create: `frontend/intent-routing-console/src/components/adminShellNavigation.ts`
  - Owns route visibility metadata and filters system-admin-only routes before `AdminShell` renders the ProLayout menu.
- Test: `frontend/intent-routing-console/src/components/adminShellNavigation.test.ts`
  - Verifies organization directory and permission management are hidden for non-`system_admin` users and visible for `system_admin`.
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
  - Uses route specs from `adminShellNavigation.ts`, maps icon keys to Ant Design icons, and places `ServiceScopeBar` before the global phase notice.
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`
  - Adds typed filter helpers for department and organization user table requests.
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`
  - Adds tests for the new filter helpers and copy-safe URL behavior already present.
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
  - Renames visible copy toward "조직 디렉터리", replaces ProTable search with single-line toolbars, keeps tab-scoped primary actions, and separates Admin Access inside the user edit modal.

## Task 1: AdminShell Role-Aware Navigation

**Files:**
- Create: `frontend/intent-routing-console/src/components/adminShellNavigation.ts`
- Create: `frontend/intent-routing-console/src/components/adminShellNavigation.test.ts`
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`

**Interfaces:**
- Consumes: `session.globalRoles` from `useModel('adminSession')`.
- Produces: `getAdminShellRouteSpecs(globalRoles: readonly string[]): AdminShellRouteSpec[]`.

- [ ] **Step 1: Write the failing navigation helper test**

Create `frontend/intent-routing-console/src/components/adminShellNavigation.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { getAdminShellRouteSpecs } from './adminShellNavigation';

const paths = (roles: readonly string[]) =>
  getAdminShellRouteSpecs(roles).map((route) => route.path);

const names = (roles: readonly string[]) =>
  getAdminShellRouteSpecs(roles).map((route) => route.name);

describe('adminShellNavigation', () => {
  it('hides system-admin-only routes for non-system-admin users', () => {
    expect(paths(['service_developer'])).not.toContain('/organization-directory');
    expect(paths(['service_developer'])).not.toContain('/permission-management');
  });

  it('shows organization directory and permission management for system admins', () => {
    expect(paths(['system_admin'])).toContain('/organization-directory');
    expect(paths(['system_admin'])).toContain('/permission-management');
  });

  it('uses directory-specific Korean copy for the organization directory route', () => {
    expect(names(['system_admin'])).toContain('조직 디렉터리');
    expect(names(['system_admin'])).toContain('권한관리');
  });
});
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/components/adminShellNavigation.test.ts
```

Expected: FAIL because `./adminShellNavigation` does not exist.

- [ ] **Step 3: Add the navigation helper**

Create `frontend/intent-routing-console/src/components/adminShellNavigation.ts`:

```ts
export type AdminShellRouteIcon =
  | 'dashboard'
  | 'services'
  | 'organizationDirectory'
  | 'permissionManagement'
  | 'intentCatalog'
  | 'releases'
  | 'testRuns'
  | 'apiKeys'
  | 'runtimeLogs'
  | 'auditLogs';

export type AdminShellRouteSpec = {
  path: string;
  name: string;
  icon: AdminShellRouteIcon;
  systemAdminOnly?: boolean;
};

export const ADMIN_SHELL_ROUTE_SPECS: AdminShellRouteSpec[] = [
  { path: '/dashboard', name: 'Dashboard', icon: 'dashboard' },
  { path: '/services', name: 'Services', icon: 'services' },
  {
    path: '/organization-directory',
    name: '조직 디렉터리',
    icon: 'organizationDirectory',
    systemAdminOnly: true,
  },
  {
    path: '/permission-management',
    name: '권한관리',
    icon: 'permissionManagement',
    systemAdminOnly: true,
  },
  { path: '/intents', name: 'Intent Catalog', icon: 'intentCatalog' },
  { path: '/releases', name: 'Releases', icon: 'releases' },
  { path: '/test-runs', name: 'Test Runs', icon: 'testRuns' },
  { path: '/api-keys', name: 'API Keys', icon: 'apiKeys' },
  { path: '/runtime-logs', name: 'Runtime Logs', icon: 'runtimeLogs' },
  { path: '/audit-logs', name: 'Audit Logs', icon: 'auditLogs' },
];

export function getAdminShellRouteSpecs(globalRoles: readonly string[] = []) {
  const isSystemAdmin = globalRoles.includes('system_admin');
  return ADMIN_SHELL_ROUTE_SPECS.filter(
    (route) => !route.systemAdminOnly || isSystemAdmin,
  );
}
```

- [ ] **Step 4: Wire the helper into `AdminShell`**

Modify `frontend/intent-routing-console/src/components/AdminShell.tsx`:

```ts
import type { PropsWithChildren, ReactNode } from 'react';
```

Replace the current local `PropsWithChildren` import with the import above, then add:

```ts
import {
  getAdminShellRouteSpecs,
  type AdminShellRouteIcon,
} from './adminShellNavigation';
```

Add the icon map near the imports or above `AdminShell`:

```tsx
const routeIcons: Record<AdminShellRouteIcon, ReactNode> = {
  dashboard: <DashboardOutlined />,
  services: <ClusterOutlined />,
  organizationDirectory: <TeamOutlined />,
  permissionManagement: <SafetyOutlined />,
  intentCatalog: <ProfileOutlined />,
  releases: <RocketOutlined />,
  testRuns: <ExperimentOutlined />,
  apiKeys: <KeyOutlined />,
  runtimeLogs: <FileSearchOutlined />,
  auditLogs: <AuditOutlined />,
};
```

Replace the current inline `route` array passed to `ProLayout` with:

```tsx
route={{
  routes: getAdminShellRouteSpecs(session.globalRoles).map((route) => ({
    path: route.path,
    name: route.name,
    icon: routeIcons[route.icon],
  })),
}}
```

- [ ] **Step 5: Run the navigation test**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/components/adminShellNavigation.test.ts
```

Expected: PASS.

## Task 2: AdminShell Content Order

**Files:**
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`

**Interfaces:**
- Consumes: existing `ServiceScopeBar` props from `adminSession`.
- Produces: page structure where `ServiceScopeBar` is directly below the page title area, before the global Sprint 11 notice.

- [ ] **Step 1: Move `ServiceScopeBar` before the global notice**

In `frontend/intent-routing-console/src/components/AdminShell.tsx`, change the authenticated content order from:

```tsx
<Alert
  type="info"
  showIcon
  message="Sprint 11 Admin UI Phase 1"
  description="Authenticated console for service-scoped catalog work, test runs, releases, API keys, runtime logs, and audit evidence. Phase 2 governed approval workflows remain informational."
  style={{ marginBottom: 12 }}
/>
<ServiceScopeBar
  session={session}
  roles={displayRoles}
  serviceOptions={serviceOptions}
  onServiceChange={setServiceId}
  onLogout={logout}
/>
<main className="admin-page-content">{children}</main>
```

to:

```tsx
<ServiceScopeBar
  session={session}
  roles={displayRoles}
  serviceOptions={serviceOptions}
  onServiceChange={setServiceId}
  onLogout={logout}
/>
<Alert
  type="info"
  showIcon
  message="Sprint 11 Admin UI Phase 1"
  description="Authenticated console for service-scoped catalog work, test runs, releases, API keys, runtime logs, and audit evidence. Phase 2 governed approval workflows remain informational."
  style={{ marginTop: 12, marginBottom: 12 }}
/>
<main className="admin-page-content">{children}</main>
```

- [ ] **Step 2: Run the AdminShell-adjacent tests and typecheck**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/components/adminShellNavigation.test.ts src/models/adminSession.test.ts
pnpm run typecheck
```

Expected: both commands exit 0.

## Task 3: Directory Filter Helpers

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`

**Interfaces:**
- Produces:
  - `EMPTY_DEPARTMENT_TABLE_FILTERS: DepartmentTableFilters`
  - `EMPTY_ORGANIZATION_USER_TABLE_FILTERS: OrganizationUserTableFilters`
  - `toDepartmentListParamsFromFilters(filters: DepartmentTableFilters): { query?: string; use_yn?: API.UseYn; limit: 100 }`
  - `toOrganizationUserListParamsFromFilters(filters: OrganizationUserTableFilters): { query?: string; department_id?: string; use_yn?: API.UseYn; limit: 100 }`

- [ ] **Step 1: Add failing helper tests**

Extend the existing import from `./directoryForms` in `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts` with:

```ts
import {
  EMPTY_DEPARTMENT_TABLE_FILTERS,
  EMPTY_ORGANIZATION_USER_TABLE_FILTERS,
  toDepartmentListParamsFromFilters,
  toOrganizationUserListParamsFromFilters,
} from './directoryForms';
```

Add these test cases inside the existing `describe('directoryForms', () => {` block, before its closing `});`:

```ts
it('normalizes department toolbar filters into list params', () => {
  expect(toDepartmentListParamsFromFilters(EMPTY_DEPARTMENT_TABLE_FILTERS)).toEqual({
    limit: 100,
  });
  expect(
    toDepartmentListParamsFromFilters({
      keyword: ' 0969 IT지원부 ',
      use_yn: 'Y',
    }),
  ).toEqual({
    query: '0969 IT지원부',
    use_yn: 'Y',
    limit: 100,
  });
});

it('normalizes organization user toolbar filters into list params', () => {
  expect(
    toOrganizationUserListParamsFromFilters(EMPTY_ORGANIZATION_USER_TABLE_FILTERS),
  ).toEqual({ limit: 100 });
  expect(
    toOrganizationUserListParamsFromFilters({
      keyword: ' 홍길동 ',
      department_id: ' dept-1 ',
      use_yn: 'N',
    }),
  ).toEqual({
    query: '홍길동',
    department_id: 'dept-1',
    use_yn: 'N',
    limit: 100,
  });
});
```

- [ ] **Step 2: Run the failing helper tests**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts
```

Expected: FAIL because the new filter helper exports do not exist.

- [ ] **Step 3: Add filter helper types and functions**

Append to `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`:

```ts
export type DepartmentTableFilters = {
  keyword?: string;
  use_yn?: API.UseYn;
};

export type OrganizationUserTableFilters = {
  keyword?: string;
  department_id?: string;
  use_yn?: API.UseYn;
};

export const EMPTY_DEPARTMENT_TABLE_FILTERS: DepartmentTableFilters = {};

export const EMPTY_ORGANIZATION_USER_TABLE_FILTERS: OrganizationUserTableFilters = {};

const optionalTrimmedString = (value: string | undefined) => {
  const trimmed = value?.trim();
  return trimmed || undefined;
};

export const toDepartmentListParamsFromFilters = (
  filters: DepartmentTableFilters,
) => ({
  ...(optionalTrimmedString(filters.keyword)
    ? { query: optionalTrimmedString(filters.keyword) }
    : {}),
  ...(filters.use_yn ? { use_yn: filters.use_yn } : {}),
  limit: 100,
});

export const toOrganizationUserListParamsFromFilters = (
  filters: OrganizationUserTableFilters,
) => ({
  ...(optionalTrimmedString(filters.keyword)
    ? { query: optionalTrimmedString(filters.keyword) }
    : {}),
  ...(optionalTrimmedString(filters.department_id)
    ? { department_id: optionalTrimmedString(filters.department_id) }
    : {}),
  ...(filters.use_yn ? { use_yn: filters.use_yn } : {}),
  limit: 100,
});
```

- [ ] **Step 4: Run the helper tests**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts
```

Expected: PASS.

## Task 4: Organization Directory Single-Line Toolbars

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`

**Interfaces:**
- Consumes:
  - `DepartmentTableFilters`
  - `OrganizationUserTableFilters`
  - `EMPTY_DEPARTMENT_TABLE_FILTERS`
  - `EMPTY_ORGANIZATION_USER_TABLE_FILTERS`
  - `toDepartmentListParamsFromFilters`
  - `toOrganizationUserListParamsFromFilters`
- Produces:
  - Department tab toolbar with `검색`, `사용 여부`, `초기화`, `부서 추가`.
  - Organization user tab toolbar with `검색`, `부서`, `사용 여부`, `초기화`, `조직 사용자 추가`.
  - ProTables with `search={false}` and existing `pagination={false}`.

- [ ] **Step 1: Add imports for toolbar controls and filter helpers**

Modify imports in `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`:

```tsx
import { SearchOutlined } from '@ant-design/icons';
```

Extend the existing `./directoryForms` import:

```ts
  EMPTY_DEPARTMENT_TABLE_FILTERS,
  EMPTY_ORGANIZATION_USER_TABLE_FILTERS,
  toDepartmentListParamsFromFilters,
  toOrganizationUserListParamsFromFilters,
  type DepartmentTableFilters,
  type OrganizationUserTableFilters,
```

- [ ] **Step 2: Add toolbar filter state**

Inside `OrganizationDirectoryPage`, after the department option state declarations, add:

```ts
const [departmentDraftFilters, setDepartmentDraftFilters] =
  useState<DepartmentTableFilters>(EMPTY_DEPARTMENT_TABLE_FILTERS);
const [departmentFilters, setDepartmentFilters] =
  useState<DepartmentTableFilters>(EMPTY_DEPARTMENT_TABLE_FILTERS);
const [userDraftFilters, setUserDraftFilters] =
  useState<OrganizationUserTableFilters>(EMPTY_ORGANIZATION_USER_TABLE_FILTERS);
const [userFilters, setUserFilters] =
  useState<OrganizationUserTableFilters>(EMPTY_ORGANIZATION_USER_TABLE_FILTERS);
```

- [ ] **Step 3: Add filter apply/reset handlers**

Inside `OrganizationDirectoryPage`, after `reloadUserTable`, add:

```ts
const applyDepartmentFilters = () => {
  setDepartmentFilters(departmentDraftFilters);
};

const resetDepartmentFilters = () => {
  setDepartmentDraftFilters(EMPTY_DEPARTMENT_TABLE_FILTERS);
  setDepartmentFilters(EMPTY_DEPARTMENT_TABLE_FILTERS);
};

const applyUserFilters = () => {
  setUserFilters(userDraftFilters);
};

const resetUserFilters = () => {
  setUserDraftFilters(EMPTY_ORGANIZATION_USER_TABLE_FILTERS);
  setUserFilters(EMPTY_ORGANIZATION_USER_TABLE_FILTERS);
};
```

- [ ] **Step 4: Add the department toolbar render helper**

Inside `OrganizationDirectoryPage`, before `return`, add:

```tsx
const renderDepartmentToolbar = () => (
  <Flex justify="space-between" align="center" wrap="wrap" gap={8} style={{ width: '100%' }}>
    <Space wrap size={8}>
      <Input
        allowClear
        prefix={<SearchOutlined />}
        placeholder="부서번호 또는 부서명"
        style={{ width: 240 }}
        value={departmentDraftFilters.keyword}
        onChange={(event) =>
          setDepartmentDraftFilters((current) => ({
            ...current,
            keyword: event.target.value,
          }))
        }
        onPressEnter={applyDepartmentFilters}
      />
      <Select<API.UseYn>
        allowClear
        placeholder="사용 여부"
        style={{ width: 128 }}
        value={departmentDraftFilters.use_yn}
        options={[
          { label: 'Y', value: 'Y' },
          { label: 'N', value: 'N' },
        ]}
        onChange={(value) =>
          setDepartmentDraftFilters((current) => ({
            ...current,
            use_yn: value,
          }))
        }
      />
      <Button onClick={applyDepartmentFilters}>조회</Button>
      <Button onClick={resetDepartmentFilters}>초기화</Button>
    </Space>
    {canManage ? (
      <Button type="primary" onClick={openCreateDepartmentModal}>
        부서 추가
      </Button>
    ) : null}
  </Flex>
);
```

- [ ] **Step 5: Add the organization user toolbar render helper**

Inside `OrganizationDirectoryPage`, after `renderDepartmentToolbar`, add:

```tsx
const renderUserToolbar = () => (
  <Flex justify="space-between" align="center" wrap="wrap" gap={8} style={{ width: '100%' }}>
    <Space wrap size={8}>
      <Input
        allowClear
        prefix={<SearchOutlined />}
        placeholder="사번 또는 이름"
        style={{ width: 220 }}
        value={userDraftFilters.keyword}
        onChange={(event) =>
          setUserDraftFilters((current) => ({
            ...current,
            keyword: event.target.value,
          }))
        }
        onPressEnter={applyUserFilters}
      />
      <Select
        allowClear
        showSearch
        filterOption={false}
        loading={loadingDepartmentFilterOptions}
        placeholder="부서"
        style={{ width: 180 }}
        value={userDraftFilters.department_id}
        options={departmentFilterOptions}
        onSearch={(value) => {
          void loadDepartmentOptions(value, 'filter');
        }}
        onChange={(value) =>
          setUserDraftFilters((current) => ({
            ...current,
            department_id: value,
          }))
        }
      />
      <Select<API.UseYn>
        allowClear
        placeholder="사용 여부"
        style={{ width: 128 }}
        value={userDraftFilters.use_yn}
        options={[
          { label: 'Y', value: 'Y' },
          { label: 'N', value: 'N' },
        ]}
        onChange={(value) =>
          setUserDraftFilters((current) => ({
            ...current,
            use_yn: value,
          }))
        }
      />
      <Button onClick={applyUserFilters}>조회</Button>
      <Button onClick={resetUserFilters}>초기화</Button>
    </Space>
    {canManage ? (
      <Button type="primary" onClick={openCreateUserModal}>
        조직 사용자 추가
      </Button>
    ) : null}
  </Flex>
);
```

- [ ] **Step 6: Replace the Departments tab ProTable search and toolbar**

Change the Departments tab child from a bare `ProTable` with ProTable search to:

```tsx
<ProTable<API.Department>
  rowKey="id"
  actionRef={departmentActionRef}
  columns={departmentColumns}
  params={departmentFilters}
  request={async (params) => {
    const rows = await listDepartments(
      toDepartmentListParamsFromFilters(params as DepartmentTableFilters),
    );
    return { data: rows, total: rows.length, success: true };
  }}
  pagination={false}
  search={false}
  toolbar={{ title: renderDepartmentToolbar() }}
  options={{ density: true, fullScreen: false, reload: true, setting: true }}
/>
```

- [ ] **Step 7: Replace the Users tab ProTable search and toolbar**

Change the Users tab child from a bare `ProTable` with ProTable search to:

```tsx
<ProTable<API.OrganizationUser>
  rowKey="id"
  actionRef={userActionRef}
  columns={userColumns}
  params={userFilters}
  request={async (params) => {
    const rows = await listOrganizationUsers(
      toOrganizationUserListParamsFromFilters(
        params as OrganizationUserTableFilters,
      ),
    );
    return { data: rows, total: rows.length, success: true };
  }}
  pagination={false}
  search={false}
  toolbar={{ title: renderUserToolbar() }}
  options={{ density: true, fullScreen: false, reload: true, setting: true }}
/>
```

- [ ] **Step 8: Run focused TypeScript verification**

Run:

```bash
cd frontend/intent-routing-console
pnpm run typecheck
```

Expected: PASS.

## Task 5: Organization Directory Copy And Modal Sectioning

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`

**Interfaces:**
- Consumes: existing create/edit handlers and `ConfirmActionButton`.
- Produces: clearer Korean directory copy and a visually separated compact Admin Access section.

- [ ] **Step 1: Rename page and tab copy**

In `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`, replace:

```tsx
<AdminShell title="Users & Departments">
```

with:

```tsx
<AdminShell title="조직 디렉터리">
```

Replace tab labels:

```ts
label: 'Departments'
label: 'Users'
```

with:

```ts
label: '부서'
label: '조직 사용자'
```

- [ ] **Step 2: Rename table column copy**

Apply these replacements in `departmentColumns`:

```ts
title: 'Dept_Number' -> title: '부서번호'
title: 'Name' -> title: '부서명'
title: 'Use' -> title: '사용 여부'
title: 'Updated' -> title: '수정일'
```

Apply these replacements in `userColumns`:

```ts
title: 'User #' -> title: '사번'
title: 'Name' -> title: '이름'
title: 'Department' -> title: '부서'
title: 'Use' -> title: '사용 여부'
title: 'Updated' -> title: '수정일'
```

- [ ] **Step 3: Rename modal copy**

Replace department modal props:

```tsx
title={departmentFormMode === 'create' ? 'Create Department' : 'Edit Department'}
okText={departmentFormMode === 'create' ? 'Create' : 'Save'}
```

with:

```tsx
title={departmentFormMode === 'create' ? '부서 추가' : '부서 편집'}
okText={departmentFormMode === 'create' ? '추가' : '저장'}
```

Replace user modal props:

```tsx
title={userFormMode === 'create' ? 'Create User' : 'Edit User'}
okText={userFormMode === 'create' ? 'Create' : 'Save'}
```

with:

```tsx
title={userFormMode === 'create' ? '조직 사용자 추가' : '조직 사용자 편집'}
okText={userFormMode === 'create' ? '추가' : '저장'}
```

Replace form labels:

```ts
label="Dept_Number" -> label="부서번호"
label="Name" -> label="이름"
label="User number" -> label="사번"
label="Department" -> label="부서"
label="Use" -> label="사용 여부"
```

- [ ] **Step 4: Separate Admin Access inside the user modal**

Add `Divider` to the Ant Design imports:

```ts
Divider,
```

At the start of `renderAdminAccessSection`, replace:

```tsx
return (
  <Form.Item label="Admin Access">
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
```

with:

```tsx
return (
  <>
    <Divider orientation="left">Admin Access</Divider>
    <Form.Item label="연결된 Admin 계정">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
```

At the end of `renderAdminAccessSection`, replace:

```tsx
    </Space>
  </Form.Item>
);
```

with:

```tsx
      </Space>
    </Form.Item>
  </>
);
```

- [ ] **Step 5: Keep Admin Access actions compact**

Leave these Admin Access capabilities in the user edit modal:

```text
권한관리에서 보기
활성화
비활성화
system_admin 부여
system_admin 해제
관리자 계정 생성
```

Do not add these capabilities to the user edit modal:

```text
서비스 권한 부여
서비스 권한 해제
권한 변경 이력
운영 점검
리스크 상세
```

- [ ] **Step 6: Run focused verification**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts
pnpm run typecheck
```

Expected: both commands exit 0.

## Task 6: Full Verification And Manual UX Check

**Files:**
- Verify only; do not modify files in this task unless a previous task failed.

**Interfaces:**
- Consumes: all changes from Tasks 1-5.
- Produces: verified UX placement refinement.

- [ ] **Step 1: Run focused frontend tests**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run \
  src/components/adminShellNavigation.test.ts \
  src/pages/OrganizationDirectory/directoryForms.test.ts \
  src/pages/PermissionManagement/permissionManagement.test.ts \
  src/services/adminServices.test.ts
```

Expected: PASS for all listed test files.

- [ ] **Step 2: Run frontend typecheck**

Run:

```bash
cd frontend/intent-routing-console
pnpm run typecheck
```

Expected: command exits 0.

- [ ] **Step 3: Search changed frontend files for prohibited patterns**

Run:

```bash
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" \
  frontend/intent-routing-console/src/components/AdminShell.tsx \
  frontend/intent-routing-console/src/components/adminShellNavigation.ts \
  frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx \
  frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts
```

Expected: no matches.

- [ ] **Step 4: Start or reuse the local frontend**

If no frontend is running on port `30140`, run:

```bash
cd frontend/intent-routing-console
pnpm run dev:local
```

Expected: Umi dev server serves `http://localhost:30140`.

- [ ] **Step 5: Manual desktop check**

Open `http://localhost:30140/organization-directory` as a `system_admin` and verify:

```text
Page title is "조직 디렉터리".
ServiceScopeBar appears before the Sprint 11 phase notice.
Tabs are "부서" and "조직 사용자".
The active tab shows one compact toolbar directly above the table.
"부서 추가" appears only on the 부서 tab.
"조직 사용자 추가" appears only on the 조직 사용자 tab.
The table does not show the old ProTable search card.
The table still has reload, density, and setting options.
```

- [ ] **Step 6: Manual modal check**

From the organization user table, open an edit modal and verify:

```text
Directory fields appear first: ID, 사번, 이름, 부서, 사용 여부.
Admin Access is visually separated below the directory fields.
Admin Access shows linked Admin account summary or disabled account creation.
Admin Access includes "권한관리에서 보기" when a linked Admin account exists.
Service role assignment, permission history, and risk findings are not present in the modal.
Activation, deactivation, and system_admin grant/revoke actions still open confirmation modals before mutation.
```

- [ ] **Step 7: Manual narrow viewport check**

Use a narrow browser viewport around `390px` width and verify:

```text
Toolbar controls wrap without overlapping.
Primary action remains reachable.
The table uses horizontal scrolling if needed instead of squeezing columns into unreadable widths.
Modal content scrolls without hiding the footer buttons.
```

- [ ] **Step 8: Manual non-system-admin check**

Log in as a non-`system_admin` account and verify:

```text
The sidebar does not render "조직 디렉터리".
The sidebar does not render "권한관리".
Direct navigation to /organization-directory still shows the existing permission-required state or server-side 403 behavior.
Direct navigation to /permission-management still shows the existing permission-required state or server-side 403 behavior.
```

## Self-Review

- Spec coverage: The plan covers menu visibility, ServiceScopeBar placement, tab-local primary actions, single-line filters, table request honesty, modal sectioning, Admin Access shortcut scope, and verification.
- Placeholder scan: This plan contains no unresolved placeholders, no open-ended implementation steps, and no unspecified test commands.
- Type consistency: The helper names used in `OrganizationDirectory/index.tsx` match the exports defined in `directoryForms.ts`, and `AdminShell` consumes the route helper defined in `adminShellNavigation.ts`.
