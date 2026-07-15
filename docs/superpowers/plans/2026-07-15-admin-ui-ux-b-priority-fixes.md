# Admin UI UX B Priority Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the approved B scope for AiIntentRouting Admin UI: P0/P1 UI safety and mobile usability issues, plus API key one-time secret UX and targeted common table/status overflow guardrails.

**Architecture:** Make backward-compatible shared UI primitives first, then apply them to Services, Permission Management, AdminShell, Organization Directory, API Keys, and the Runtime Logs row-risk cleanup. Keep API behavior unchanged: existing Umi `request`, session-cookie auth, server-derived roles, masked runtime logs, and read-only audit logs stay intact. Use bounded table scroll and compact rendering instead of fake server pagination.

**Tech Stack:** React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design Pro v6, ProComponents, Vitest, Playwright/local dev stack.

## Global Constraints

- Do not read `.env`, secret, token, private key, or credential files.
- Do not revert user changes or unrelated untracked files.
- Do not add React Query, `@tanstack/react-query`, axios, `useQuery`, `useMutation`, `queryClient`, or `invalidateQueries`.
- Normal Admin UI browser requests must keep Umi `request`, `withCredentials`, and the `irt_admin_session` HttpOnly cookie pattern.
- Do not send `Authorization: Bearer`, `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope` from normal browser Admin UI code.
- Runtime Logs must render `query_masked` only; do not add raw query reveal controls.
- Audit Logs must remain read-only; do not add edit, delete, export, approve, or reject controls.
- Do not fake server pagination, compound filters, live polling, approval state, or backend readiness.
- Unsupported or not-wired Phase 2 controls must remain informational through `FutureFeatureNotice`.
- Dangerous role, release, revoke, or permission-changing actions must use `ConfirmActionButton` or an equivalent `Modal.confirm` flow.
- Use `apply_patch` for manual file edits.
- Keep changes scoped to `frontend/intent-routing-console` and this plan unless a test or doc contract requires a companion update.

## Evidence Inputs

- UI review output: `var/ui-review-2026-07-15T12-03-00-150Z`
- Permission Management mobile evidence: `interactive/permission-management-mobile-viewport.metrics.json` showed `documentSize.width = 1349` on a `390x844` viewport.
- Services mobile evidence: `interactive/services-mobile-viewport.metrics.json` showed `documentSize.width = 488` and `documentSize.height = 229062` on a `390x844` viewport.
- Organization Directory modal evidence: `interactive/organization-directory-user-edit-modal.metrics.json` showed modal height `889.28125` on a `900px` viewport.
- API Keys mobile evidence: `api-keys-mobile-390x844.metrics.json` and `interactive/api-keys-mobile-viewport.metrics.json` showed width `580` on a `390x844` viewport.
- API Keys overflow candidates pointed at the create form scope selectors first: `Allowed intents` / `Allowed route keys` rendered at `360px` wide and overflowed the `390px` viewport. The inventory table still needs bounded scroll, but table scroll alone is not sufficient.
- Source evidence: `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx` currently executes grant through a direct `Button onClick={handleGrant}` while revoke uses `ConfirmActionButton`.

## File Structure

- Modify: `frontend/intent-routing-console/src/components/ConfirmActionButton.tsx`
  - Backward-compatible risk and typed-confirmation support.
- Create: `frontend/intent-routing-console/src/components/StatusTag.tsx`
  - Shared semantic status tag used by touched tables. Includes compact sizing, nowrap behavior, and text+icon risk/error rendering.
- Modify: `frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx`
  - Remove fixed mobile-breaking selector min width while preserving full-width behavior inside wider forms.
- Modify: `frontend/intent-routing-console/src/global.less`
  - Remove business row background and add responsive table/modal guardrail classes.
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
  - Remove the global Sprint 11 alert from every authenticated page.
- Modify: `frontend/intent-routing-console/src/pages/Dashboard/index.tsx`
  - Add a compact dashboard-scoped Phase 1/onboarding notice.
- Modify: `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx`
  - Add grant confirmation and bounded membership table scroll.
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
  - Add bounded accessible services table scroll and compact service cells.
- Modify: `frontend/intent-routing-console/src/pages/PermissionManagement/index.tsx`
  - Compact Admin 계정 table, move overflow actions into a dropdown, and constrain tabs/table overflow.
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
  - Stabilize user edit modal height and replace deprecated Ant Design props.
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
  - Move one-time secret reveal from inline page Alert into a creation-success modal that clears raw secret on close.
- Modify: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
  - Remove risk row background and keep risk represented in the decision/status cell.
- Modify tests:
  - `frontend/intent-routing-console/src/pages/Services/membershipPanelContract.test.ts`
  - `frontend/intent-routing-console/src/pages/PermissionManagement/permissionManagement.test.ts`
  - `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`
  - `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`
  - Create `frontend/intent-routing-console/src/components/confirmActionButtonContract.test.ts`
  - Create `frontend/intent-routing-console/src/components/statusTagContract.test.ts`
  - Create `frontend/intent-routing-console/src/components/intentRouteMultiSelectContract.test.ts`

---

### Task 1: Shared ConfirmActionButton And StatusTag Guardrails

