# Admin UI Phase 0 Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the Sprint 11 Admin UI Phase 0 read-only console after manual review, while removing any fake pagination behavior and keeping Phase 1/2 capabilities out of scope.

**Architecture:** Keep the existing Umi 4, Ant Design Pro v6, ProComponents, and Umi `request` implementation. Treat Admin APIs as array-returning read endpoints with explicit `limit` parameters, not server-paginated resources. Keep all write flows disabled or absent.

**Tech Stack:** Umi Max 4, React 18, Ant Design 5, Ant Design ProComponents, Vitest, TypeScript, local backend on port 30141, frontend on port 30140.

---

All paths below are relative to `/home/haua/workspace/AiIntentRouting`.

## Scope

In scope:
- Change local Admin UI default environment label from `prod` to `local`.
- Display Dashboard missing latency as `-`, not `0 ms`.
- Remove fake pagination slicing from Phase 0 list helpers.
- Disable ProTable pagination for array-backed Phase 0 tables and present them as recent read-only lists.
- Improve Runtime Logs empty state and Phase 2 notice weight.
- Improve Audit Logs table polish without adding edit, delete, export, approve, or reject controls.
- Keep Runtime Logs limited to `query_masked`; never display raw/original query text.

Out of scope:
- React Query, axios, `Authorization: Bearer`.
- Phase 1 write flows.
- Phase 2 original text approval or decrypt flows.
- Fake live polling.
- Backend API contract changes.

## File Structure

- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
  - Owns local session defaults and persisted Admin API header context.
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
  - Verifies the local default environment and session readiness behavior.
- Create: `frontend/intent-routing-console/src/pages/Dashboard/metricDisplay.ts`
  - Pure display helpers for Dashboard metric values.
- Create: `frontend/intent-routing-console/src/pages/Dashboard/metricDisplay.test.ts`
  - Verifies nullable latency display.
- Modify: `frontend/intent-routing-console/src/pages/Dashboard/index.tsx`
  - Uses the display helper for p95 latency.
- Modify: `frontend/intent-routing-console/src/services/tableData.ts`
  - Replaces fake pagination slicing with a read-only table result helper.
- Modify: `frontend/intent-routing-console/src/services/tableData.test.ts`
  - Verifies that helpers do not pretend to server-page data.
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Uses explicit recent limits and the read-only table result helper.
- Modify: `frontend/intent-routing-console/src/components/IntentCatalogTable.tsx`
  - Disables pagination for current array-backed Phase 0 endpoint.
- Modify: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
  - Disables pagination, improves empty state, keeps `query_masked` only.
- Modify: `frontend/intent-routing-console/src/components/AuditLogsTable.tsx`
  - Disables pagination, softens result tag, improves target/trace readability.
- Modify: `frontend/intent-routing-console/src/components/FutureFeatureNotice.tsx`
  - Adds a compact mode for informational Phase 2 notices.
- Modify: `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`
  - Uses compact notice mode.
- Modify: `frontend/intent-routing-console/src/global.less`
  - Adds small visual polish classes for compact notices and audit status tags.

---

### Task 1: Add Failing Tests For The Review Findings

**Files:**
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
- Create: `frontend/intent-routing-console/src/pages/Dashboard/metricDisplay.test.ts`
- Modify: `frontend/intent-routing-console/src/services/tableData.test.ts`

- [ ] **Step 1: Update the admin session default test**

Replace the first test in `frontend/intent-routing-console/src/models/adminSession.test.ts` with:

```ts
it('uses v04-compatible local defaults for Admin API headers', () => {
  expect(readAdminSession()).toEqual({
    ...DEFAULT_ADMIN_SESSION,
    serviceId: 'it-helpdesk-pilot-sprint10-operation-monitoring',
    serviceScope: 'it-helpdesk-pilot-sprint10-operation-monitoring',
    environment: 'local',
  });
});
```

- [ ] **Step 2: Add the Dashboard metric display test**