**Files:**
- Modify: `frontend/intent-routing-console/src/components/ConfirmActionButton.tsx`
- Create: `frontend/intent-routing-console/src/components/StatusTag.tsx`
- Modify: `frontend/intent-routing-console/src/global.less`
- Test: `frontend/intent-routing-console/src/components/confirmActionButtonContract.test.ts`
- Test: `frontend/intent-routing-console/src/components/statusTagContract.test.ts`

**Interfaces:**
- Produces:
  - `ConfirmActionButton` optional props: `riskLevel?: 'low' | 'high'`, `confirmText?: string`, `requireTypedConfirmation?: boolean`
  - `StatusTag({ status, label, size })` with `size?: 'small' | 'middle'`, nowrap, and risk/error/unauthorized icon support.
- Consumes:
  - Existing `ConfirmActionButton` usages without requiring call-site rewrites.

- [ ] **Step 1: Write failing ConfirmActionButton contract test**

Create `frontend/intent-routing-console/src/components/confirmActionButtonContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'ConfirmActionButton.tsx'), 'utf8');

describe('ConfirmActionButton contract', () => {
  it('supports high-risk typed confirmation without breaking existing props', () => {
    const text = source();

    expect(text).toContain("riskLevel?: 'low' | 'high'");
    expect(text).toContain('requireTypedConfirmation?: boolean');
    expect(text).toContain('confirmText?: string');
    expect(text).toContain('Modal.confirm({');
    expect(text).toContain('cancelText:');
    expect(text).toContain('typed confirmation');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/confirmActionButtonContract.test.ts
```

Expected: FAIL because `riskLevel`, `requireTypedConfirmation`, and `confirmText` are not implemented.

- [ ] **Step 3: Implement backward-compatible ConfirmActionButton props**

In `ConfirmActionButton.tsx`, replace the prop type with:

```ts
type ConfirmActionButtonProps = Pick<
  ButtonProps,
  'className' | 'danger' | 'disabled' | 'size' | 'style' | 'type'
> & {
  children: ReactNode;
  title: string;
  content: ReactNode;
  okText: string;
  onConfirm: () => Promise<void>;
  onSuccess?: () => void;
  riskLevel?: 'low' | 'high';
  confirmText?: string;
  requireTypedConfirmation?: boolean;
};
```

Update `openConfirm` to calculate danger from `danger || riskLevel === 'high'`. Add typed confirmation only when `requireTypedConfirmation` and `confirmText` are both set:

```tsx
let typedValue = '';
const highRisk = danger || riskLevel === 'high';

Modal.confirm({
  title,
  content: requireTypedConfirmation && confirmText ? (
    <Space direction="vertical" size={8} style={{ width: '100%' }}>
      {content}
      <Typography.Text type="secondary">
        typed confirmation: {confirmText}
      </Typography.Text>
      <Input
        aria-label="typed confirmation"
        placeholder={confirmText}
        onChange={(event) => {
          typedValue = event.target.value;
        }}
      />
    </Space>
  ) : content,
  okText,
  cancelText: '취소',
  okButtonProps: { danger: highRisk },
  async onOk() {
    if (requireTypedConfirmation && confirmText && typedValue !== confirmText) {
      message.error('확인 문구가 일치하지 않습니다.');
      throw new Error('typed confirmation mismatch');
    }
    await onConfirm();
    message.success('처리되었습니다.');
    onSuccess?.();
  },
});
```

Also import `Input`, `Space`, and `Typography` from `antd`.

- [ ] **Step 4: Add shared StatusTag**

Create `frontend/intent-routing-console/src/components/StatusTag.tsx`:

```tsx
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

type AdminStatus =
  | 'active'
  | 'inactive'
  | 'disabled'
  | 'draft'
  | 'deprecated'
  | 'pass'
  | 'fail'
  | 'risk'
  | 'unauthorized'
  | 'clarify'
  | 'fallback'
  | 'off_topic'
  | 'confident'
  | 'pending'
  | 'recorded'
  | 'none';

type AdminStatusTone = {
  bg: string;
  color: string;
  border: string;
  icon?: boolean;
};

const STATUS_TONE: Record<string, AdminStatusTone> = {
  active: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  confident: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  pass: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  recorded: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  clarify: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  pending: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  fail: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  risk: { bg: '#FBE9E7', color: '#A23B2E', border: '#E6B8B3', icon: true },
  unauthorized: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  inactive: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  disabled: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  draft: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  deprecated: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  fallback: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  off_topic: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  none: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
};

export function StatusTag({
  status,
  label,
  size = 'small',
}: {
  status?: AdminStatus | string | null;
  label?: string;
  size?: 'small' | 'middle';
}) {
  const normalized = status || 'none';
  const tone = STATUS_TONE[normalized] ?? STATUS_TONE.none;
  return (
    <Tag
      className={`admin-status-tag admin-status-tag-${size}`}
      icon={tone.icon ? <ExclamationCircleOutlined /> : undefined}
      style={{
        background: tone.bg,
        borderColor: tone.border,
        color: tone.color,
      }}
    >
      {label ?? normalized}
    </Tag>
  );
}
```

- [ ] **Step 5: Write StatusTag contract test**

Create `frontend/intent-routing-console/src/components/statusTagContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'StatusTag.tsx'), 'utf8');

describe('StatusTag contract', () => {
  it('keeps semantic status mapping centralized with compact text and risk icons', () => {
    const text = source();

    expect(text).toContain("active: { bg: '#EAF3EE'");
    expect(text).toContain("risk: { bg: '#FBE9E7'");
    expect(text).toContain("pending: { bg: '#FDF3E3'");
    expect(text).toContain("disabled: { bg: '#EEF0F3'");
    expect(text).toContain('ExclamationCircleOutlined');
    expect(text).toContain("size?: 'small' | 'middle'");
    expect(text).toContain('export function StatusTag');
  });
});
```

- [ ] **Step 6: Remove business row background from global CSS**

Delete this block from `frontend/intent-routing-console/src/global.less`:

```less
.row-risk td {
  background: #fff1f0;
}
```

Add responsive guardrail classes:

```less
.admin-scroll-table {
  max-width: 100%;
}

.admin-scroll-table .ant-table-wrapper,
.admin-scroll-table .ant-table-container {
  max-width: 100%;
}

.admin-nowrap-cell {
  white-space: nowrap;
}

.admin-ellipsis-cell {
  display: inline-block;
  max-width: 100%;
}

.admin-status-tag {
  align-items: center;
  display: inline-flex;
  font-weight: 500;
  line-height: 20px;
  white-space: nowrap;
}

.admin-status-tag-small {
  font-size: 12px;
  padding-inline: 6px;
}

.admin-status-tag-middle {
  font-size: 13px;
  padding-inline: 8px;
}
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/confirmActionButtonContract.test.ts src/components/statusTagContract.test.ts
```

Expected: PASS.

### Task 2: Services P0 Grant Confirmation And P1 Table Bounds

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
- Test: `frontend/intent-routing-console/src/pages/Services/membershipPanelContract.test.ts`

**Interfaces:**
- Consumes: `ConfirmActionButton` from Task 1.
- Produces: grant role confirmation before `grantServiceRole`, bounded Services tables, and compact cell rendering.

- [ ] **Step 1: Extend failing Services contract test**

In `membershipPanelContract.test.ts`, add:

```ts
it('requires confirmation before granting a selected-Service role', () => {
  const source = readSource('ServiceMembershipPanel.tsx');
  const grantArea = source.match(/<Space wrap align="end"[\s\S]*?<\/Space>/)?.[0];

  expect(grantArea).toContain('<ConfirmActionButton');
  expect(grantArea).toContain('title="Grant service role?"');
  expect(grantArea).toContain('onConfirm={handleGrant}');
  expect(grantArea).not.toContain('onClick={handleGrant}');
});

it('bounds membership table overflow without fake pagination', () => {
  const source = readSource('ServiceMembershipPanel.tsx');

  expect(source).toContain('scroll={{');
  expect(source).toContain('tableLayout="fixed"');
  expect(source).toContain('pagination={false}');
});
```

Add a second source read helper for `index.tsx` if needed:

```ts
const servicesIndexSource = () =>
  readFileSync(resolve(process.cwd(), 'src/pages/Services/index.tsx'), 'utf8');
```

Then add:

```ts
it('bounds the accessible services table without server pagination', () => {
  const source = servicesIndexSource();

  expect(source).toContain('scroll={{');
  expect(source).toContain('pagination={false}');
  expect(source).toContain('tableLayout="fixed"');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/pages/Services/membershipPanelContract.test.ts
```

Expected: FAIL because grant currently uses direct `Button onClick={handleGrant}` and tables have no `scroll`.

- [ ] **Step 3: Replace grant Button with ConfirmActionButton**

In `ServiceMembershipPanel.tsx`, derive the selected user:

```ts
const selectedUser = userOptions.find((option) => option.value === selectedUserId)?.user;
```

Replace the grant `Button` with:

```tsx
<ConfirmActionButton
  type="primary"
  title="Grant service role?"
  okText="Grant role"
  content={
    <Space direction="vertical" size={4}>
      <Typography.Text>
        {selectedServiceId} 서비스에 {selectedRole ?? '-'} 권한을 부여합니다.
      </Typography.Text>
      <Typography.Text type="secondary">
        대상: {selectedUser?.email ?? selectedUserId ?? '-'}
      </Typography.Text>
    </Space>
  }
  disabled={!canManage || !selectedUserId || !selectedRole}
  onConfirm={handleGrant}
>
  Grant role
</ConfirmActionButton>
```

- [ ] **Step 4: Compact membership table columns and bound scroll**

Update membership table columns so ordinary cells stay single-line:

```tsx
render: (_, row) => (
  <Typography.Text ellipsis style={{ maxWidth: 180 }}>
    {row.display_name}
  </Typography.Text>
)
```

Use `Typography.Text code copyable ellipsis` for user IDs in a separate column only if the column has width. Set table props:

```tsx
<Table<ServiceMemberTableRow>
  rowKey="rowKey"
  size="small"
  loading={loadingMembers}
  pagination={false}
  columns={columns}
  dataSource={members}
  scroll={{ x: 760, y: 320 }}
  tableLayout="fixed"
/>
```

- [ ] **Step 5: Compact Accessible Services table and bound scroll**

In `Services/index.tsx`, keep `pagination={false}` and add:

```tsx
scroll={{ x: 760, y: 420 }}
tableLayout="fixed"
```