Create `frontend/intent-routing-console/src/pages/Dashboard/metricDisplay.test.ts`:

```ts
import { describe, expect, it } from 'vitest';

import { formatLatencyMs } from './metricDisplay';

describe('formatLatencyMs', () => {
  it('shows a dash when latency is missing', () => {
    expect(formatLatencyMs(null)).toBe('-');
    expect(formatLatencyMs(undefined)).toBe('-');
  });

  it('shows measured latency with an ms suffix', () => {
    expect(formatLatencyMs(0)).toBe('0 ms');
    expect(formatLatencyMs(27)).toBe('27 ms');
  });
});
```

- [ ] **Step 3: Update the table data helper test to reject fake pagination**

Replace the existing `pages local array responses...` test in `frontend/intent-routing-console/src/services/tableData.test.ts` with:

```ts
it('returns array-backed read-only rows without pretending to server-page data', () => {
  const result = toReadOnlyTableResult([1, 2, 3, 4, 5]);

  expect(result).toEqual({
    data: [1, 2, 3, 4, 5],
    total: 5,
    success: true,
  });
});
```

Update the import in the same file from:

```ts
toTableResult,
```

to:

```ts
toReadOnlyTableResult,
```

- [ ] **Step 4: Run tests and confirm RED**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
```

Expected: FAIL because `metricDisplay.ts` and `toReadOnlyTableResult` do not exist yet, and the default environment is still `prod`.

---

### Task 2: Implement Local Environment Default And Dashboard Latency Display

**Files:**
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
- Create: `frontend/intent-routing-console/src/pages/Dashboard/metricDisplay.ts`
- Modify: `frontend/intent-routing-console/src/pages/Dashboard/index.tsx`

- [ ] **Step 1: Change the default environment**

In `frontend/intent-routing-console/src/models/adminSession.ts`, change:

```ts
environment: 'prod',
```

to:

```ts
environment: 'local',
```

- [ ] **Step 2: Add the metric display helper**

Create `frontend/intent-routing-console/src/pages/Dashboard/metricDisplay.ts`:

```ts
export function formatLatencyMs(value: number | null | undefined) {
  return value == null ? '-' : `${value} ms`;
}
```

- [ ] **Step 3: Use the helper in Dashboard**

In `frontend/intent-routing-console/src/pages/Dashboard/index.tsx`, add:

```ts
import { formatLatencyMs } from './metricDisplay';
```

Replace the latency statistic:

```tsx
<Statistic title="Latency p95" value={metrics?.latency_ms.p95 ?? 0} suffix="ms" />
```

with:

```tsx
<Statistic title="Latency p95" value={formatLatencyMs(metrics?.latency_ms.p95)} />
```

- [ ] **Step 4: Run tests and confirm GREEN for this task**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
```

Expected: Dashboard metric and admin session tests pass. Table helper tests may still fail until Task 3.

---

### Task 3: Remove Fake Pagination From Array-Backed Tables

**Files:**
- Modify: `frontend/intent-routing-console/src/services/tableData.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/components/IntentCatalogTable.tsx`
- Modify: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
- Modify: `frontend/intent-routing-console/src/components/AuditLogsTable.tsx`

- [ ] **Step 1: Replace the table result helper**

In `frontend/intent-routing-console/src/services/tableData.ts`, replace `toTableResult` with:

```ts
export function toReadOnlyTableResult<T>(rows: T[]): TableResult<T> {
  return {
    data: rows,
    total: rows.length,
    success: true,
  };
}
```

Keep `filterIntents` and `filterRuntimeLogs` unchanged.

- [ ] **Step 2: Update admin service imports and limits**

In `frontend/intent-routing-console/src/services/adminServices.ts`, replace:

```ts
toTableResult,
```

with:

```ts
toReadOnlyTableResult,
```

Add constants near the top:

```ts
const RECENT_RUNTIME_LOG_LIMIT = 100;
const RECENT_AUDIT_LOG_LIMIT = 100;
```