Set explicit widths on `Service`, `Environment`, `Status`, `Roles`, and action columns. Render service ID as a single-line code value with ellipsis:

```tsx
<Typography.Text code copyable ellipsis style={{ maxWidth: 220 }}>
  {row.service_id}
</Typography.Text>
```

Move display name to a tooltip or omit it from the table row; selected service details already show full context above the table.

- [ ] **Step 6: Run focused tests**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/pages/Services/membershipPanelContract.test.ts
```

Expected: PASS.

### Task 3: Permission Management Mobile Overflow And Action Compaction

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/PermissionManagement/index.tsx`
- Modify: `frontend/intent-routing-console/src/global.less`
- Test: `frontend/intent-routing-console/src/pages/PermissionManagement/permissionManagement.test.ts`

**Interfaces:**
- Consumes: `StatusTag` and `ConfirmActionButton`.
- Produces: Admin 계정 table with max two inline actions, dropdown for remaining actions, bounded horizontal table scroll, and scrollable mobile tabs.

- [ ] **Step 1: Extend failing Permission Management source tests**

Add to `permissionManagement.test.ts`:

```ts
it('keeps admin user row actions compact and moves overflow actions into a dropdown', () => {
  const source = pageSource();

  expect(source).toContain('Dropdown');
  expect(source).toContain('MoreOutlined');
  expect(source).toContain('adminUserMoreMenuItems');
  expect(source).toContain('scroll={{');
  expect(source).not.toContain('width: 240');
});

it('adds a scrollable tabs class for mobile Permission Management tabs', () => {
  const source = pageSource();

  expect(source).toContain('className="permission-management-tabs"');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/pages/PermissionManagement/permissionManagement.test.ts
```

Expected: FAIL because there is no dropdown/more menu, table scroll, or tabs class.

- [ ] **Step 3: Add imports**

In `PermissionManagement/index.tsx`, add:

```ts
import { MoreOutlined } from '@ant-design/icons';
```

Add `Dropdown` and `Tooltip` to the `antd` imports.

- [ ] **Step 4: Add compact cell helpers**

Add helpers near existing tag helpers:

```tsx
const compactCodeText = (value?: string | null, maxWidth = 180) => (
  <Typography.Text code copyable ellipsis style={{ maxWidth }}>
    {value || '-'}
  </Typography.Text>
);

const compactText = (value?: string | null, maxWidth = 180) => (
  <Typography.Text ellipsis style={{ maxWidth }}>
    {value || '-'}
  </Typography.Text>
);
```

Use these in the `Admin user` and `Organization user` columns instead of vertical `Space direction="vertical"`.

- [ ] **Step 5: Move low-frequency row actions to dropdown**

Keep `활성화` and `비활성화` inline. Replace the remaining inline buttons with:

```tsx
const adminUserMoreMenuItems = (row: API.PermissionAdminUserSummary) => {
  const hasSystemAdmin = row.global_roles.includes('system_admin');
  const hasApplicationAdmin = row.global_roles.includes('application_admin');
  const inactiveOrgUser = row.organization_user?.use_yn === 'N';
  const mutating = mutatingAdminUserId === row.user_id;

  return [
    {
      key: 'grant-application-admin',
      label: 'application_admin 부여',
      disabled: mutating || hasApplicationAdmin,
      onClick: () => openApplicationAdminRoleConfirm(row, true),
    },
    {
      key: 'revoke-application-admin',
      label: 'application_admin 해제',
      disabled: mutating || !hasApplicationAdmin || hasSystemAdmin,
      onClick: () => openApplicationAdminRoleConfirm(row, false),
    },
    {
      key: 'transfer-system-admin',
      label: 'system_admin 이관',
      disabled:
        mutating ||
        !session.user ||
        row.user_id === session.user.user_id ||
        hasSystemAdmin ||
        !hasApplicationAdmin ||
        row.status !== 'active' ||
        inactiveOrgUser,
      onClick: () => openSystemAdminTransferModal(row),
    },
  ];
};
```

Add the confirm wrapper:

```tsx
const openApplicationAdminRoleConfirm = (
  row: API.PermissionAdminUserSummary,
  grant: boolean,
) => {
  Modal.confirm({
    title: grant ? 'Grant application_admin?' : 'Revoke application_admin?',
    content: grant
      ? `${row.email} 계정에 application_admin 전역 권한을 부여합니다.`
      : `${row.email} 계정의 application_admin 전역 권한을 해제합니다.`,
    okText: grant ? 'application_admin 부여' : 'application_admin 해제',
    cancelText: '취소',
    okButtonProps: { danger: !grant },
    onOk: () => handleApplicationAdminRoleChange(row, grant),
  });
};
```

Use the dropdown inside the option column:

```tsx
<Dropdown menu={{ items: adminUserMoreMenuItems(row) }} trigger={['click']}>
  <Button type="link" size="small" icon={<MoreOutlined />}>
    더보기
  </Button>
</Dropdown>
```

- [ ] **Step 6: Bound ProTable overflow**

For the Admin 계정 `ProTable`, keep `pagination={false}` and add:

```tsx
scroll={{ x: 1120 }}
```

Set the action column width to `180` and use `Space size={8} className="admin-nowrap-cell"`.