Replace list function returns with:

```ts
export async function listIntents(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.Intent[]>(servicePath(serviceId, '/intents'), {
    method: 'GET',
  });
  return toReadOnlyTableResult(filterIntents(rows, params));
}

export async function listRuntimeLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.RuntimeLog[]>(servicePath(serviceId, '/runtime-logs'), {
    method: 'GET',
    params: { limit: RECENT_RUNTIME_LOG_LIMIT },
  });
  return toReadOnlyTableResult(filterRuntimeLogs(rows, params));
}

export async function listAuditLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.AuditLog[]>(servicePath(serviceId, '/audit-logs'), {
    method: 'GET',
    params: {
      limit: RECENT_AUDIT_LOG_LIMIT,
      event_type: params.event_type || undefined,
      trace_id: params.trace_id || undefined,
    },
  });
  return toReadOnlyTableResult(rows);
}
```

- [ ] **Step 3: Disable ProTable pagination**

In each table component, replace:

```tsx
pagination={{ pageSize: 20 }}
```

with:

```tsx
pagination={false}
```

Apply this to:
- `frontend/intent-routing-console/src/components/IntentCatalogTable.tsx`
- `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
- `frontend/intent-routing-console/src/components/AuditLogsTable.tsx`

- [ ] **Step 4: Run unit tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
```

Expected: all unit tests pass.

---

### Task 4: Polish Runtime Logs And Audit Logs Empty/Notice/Status UI

**Files:**
- Modify: `frontend/intent-routing-console/src/components/FutureFeatureNotice.tsx`
- Modify: `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`
- Modify: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
- Modify: `frontend/intent-routing-console/src/components/AuditLogsTable.tsx`
- Modify: `frontend/intent-routing-console/src/global.less`

- [ ] **Step 1: Add compact notice support**

In `frontend/intent-routing-console/src/components/FutureFeatureNotice.tsx`, update the props:

```ts
type FutureFeatureNoticeProps = {
  title: string;
  backendRequirement: string;
  phase?: 'Phase 2' | 'Future';
  compact?: boolean;
};
```

Update the function signature:

```ts
export function FutureFeatureNotice({
  title,
  backendRequirement,
  phase = 'Phase 2',
  compact = false,
}: FutureFeatureNoticeProps) {
```

Update the `Alert` props:

```tsx
className={compact ? 'future-feature-notice-compact' : undefined}
action={<Button disabled size={compact ? 'small' : 'middle'}>사용 불가</Button>}
```

- [ ] **Step 2: Use compact mode on Runtime Logs**

In `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`, update:

```tsx
<FutureFeatureNotice
  title="Original text approval"
  backendRequirement="Phase 2 backend approval and audit contracts are required before this console can expose original request text."
/>
```

to:

```tsx
<FutureFeatureNotice
  compact
  title="Original text approval"
  backendRequirement="Phase 2 backend approval and audit contracts are required before this console can expose original request text."
/>
```

- [ ] **Step 3: Add explicit Runtime Logs empty state**

In `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`, update the antd import:

```ts
import { Drawer, Empty, Space, Tag, Typography } from 'antd';
```

Add this prop to `ProTable<API.RuntimeLog>`:

```tsx
locale={{
  emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No recent runtime logs" />,
}}
```

Keep the `Masked query` column and detail drawer unchanged so only `query_masked` is displayed.

- [ ] **Step 4: Soften Audit Logs result tag and target readability**

In `frontend/intent-routing-console/src/components/AuditLogsTable.tsx`, change the antd import:

```ts
import { Alert, Empty, Tag, Typography } from 'antd';
```

Replace the target column:

```ts
{ title: 'Target', dataIndex: 'target_id', search: false, ellipsis: true },
```

with:

```tsx
{
  title: 'Target',
  dataIndex: 'target_id',
  search: false,
  ellipsis: true,
  render: (_, row) => (
    <Typography.Text ellipsis={{ tooltip: row.target_id }}>{row.target_id}</Typography.Text>
  ),
},
```