- [ ] **Step 7: Make Permission Management tabs scroll inside the page**

Add `className="permission-management-tabs"` to the `Tabs`.

In `global.less`, add:

```less
.permission-management-tabs .ant-tabs-nav {
  max-width: 100%;
  overflow-x: auto;
}

.permission-management-tabs .ant-tabs-nav-list {
  min-width: max-content;
}
```

- [ ] **Step 8: Run focused tests**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/pages/PermissionManagement/permissionManagement.test.ts
```

Expected: PASS.

### Task 4: AdminShell Notice Scope And Organization Directory Modal Stability

**Files:**
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Dashboard/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`
- Test: `frontend/intent-routing-console/src/components/adminShellNavigation.test.ts`
- Test: `frontend/intent-routing-console/src/pages/Dashboard/dashboardViewState.test.ts`

**Interfaces:**
- Produces: No global Sprint alert on every authenticated page; Dashboard owns compact phase/onboarding notice.
- Produces: Organization Directory modals with stable body scroll and non-deprecated Ant Design props.

- [ ] **Step 1: Add AdminShell source assertion**

In `adminShellNavigation.test.ts`, add:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const adminShellSource = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'AdminShell.tsx'), 'utf8');

it('does not render the Sprint phase notice globally in AdminShell', () => {
  expect(adminShellSource()).not.toContain('Sprint 11 Admin UI Phase 1');
});
```

- [ ] **Step 2: Add Organization Directory modal source assertion**

In `directoryForms.test.ts`, add:

```ts
it('uses stable modal scroll settings and current Ant Design hidden props', () => {
  const source = pageSource();

  expect(source).toContain('destroyOnHidden');
  expect(source).not.toContain('destroyOnClose');
  expect(source).not.toContain('destroyInactiveTabPane');
  expect(source).toContain("body: { maxHeight: 'calc(100vh - 220px)', overflow: 'auto' }");
  expect(source).toContain("footer: { marginTop: 0 }");
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/adminShellNavigation.test.ts src/pages/OrganizationDirectory/directoryForms.test.ts
```

Expected: FAIL because AdminShell still renders the global alert and Organization Directory uses deprecated props.

- [ ] **Step 4: Remove global alert from AdminShell**

Delete this block from `AdminShell.tsx`:

```tsx
<Alert
  type="info"
  showIcon
  message="Sprint 11 Admin UI Phase 1"
  description="Authenticated console for service-scoped catalog work, test runs, releases, API keys, runtime logs, and audit evidence. Phase 2 governed approval workflows remain informational."
  style={{ marginTop: 12, marginBottom: 12 }}
/>
```

Remove the `Alert` import if unused.

- [ ] **Step 5: Add compact Dashboard-scoped notice**

In `Dashboard/index.tsx`, place this near the top of the page content:

```tsx
<Alert
  type="info"
  showIcon
  className="admin-compact-page-notice"
  message="Admin UI Phase 1"
  description="현재 화면은 서비스 범위 운영, 런타임 증거, 감사 증거를 중심으로 합니다. 승인형 Phase 2 흐름은 연결된 화면에서 안내됩니다."
/>
```

- [ ] **Step 6: Stabilize Organization Directory tabs and modals**

In `OrganizationDirectory/index.tsx`, replace:

```tsx
destroyInactiveTabPane
```

with:

```tsx
destroyOnHidden
```

For both department and user `Modal`, replace `destroyOnClose` with `destroyOnHidden` and add:

```tsx
centered
width={640}
style={{ maxWidth: 'calc(100vw - 32px)' }}
styles={{
  body: { maxHeight: 'calc(100vh - 220px)', overflow: 'auto' },
  footer: { marginTop: 0 },
}}
```

The browser smoke in Task 7, not this source assertion, is the pass/fail check for the real UX: modal body must be the scroll container, and the footer buttons must remain visible and clickable at `1440x900` and `390x844`.

- [ ] **Step 7: Run focused tests**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/adminShellNavigation.test.ts src/pages/OrganizationDirectory/directoryForms.test.ts src/pages/Dashboard/dashboardViewState.test.ts
```

Expected: PASS.

### Task 5: API Keys One-Time Secret Modal And Mobile Overflow

**Files:**
- Modify: `frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Modify: `frontend/intent-routing-console/src/global.less`
- Test: `frontend/intent-routing-console/src/components/intentRouteMultiSelectContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`

**Interfaces:**
- Consumes: `ConfirmActionButton` high-risk typed confirmation from Task 1.
- Produces: raw `api_key` appears only inside the creation-success modal and is cleared from state when the modal closes.
- Produces: API key create form, runtime setup summary, and manual revoke controls no longer create page-level mobile overflow.

- [ ] **Step 1: Add failing IntentRouteMultiSelect mobile-width contract test**

Create `frontend/intent-routing-console/src/components/intentRouteMultiSelectContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'IntentRouteMultiSelect.tsx'), 'utf8');

describe('IntentRouteMultiSelect layout contract', () => {
  it('does not force a 360px minimum width on mobile forms', () => {
    const text = source();

    expect(text).not.toContain('minWidth: 360');
    expect(text).toContain("style={{ width: '100%', maxWidth: '100%' }}");
  });
});
```

- [ ] **Step 2: Extend failing API key page tests**

In `runtimeSetup.test.ts`, add source-based assertions:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const apiKeysPageSource = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');
```