Replace the result column render:

```tsx
render: () => <Tag color="green">recorded</Tag>,
```

with:

```tsx
render: () => <Tag className="audit-result-recorded">recorded</Tag>,
```

Add this prop to `ProTable<API.AuditLog>`:

```tsx
locale={{
  emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No audit logs" />,
}}
```

- [ ] **Step 5: Add small CSS polish**

Append to `frontend/intent-routing-console/src/global.less`:

```less
.future-feature-notice-compact {
  padding: 12px 16px;
}

.audit-result-recorded {
  border-color: #c7d7c1;
  background: #f1f7ed;
  color: #315c2b;
}
```

- [ ] **Step 6: Run typecheck**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Expected: `tsc --noEmit` exits 0.

---

### Task 5: Full Verification And Manual Review

**Files:**
- No new files.
- Verify all changed frontend files.

- [ ] **Step 1: Run full frontend checks**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
corepack pnpm typecheck
corepack pnpm build
```

Expected:
- Unit tests pass.
- Typecheck passes.
- Build completes with Webpack compiled successfully.

- [ ] **Step 2: Search for forbidden patterns**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|server pagination|live polling" src config package.json
```

Expected: no output from `src`, `config`, or `package.json`.

- [ ] **Step 3: Verify local ports**

Run:

```bash
lsof -nP -iTCP:30140 -sTCP:LISTEN
lsof -nP -iTCP:30141 -sTCP:LISTEN
```

Expected:
- frontend node process listening on `30140`
- backend uvicorn process listening on `30141`

- [ ] **Step 4: Verify dashboard and API proxy**

Run:

```bash
curl -s -i http://127.0.0.1:30140/dashboard | sed -n '1,20p'
curl -s -i \
  -H 'X-Admin-Token: local-admin-token' \
  -H 'X-Actor-Id: admin-user' \
  -H 'X-Actor-Roles: system_admin' \
  -H 'X-Service-Scope: it-helpdesk-pilot-sprint10-operation-monitoring' \
  'http://127.0.0.1:30140/admin/v1/services/it-helpdesk-pilot-sprint10-operation-monitoring/runtime-metrics?window_hours=24' \
  | sed -n '1,30p'
```

Expected:
- `/dashboard` returns HTTP 200.
- metrics proxy returns HTTP 200.

- [ ] **Step 5: Manual browser review**

Open:

```text
http://127.0.0.1:30140/dashboard
```

Check:
- Service scope tag defaults to `local` after clearing old localStorage or saving session again.
- Dashboard `Latency p95` displays `-` when API returns `null`.
- Intent Catalog has no create, edit, delete, release, or approve controls.
- Runtime Logs shows no raw/original query text.
- Runtime Logs empty state says `No recent runtime logs`.
- Runtime Logs Phase 2 notice is less visually heavy.
- Audit Logs result tag is softer and still readable.
- Audit Logs has no edit, delete, export, approve, or reject controls.

---

## Self-Review

Spec coverage:
- `prod` label confusion is covered by Task 1 and Task 2.
- Dashboard `Latency p95` missing value is covered by Task 1 and Task 2.
- Runtime Logs empty state and Phase 2 notice polish are covered by Task 4.
- Audit Logs visual polish is covered by Task 4.
- Fake pagination removal is covered by Task 1 and Task 3.
- v04 forbidden patterns are covered by Task 5.

Type consistency:
- `toReadOnlyTableResult` is introduced in tests before implementation and then imported by `adminServices.ts`.
- `formatLatencyMs` is introduced in tests before implementation and then imported by Dashboard.
- `compact` is optional on `FutureFeatureNotice`, so existing callers remain valid.

Phase boundary check:
- No Phase 1 write controls are added.
- No Phase 2 decrypt/original text UI is enabled.
- Runtime Logs continue to display `query_masked` only.