Add:

```ts
it('renders the one-time API key secret in a close-to-clear modal, not a page alert', () => {
  const source = apiKeysPageSource();

  expect(source).toContain('<Modal');
  expect(source).toContain('open={Boolean(createdKey)}');
  expect(source).toContain('onCancel={clearCreatedKey}');
  expect(source).toContain('setCreatedKey(undefined)');
  expect(source).toContain('이 secret은 이 모달을 닫으면 다시 볼 수 없습니다.');
  expect(source).not.toContain('message="새 API key secret"');
});

it('uses bounded API key inventory table scroll without fake pagination', () => {
  const source = apiKeysPageSource();

  expect(source).toContain('scroll={{');
  expect(source).toContain('pagination={false}');
});

it('keeps API key form controls responsive on mobile', () => {
  const source = apiKeysPageSource();

  expect(source).toContain('className="api-key-scope-fields"');
  expect(source).toContain('column={{ xs: 1, md: 2 }}');
  expect(source).toContain("style={{ width: '100%', maxWidth: 320 }}");
  expect(source).toContain("layout=\"vertical\"");
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/intentRouteMultiSelectContract.test.ts src/pages/ApiKeys/runtimeSetup.test.ts
```

Expected: FAIL because the secret is currently shown in an inline Alert, the inventory table has no scroll, and `IntentRouteMultiSelect` forces `minWidth: 360`.

- [ ] **Step 4: Make IntentRouteMultiSelect mobile-safe**

In `IntentRouteMultiSelect.tsx`, replace:

```tsx
style={{ minWidth: 360, width: '100%' }}
```

with:

```tsx
style={{ width: '100%', maxWidth: '100%' }}
```

Keep the option dropdown content unchanged; vertical `Space` in `optionRender` is allowed because it renders option detail, not a table scan cell.

- [ ] **Step 5: Import Modal and add clear helper**

In `ApiKeys/index.tsx`, add `Modal` to the `antd` imports.

Add:

```ts
const clearCreatedKey = () => {
  setCreatedKey(undefined);
};
```

- [ ] **Step 6: Replace inline Alert with creation-success Modal**

Delete the inline `createdKey ? <Alert ... /> : null` block.

Render this modal inside the page fragment:

```tsx
<Modal
  open={Boolean(createdKey)}
  title="새 API key secret"
  onCancel={clearCreatedKey}
  footer={[
    <Button key="close" type="primary" onClick={clearCreatedKey}>
      복사 완료
    </Button>,
  ]}
  destroyOnHidden
  centered
  width={640}
  style={{ maxWidth: 'calc(100vw - 32px)' }}
  styles={{
    body: { maxHeight: 'calc(100vh - 220px)', overflow: 'auto' },
  }}
>
  {createdKey ? (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Alert
        type="warning"
        showIcon
        message="이 secret은 이 모달을 닫으면 다시 볼 수 없습니다."
        description="폐기는 secret 값이 아니라 key_id로 수행합니다. 페이지 이동, 새로고침, 모달 닫기 후에는 raw secret을 다시 표시하지 않습니다."
      />
      <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
        {createdKey.api_key}
      </Typography.Paragraph>
      <Space wrap>
        <Typography.Text copyable code>
          key_id {createdKey.key_id}
        </Typography.Text>
        <Tag>fingerprint {createdKey.key_fingerprint}</Tag>
        <Tag>{createdKey.status}</Tag>
      </Space>
    </Space>
  ) : null}
</Modal>
```

- [ ] **Step 7: Make create form and runtime setup responsive**

Replace the scope selector horizontal `Space` around `allowed_intents` and `allowed_route_keys` with a responsive grid class:

```tsx
<div className="api-key-scope-fields">
  <Form.Item
    name="allowed_intents"
    label={helpLabel('Allowed intents', apiKeyHelp.allowedIntents)}
  >
    <IntentRouteMultiSelect
      mode="intent"
      candidates={scopeCandidates}
      placeholder="허용할 intent 선택"
    />
  </Form.Item>
  <Form.Item
    name="allowed_route_keys"
    label={helpLabel('Allowed route keys', apiKeyHelp.allowedRouteKeys)}
  >
    <IntentRouteMultiSelect
      mode="route"
      candidates={scopeCandidates}
      placeholder="허용할 route key 선택"
    />
  </Form.Item>
</div>
```

Add CSS in `global.less`:

```less
.api-key-scope-fields {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  max-width: 100%;
}
```

Change runtime setup summary descriptions from:

```tsx
<Descriptions size="small" column={2}>
```

to:

```tsx
<Descriptions size="small" column={{ xs: 1, md: 2 }}>
```

For manual revoke, keep `layout="vertical"` or switch to a wrapping vertical-friendly layout, and replace the fixed input width:

```tsx
<Input placeholder="key_id" style={{ width: '100%', maxWidth: 320 }} />
```

- [ ] **Step 8: Strengthen API key revoke confirmation without stale form values**

For row revoke and manual revoke `ConfirmActionButton`, add:

```tsx
riskLevel="high"
requireTypedConfirmation
confirmText={row.key_id}
```

For manual revoke, do not pass `revokeForm.getFieldValue('key_id')` directly as a prop because Ant Design form value updates do not guarantee the parent component has re-rendered before the confirm button opens. Use `Form.useWatch`:

```ts
const manualRevokeKeyId = Form.useWatch('key_id', revokeForm)?.trim();
```

Then pass:

```tsx
riskLevel="high"
requireTypedConfirmation={Boolean(manualRevokeKeyId)}
confirmText={manualRevokeKeyId}
```

- [ ] **Step 9: Bound API key inventory overflow**

Add to the API key inventory `ProTable`:

```tsx
scroll={{ x: 960 }}
```

Set widths for `Key ID`, `App`, `Fingerprint`, `Scopes`, `Status`, `Expires`, and option columns. Replace the vertical `Scopes` cell with one-line text:

```tsx
<Typography.Text className="admin-nowrap-cell">
  intents {row.allowed_intents.length} · routes {row.allowed_route_keys.length}
</Typography.Text>
```

- [ ] **Step 10: Run focused tests**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/intentRouteMultiSelectContract.test.ts src/pages/ApiKeys/runtimeSetup.test.ts
```

Expected: PASS.

### Task 6: Targeted Common Table/Status Cleanup

**Files:**
- Modify: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
- Modify only if already touched by Tasks 2-5 or verified by evidence: `frontend/intent-routing-console/src/pages/Services/index.tsx`
- Modify only if already touched by Tasks 2-5 or verified by evidence: `frontend/intent-routing-console/src/pages/PermissionManagement/index.tsx`
- Modify only if already touched by Tasks 2-5 or verified by evidence: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
- Modify only if already touched by Tasks 2-5 or verified by evidence: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Test: targeted source tests already listed above, plus table-data tests if helper behavior changes.

**Interfaces:**
- Consumes: `StatusTag`.
- Produces: no Runtime Logs business semantic row background, and StatusTag adoption only in files already touched for B-scope fixes or proven by mobile/browser evidence.
- Does not produce: full design-system migration across every Admin UI table.

- [ ] **Step 1: Add Runtime Logs source assertion**

Create or extend a source assertion in the closest test file. If no Runtime Logs test exists, create `frontend/intent-routing-console/src/components/runtimeLogsTableContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'RuntimeLogsTable.tsx'), 'utf8');

describe('RuntimeLogsTable contract', () => {
  it('renders masked query only and does not use business row backgrounds', () => {
    const text = source();

    expect(text).toContain("dataIndex: 'query_masked'");
    expect(text).toContain('Masked query');
    expect(text).not.toContain('rowClassName');
    expect(text).not.toContain('row-risk');
    expect(text).not.toContain('query_raw');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/runtimeLogsTableContract.test.ts
```

Expected: FAIL until `rowClassName` is removed.

- [ ] **Step 3: Replace touched table status tags with StatusTag only in evidence-backed files**

Use this pattern only in files already modified by Tasks 2-5, or where browser smoke still shows status/tag overflow after the P0/P1 fixes:

```tsx
import { StatusTag } from '@/components/StatusTag';

render: (_, row) => <StatusTag status={row.status} />
```

For `Y/N`, use explicit labels:

```tsx
<StatusTag status={value === 'Y' ? 'active' : 'disabled'} label={value === 'Y' ? '사용' : '미사용'} />
```

For Runtime Logs decision:

```tsx
<StatusTag status={row.decision === 'risk' ? 'risk' : row.decision ?? 'none'} />
```

- [ ] **Step 4: Remove Runtime Logs row background**

In `RuntimeLogsTable.tsx`, delete:

```tsx
rowClassName={(row) => (row.decision === 'risk' ? 'row-risk' : '')}
```

Keep the detail drawer masked-query only:

```tsx
<Typography.Text>Masked query {selected.query_masked ?? 'none'}</Typography.Text>
```

- [ ] **Step 5: Compact simple vertical cells only where B evidence justifies it**

For table cells in files already touched by Tasks 2-5, or files with direct mobile overflow evidence, convert ordinary list rows to one-line ellipsis. Example:

```tsx
<Typography.Text ellipsis style={{ maxWidth: 220 }}>
  {row.intent_id}
</Typography.Text>
```

Keep vertical layout in drawers, modal bodies, form option renderers, and detail displays where the user is inspecting one item instead of scanning a table.

Do not edit `IntentCatalogTable.tsx` or `AuditLogsTable.tsx` in this task unless a fresh browser smoke or a source inspection shows a B-scope overflow/security problem. QueryFilter cleanup and audit detail drawer work remain outside this B implementation unless separately approved.

- [ ] **Step 6: Run focused tests**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run src/components/runtimeLogsTableContract.test.ts src/components/statusTagContract.test.ts src/components/intentRouteMultiSelectContract.test.ts src/pages/Services/membershipPanelContract.test.ts src/pages/PermissionManagement/permissionManagement.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/pages/OrganizationDirectory/directoryForms.test.ts
```

Expected: PASS.

### Task 7: Full Verification And Browser Smoke

**Files:**
- No source files unless verification exposes a regression.

**Interfaces:**
- Consumes all previous tasks.
- Produces final confidence report with tests, guardrail search, and browser evidence paths.

- [ ] **Step 1: Run typecheck**

Run:

```bash
cd frontend/intent-routing-console && pnpm run typecheck
```

Expected: exit `0`.

- [ ] **Step 2: Run targeted Vitest suite**

Run:

```bash
cd frontend/intent-routing-console && pnpm exec vitest run \
  src/components/confirmActionButtonContract.test.ts \
  src/components/statusTagContract.test.ts \
  src/components/intentRouteMultiSelectContract.test.ts \
  src/components/runtimeLogsTableContract.test.ts \
  src/pages/Services/membershipPanelContract.test.ts \
  src/pages/PermissionManagement/permissionManagement.test.ts \
  src/pages/OrganizationDirectory/directoryForms.test.ts \
  src/pages/ApiKeys/runtimeSetup.test.ts
```

Expected: exit `0`.

- [ ] **Step 3: Run full frontend unit tests if targeted suite passes**

Run:

```bash
cd frontend/intent-routing-console && pnpm run test:unit
```

Expected: exit `0`.

- [ ] **Step 4: Run diff whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit `0`.

- [ ] **Step 5: Run changed-file forbidden-pattern search**

Use the actual changed runtime/source file list after implementation. Do not include tests in this implementation search; `runtimeSetup.test.ts` intentionally documents runtime-client `Authorization: Bearer {{intent_routing_api_key}}`, which is allowed outside Admin UI browser auth. The expected command shape is:

```bash
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" \
  frontend/intent-routing-console/src/components/ConfirmActionButton.tsx \
  frontend/intent-routing-console/src/components/StatusTag.tsx \
  frontend/intent-routing-console/src/components/AdminShell.tsx \
  frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx \
  frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx \
  frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx \
  frontend/intent-routing-console/src/pages/Services/index.tsx \
  frontend/intent-routing-console/src/pages/PermissionManagement/index.tsx \
  frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx \
  frontend/intent-routing-console/src/pages/ApiKeys/index.tsx
```

Expected: no implementation matches. The runtime setup test may still intentionally contain `Authorization: Bearer {{intent_routing_api_key}}`; do not include test files in this search unless reporting that this match is runtime-client documentation, not Admin UI browser auth.

- [ ] **Step 6: Run local browser smoke**

Start the local stack or frontend dev server according to the current project runbook. Use `http://127.0.0.1:30140`.

Capture desktop `1440x900` and mobile `390x844` for:

```text
/services
/permission-management
/organization-directory
/api-keys
/runtime-logs
```

Expected:

- Source-based tests are guardrails for structure only. Browser smoke and DOM metrics are the pass/fail check for real overflow and modal behavior.
- `/services` mobile document width is `390` or only table-internal scroll grows; document height is no longer six figures; the first viewport is nonblank and shows shell/page title or meaningful Services content without waiting on a blank body.
- `/permission-management` mobile must be checked on every tab: `Admin 계정`, `접근 신청`, `전역 권한`, `서비스 권한`, `권한 변경 이력`, and `운영 점검`. For each tab, page-level document width must not grow to the previous `1349`; any necessary horizontal overflow must be contained inside the table or tabs scroller.
- `/organization-directory` user edit modal body scrolls internally, the footer remains visible and clickable, and deprecated-prop console warnings for `destroyOnClose` / `destroyInactiveTabPane` are gone.
- `/api-keys` mobile document width is the viewport width or overflow is limited to table-internal scroll. Specifically verify the create-form `Allowed intents` / `Allowed route keys` selectors, runtime setup `Descriptions`, manual revoke input, and inventory table.
- `/api-keys` raw secret appears only in the creation-success modal after a local/dev API key create action; closing the modal removes the raw secret from the DOM and inventory/runtime setup do not show it.
- `/runtime-logs` still shows `query_masked` and no raw query reveal UI.

- [ ] **Step 7: Stop any dev server started for verification**

If the implementation session starts a local dev stack, stop it before final reporting unless the user explicitly asks to leave it running.

## Out Of Scope For This B Plan

- New backend endpoints.
- Server pagination or live polling.
- Phase 2 raw-query approval UI activation.
- Audit Logs edit/delete/export actions.
- Dashboard C-1/C-2/C-3 progress redesign beyond the compact notice move.
- Full design-system migration of every table in the app.

## Self-Review Checklist

- Spec coverage:
  - P0 grant confirmation: Task 2.
  - Permission Management overflow/actions: Task 3.
  - Services accessible services height/width: Task 2.
  - AdminShell global alert: Task 4.
  - Organization Directory modal: Task 4.
  - API Keys one-time secret modal and mobile create-form overflow: Task 5.
  - Common table/status/row-risk guardrails: Tasks 1 and 6.
- Placeholder scan:
  - This plan contains no unresolved placeholder markers or unspecified implementation step.
- Type consistency:
  - `StatusTag` is introduced before page use.
  - `ConfirmActionButton` optional props are backward-compatible for existing call sites.
  - `IntentRouteMultiSelect` mobile width is fixed before `/api-keys` form verification.
  - Table scroll changes keep `pagination={false}` and do not introduce fake server pagination.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-15-admin-ui-ux-b-priority-fixes.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Use option 1 when the worktree is clean enough to isolate task reviews. Use option 2 when preserving local untracked plan files and current context is more important than parallelism.
