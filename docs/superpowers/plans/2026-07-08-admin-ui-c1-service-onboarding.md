# Admin UI C-1 Service Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the C-1 Admin UI Service onboarding slice so a `system_admin` can register a Service from the browser, refresh server-derived Service scope, select the new Service, and continue into the existing Intent Catalog workflow.

**Architecture:** Reuse the existing Umi Max Admin UI, account-session model, `AdminShell`, `ServiceScopeBar`, Umi `request`, and Ant Design Pro conventions. The backend `POST /admin/v1/services` already exists, so this plan adds frontend types, service wrapper, permission helper, Services page, routing, documentation updates, and focused tests. C-2 role assignment and C-3 runtime setup remain documented as future slices and must not be faked in C-1.

**Tech Stack:** React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design ProComponents, Vitest, FastAPI Admin API, pytest docs/API contract tests.

---

## Required Context

- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- `frontend/intent-routing-console/src/components/AdminShell.tsx`
- `frontend/intent-routing-console/src/components/ServiceScopeBar.tsx`
- `frontend/intent-routing-console/src/models/adminSession.ts`
- `frontend/intent-routing-console/src/services/adminServices.ts`
- `src/intent_routing/api/admin.py`

## File Structure

- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
  - Add Service creation request/response types matching `ServiceCreateRequest` and `ServiceResponse`.
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Add `createService`.
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
  - Verify `createService` calls `POST /services` with a body and no custom auth headers.
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
  - Add `canCreateServices`.
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
  - Verify only global `system_admin` can create Services.
- Create: `frontend/intent-routing-console/src/pages/Services/serviceForm.ts`
  - Keep form defaults and payload normalization testable outside React.
- Create: `frontend/intent-routing-console/src/pages/Services/serviceForm.test.ts`
  - Verify trim/default behavior.
- Create: `frontend/intent-routing-console/src/pages/Services/index.tsx`
  - Implement Services page, create form, current accessible Services table, C-2 future notice, and post-create handoff.
- Modify: `frontend/intent-routing-console/config/config.ts`
  - Add `/services` route.
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
  - Add Services navigation entry.
- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
  - Update C-1 implementation note from blocker to implemented once code is complete.
- Modify: `tests/unit/test_admin_ui_handbook_docs_contract.py`
  - Require `ONBOARDING_FLOW.md` and C-1/C-2/C-3 wording.

---

### Task 1: Frontend Service Contract And Permission Helper

**Files:**
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`

- [ ] **Step 1: Write failing frontend service and permission tests**

In `frontend/intent-routing-console/src/services/adminServices.test.ts`, add `createService` to the import list and add this test inside the existing admin service Phase 1 describe block:

```ts
  it('creates services with POST body and session-cookie auth', async () => {
    const payload: API.ServiceCreateRequest = {
      service_id: 'svc-c1-onboarding',
      display_name: 'C1 Onboarding',
      environment: 'dev',
      default_threshold_preset: 'balanced',
      max_input_tokens: 256,
    };

    await createService(payload);

    expect(requestMock).toHaveBeenCalledWith('/services', {
      method: 'POST',
      data: payload,
    });
  });
```

The import block should include `createService`:

```ts
import {
  activateRelease,
  approveExample,
  createApiKey,
  createCatalogVersion,
  createExample,
  createIntent,
  createPolicyVersion,
  createRelease,
  createService,
  createTestRun,
  fetchTestRun,
  fetchTestRunResults,
  listApiKeys,
  listCatalogVersions,
  listExamples,
  listIntentRouteCandidates,
  listPolicyVersions,
  listReleases,
  listReleaseCandidates,
  listTestRuns,
  patchIntent,
  revokeApiKey,
  rollbackRelease,
} from './adminServices';
```

In `frontend/intent-routing-console/src/models/adminSession.test.ts`, add `canCreateServices` to the import list and add these tests inside the existing admin session model helpers describe block:

```ts
  it('allows only global system admins to create services', () => {
    const session = normalizeAuthSession(currentUser, services, 'svc-a');

    expect(canCreateServices(session)).toBe(true);
  });

  it('does not allow service-scoped roles to create services', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_owner'] }],
      'svc-a',
    );

    expect(getDisplayRoles(session)).toEqual(['service_owner']);
    expect(canCreateServices(session)).toBe(false);
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts
```

Expected: FAIL because `API.ServiceCreateRequest`, `createService`, and `canCreateServices` do not exist.

- [ ] **Step 3: Add Service API types**

In `frontend/intent-routing-console/src/types/api.d.ts`, add these types after `AccessibleService`:

```ts
  type ServiceCreateRequest = {
    service_id: string;
    display_name: string;
    environment: string;
    default_threshold_preset: ThresholdPreset;
    max_input_tokens: number;
  };

  type Service = {
    service_id: string;
    display_name: string;
    environment: string;
    default_threshold_preset: string;
    max_input_tokens: number;
    status: string;
    created_by: string;
    created_at: string;
    updated_at: string;
  };
```

- [ ] **Step 4: Add `createService`**

In `frontend/intent-routing-console/src/services/adminServices.ts`, add this function after `servicePath`:

```ts
export async function createService(payload: API.ServiceCreateRequest) {
  return request<API.Service>('/services', {
    method: 'POST',
    data: payload,
  });
}
```

Do not add `Authorization`, `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope` headers.

- [ ] **Step 5: Add `canCreateServices`**

In `frontend/intent-routing-console/src/models/adminSession.ts`, add this helper after `canManageApiKeys`:

```ts
export const canCreateServices = (session: AdminSession) =>
  session.globalRoles.includes('system_admin');
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add frontend/intent-routing-console/src/types/api.d.ts frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/services/adminServices.test.ts frontend/intent-routing-console/src/models/adminSession.ts frontend/intent-routing-console/src/models/adminSession.test.ts
git commit -m "feat: add service onboarding frontend contract"
```

---

### Task 2: Service Form Payload Helper

**Files:**
- Create: `frontend/intent-routing-console/src/pages/Services/serviceForm.test.ts`
- Create: `frontend/intent-routing-console/src/pages/Services/serviceForm.ts`

- [ ] **Step 1: Write failing form helper tests**

Create `frontend/intent-routing-console/src/pages/Services/serviceForm.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  serviceFormInitialValues,
  toServiceCreateRequest,
  type ServiceFormValues,
} from './serviceForm';

describe('service onboarding form helpers', () => {
  it('provides safe defaults for C-1 Service creation', () => {
    expect(serviceFormInitialValues).toEqual({
      environment: 'dev',
      default_threshold_preset: 'balanced',
      max_input_tokens: 256,
    });
  });

  it('normalizes form values into the Admin API payload', () => {
    const values: ServiceFormValues = {
      service_id: '  dx-review-helpdesk  ',
      display_name: '  DX Review Helpdesk  ',
      environment: ' dev ',
      default_threshold_preset: 'strict',
      max_input_tokens: 512,
    };

    expect(toServiceCreateRequest(values)).toEqual({
      service_id: 'dx-review-helpdesk',
      display_name: 'DX Review Helpdesk',
      environment: 'dev',
      default_threshold_preset: 'strict',
      max_input_tokens: 512,
    });
  });

  it('falls back to the default token limit when the input is cleared', () => {
    const values: ServiceFormValues = {
      service_id: 'svc-a',
      display_name: 'Service A',
      environment: 'prod',
      default_threshold_preset: 'balanced',
      max_input_tokens: null,
    };

    expect(toServiceCreateRequest(values).max_input_tokens).toBe(256);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/pages/Services/serviceForm.test.ts
```

Expected: FAIL because `serviceForm.ts` does not exist.

- [ ] **Step 3: Implement form helper**

Create `frontend/intent-routing-console/src/pages/Services/serviceForm.ts`:

```ts
export type ServiceFormValues = {
  service_id: string;
  display_name: string;
  environment: string;
  default_threshold_preset: API.ThresholdPreset;
  max_input_tokens: number | null;
};

export const serviceFormInitialValues: Pick<
  ServiceFormValues,
  'environment' | 'default_threshold_preset' | 'max_input_tokens'
> = {
  environment: 'dev',
  default_threshold_preset: 'balanced',
  max_input_tokens: 256,
};

export const toServiceCreateRequest = (
  values: ServiceFormValues,
): API.ServiceCreateRequest => ({
  service_id: values.service_id.trim(),
  display_name: values.display_name.trim(),
  environment: values.environment.trim(),
  default_threshold_preset: values.default_threshold_preset,
  max_input_tokens: Number(
    values.max_input_tokens ?? serviceFormInitialValues.max_input_tokens,
  ),
});
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/pages/Services/serviceForm.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add frontend/intent-routing-console/src/pages/Services/serviceForm.ts frontend/intent-routing-console/src/pages/Services/serviceForm.test.ts
git commit -m "feat: add service onboarding form helper"
```

---

### Task 3: Services Page

**Files:**
- Create: `frontend/intent-routing-console/src/pages/Services/index.tsx`

- [ ] **Step 1: Create the Services page implementation**

Create `frontend/intent-routing-console/src/pages/Services/index.tsx`:

```tsx
import { useMemo, useState } from 'react';
import { history, useModel } from '@umijs/max';
import type { TableProps } from 'antd';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';
import { canCreateServices, isAdminSessionReady } from '@/models/adminSession';
import { createService } from '@/services/adminServices';
import {
  serviceFormInitialValues,
  toServiceCreateRequest,
  type ServiceFormValues,
} from './serviceForm';

const serviceIdPattern = /^[a-z][a-z0-9_-]{1,62}$/;

const serviceHelp = {
  serviceId:
    '고정 Service ID입니다. 소문자, 숫자, 하이픈, 언더스코어만 사용합니다. 예: it-helpdesk',
  displayName: '운영자가 화면에서 알아보기 쉬운 서비스 이름입니다.',
  environment: '이 Service가 사용할 환경입니다. Release와 API key environment 기준이 됩니다.',
  preset:
    '개발자가 숫자 threshold를 직접 다루지 않도록 제공하는 기본 분류 기준입니다.',
  maxInputTokens: 'runtime API가 받을 사용자 질의의 최대 token 수입니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

const environmentOptions = [
  { label: 'dev', value: 'dev' },
  { label: 'test', value: 'test' },
  { label: 'stage', value: 'stage' },
  { label: 'staging', value: 'staging' },
  { label: 'prod', value: 'prod' },
];

const presetOptions = [
  { label: 'strict', value: 'strict' },
  { label: 'balanced', value: 'balanced' },
  { label: 'exploratory', value: 'exploratory' },
];

export default function ServicesPage() {
  const { session, restoreSession, setServiceId } = useModel('adminSession');
  const [form] = Form.useForm<ServiceFormValues>();
  const [creating, setCreating] = useState(false);
  const [createdService, setCreatedService] = useState<API.Service>();
  const ready = isAdminSessionReady(session);
  const canCreate = canCreateServices(session);

  const selectedService = session.services.find(
    (service) => service.service_id === session.serviceId,
  );

  const columns = useMemo<TableProps<API.AccessibleService>['columns']>(
    () => [
      {
        title: 'Service',
        dataIndex: 'service_id',
        render: (_, row) => (
          <Space direction="vertical" size={0}>
            <Typography.Text code>{row.service_id}</Typography.Text>
            <Typography.Text type="secondary">{row.display_name}</Typography.Text>
          </Space>
        ),
      },
      {
        title: 'Environment',
        dataIndex: 'environment',
        width: 128,
        render: (_, row) => <Tag color="blue">{row.environment}</Tag>,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        width: 112,
        render: (_, row) => (
          <Tag color={row.status === 'active' ? 'green' : 'default'}>{row.status}</Tag>
        ),
      },
      {
        title: 'Roles',
        dataIndex: 'roles',
        render: (_, row) => (
          <Space wrap size={4}>
            {row.roles.map((role) => (
              <Tag key={`${row.service_id}:${role}`}>{role}</Tag>
            ))}
          </Space>
        ),
      },
      {
        title: '',
        width: 112,
        render: (_, row) => (
          <Button
            type="link"
            size="small"
            onClick={() => {
              setServiceId(row.service_id);
            }}
          >
            선택
          </Button>
        ),
      },
    ],
    [setServiceId],
  );

  const handleCreate = async (values: ServiceFormValues) => {
    setCreating(true);
    try {
      const created = await createService(toServiceCreateRequest(values));
      setCreatedService(created);
      message.success('Service가 등록되었습니다.');
      await restoreSession();
      setServiceId(created.service_id);
      form.resetFields();
      form.setFieldsValue(serviceFormInitialValues);
    } finally {
      setCreating(false);
    }
  };

  return (
    <AdminShell title="Services">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {ready ? (
          <>
            <Alert
              type="info"
              showIcon
              message="C-1 Service onboarding"
              description="Service 등록은 권한 우선 온보딩의 첫 단계입니다. 이후 C-2에서 서비스별 사용자 권한 부여 흐름이 연결됩니다."
            />
            <FutureFeatureNotice
              compact
              title="Service membership and role assignment"
              backendRequirement="C-2 role-assignment API/UI contracts are required before this console can grant service_developer, service_operator, or auditor roles."
            />
            {selectedService ? (
              <Card title="Selected Service">
                <Descriptions bordered size="small" column={{ xs: 1, md: 3 }}>
                  <Descriptions.Item label="Service ID">
                    <Typography.Text code>{selectedService.service_id}</Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Display name">
                    {selectedService.display_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="Environment">
                    <Tag color="blue">{selectedService.environment}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Status">
                    <Tag color={selectedService.status === 'active' ? 'green' : 'default'}>
                      {selectedService.status}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Roles">
                    <Space wrap size={4}>
                      {selectedService.roles.map((role) => (
                        <Tag key={`${selectedService.service_id}:${role}`}>{role}</Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ) : null}
            {canCreate ? (
              <Card title="Create Service">
                <Form<ServiceFormValues>
                  form={form}
                  layout="vertical"
                  requiredMark={false}
                  initialValues={serviceFormInitialValues}
                  onFinish={handleCreate}
                >
                  <Space wrap align="start" size={12}>
                    <Form.Item
                      name="service_id"
                      label={helpLabel('Service ID', serviceHelp.serviceId)}
                      rules={[
                        { required: true, whitespace: true, message: 'Service ID를 입력하세요.' },
                        {
                          pattern: serviceIdPattern,
                          message:
                            'Service ID는 소문자로 시작하고 소문자, 숫자, 하이픈, 언더스코어만 사용할 수 있습니다.',
                        },
                      ]}
                    >
                      <Input placeholder="it-helpdesk" style={{ width: 240 }} />
                    </Form.Item>
                    <Form.Item
                      name="display_name"
                      label={helpLabel('Display name', serviceHelp.displayName)}
                      rules={[
                        { required: true, whitespace: true, message: 'Display name을 입력하세요.' },
                      ]}
                    >
                      <Input placeholder="IT Helpdesk" style={{ width: 260 }} />
                    </Form.Item>
                    <Form.Item
                      name="environment"
                      label={helpLabel('Environment', serviceHelp.environment)}
                      rules={[
                        { required: true, whitespace: true, message: 'Environment를 선택하세요.' },
                      ]}
                    >
                      <Select
                        showSearch
                        options={environmentOptions}
                        style={{ width: 160 }}
                      />
                    </Form.Item>
                    <Form.Item
                      name="default_threshold_preset"
                      label={helpLabel('Default preset', serviceHelp.preset)}
                      rules={[{ required: true, message: 'Preset을 선택하세요.' }]}
                    >
                      <Select options={presetOptions} style={{ width: 180 }} />
                    </Form.Item>
                    <Form.Item
                      name="max_input_tokens"
                      label={helpLabel('Max input tokens', serviceHelp.maxInputTokens)}
                      rules={[{ required: true, message: 'Token limit을 입력하세요.' }]}
                    >
                      <InputNumber min={1} max={8192} style={{ width: 180 }} />
                    </Form.Item>
                  </Space>
                  <Button type="primary" htmlType="submit" loading={creating}>
                    Service 등록
                  </Button>
                </Form>
              </Card>
            ) : (
              <Alert
                type="info"
                showIcon
                message="Service creation requires system_admin"
                description="현재 계정은 접근 가능한 Service를 볼 수 있지만 신규 Service를 등록할 수 없습니다."
              />
            )}
            {createdService ? (
              <Alert
                type="success"
                showIcon
                message="Service onboarding started"
                description={
                  <Space direction="vertical" size={8}>
                    <Typography.Text>
                      {createdService.display_name} Service가 등록되었고 현재 Service scope로 선택되었습니다.
                    </Typography.Text>
                    <Button type="primary" onClick={() => history.push('/intents')}>
                      Intent Catalog로 이동
                    </Button>
                  </Space>
                }
              />
            ) : null}
            <Card title="Accessible Services">
              <Table<API.AccessibleService>
                rowKey="service_id"
                size="small"
                pagination={false}
                dataSource={session.services}
                columns={columns}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="No accessible services"
                    />
                  ),
                }}
              />
            </Card>
          </>
        ) : (
          <AdminSessionRequired />
        )}
      </Space>
    </AdminShell>
  );
}
```

- [ ] **Step 2: Run focused typecheck to catch page errors**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Expected: PASS after this task and Task 4 route wiring are both complete. If run before Task 4, page code can still typecheck because it is imported by convention only after route wiring.

- [ ] **Step 3: Commit Task 3**

```bash
git add frontend/intent-routing-console/src/pages/Services/index.tsx
git commit -m "feat: add services onboarding page"
```

---

### Task 4: Route And Navigation Wiring

**Files:**
- Modify: `frontend/intent-routing-console/config/config.ts`
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`

- [ ] **Step 1: Add Umi route**

In `frontend/intent-routing-console/config/config.ts`, add the Services route after Dashboard:

```ts
    { path: '/dashboard', component: './Dashboard' },
    { path: '/services', component: './Services' },
    { path: '/intents', component: './Intents' },
```

- [ ] **Step 2: Add Services navigation entry**

In `frontend/intent-routing-console/src/components/AdminShell.tsx`, update the icon imports:

```tsx
import {
  AuditOutlined,
  ClusterOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  KeyOutlined,
  ProfileOutlined,
  RocketOutlined,
} from '@ant-design/icons';
```

Then add Services after Dashboard in the ProLayout routes:

```tsx
            { path: '/dashboard', name: 'Dashboard', icon: <DashboardOutlined /> },
            { path: '/services', name: 'Services', icon: <ClusterOutlined /> },
            { path: '/intents', name: 'Intent Catalog', icon: <ProfileOutlined /> },
```

- [ ] **Step 3: Run typecheck**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Expected: PASS.

- [ ] **Step 4: Commit Task 4**

```bash
git add frontend/intent-routing-console/config/config.ts frontend/intent-routing-console/src/components/AdminShell.tsx
git commit -m "feat: route services onboarding page"
```

---

### Task 5: Documentation And Docs Contract

**Files:**
- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- Modify: `tests/unit/test_admin_ui_handbook_docs_contract.py`

- [ ] **Step 1: Write failing docs contract checks**

In `tests/unit/test_admin_ui_handbook_docs_contract.py`, update `test_admin_ui_v04_handbook_files_exist` to include `ONBOARDING_FLOW.md`:

```python
        "ONBOARDING_FLOW.md",
```

Add this test at the end of the file:

```python
def test_admin_ui_v04_records_authorization_first_onboarding_flow() -> None:
    onboarding = _read(V04 / "ONBOARDING_FLOW.md")
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    readme = _read(V04 / "README.md")

    for expected in (
        "C-1: Service Onboarding",
        "C-2: Service Membership, Roles, And Developer Validation",
        "C-3: Runtime Integration And Operations",
        "Service picker options come from `/me/services`",
        "Do not send `X-Admin-Token`",
    ):
        assert expected in onboarding

    assert "Authorization-first onboarding" in pattern_kit
    assert "ONBOARDING_FLOW.md" in readme
```

- [ ] **Step 2: Run docs contract to verify current documentation passes**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected: PASS if `ONBOARDING_FLOW.md` already contains the required C-flow wording. If it fails, update the doc in Step 3.

- [ ] **Step 3: Update C-1 implementation note after Services UI exists**

In `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`, replace the C-1 current implementation note with:

```markdown
Current implementation note:

- Backend `POST /admin/v1/services` exists.
- Admin UI `/services` lets `system_admin` create a Service, refresh
  server-derived Service scope, select the new Service, and continue to Intent
  Catalog.
- Service membership and role assignment remain C-2 work and must not be faked
  in C-1.
```

- [ ] **Step 4: Run docs contract**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md tests/unit/test_admin_ui_handbook_docs_contract.py
git commit -m "docs: record c1 service onboarding implementation"
```

---

### Task 6: Final Verification And Manual QA

**Files:**
- No new implementation files.

- [ ] **Step 1: Run frontend unit tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/Services/serviceForm.test.ts
```

Expected: PASS.

- [ ] **Step 2: Run frontend typecheck**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Expected: PASS.

- [ ] **Step 3: Run focused backend API verification**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_catalog_api.py::test_admin_can_create_service_and_api_key tests/integration/test_admin_catalog_api.py::test_duplicate_service_returns_conflict_and_session_recovers tests/integration/test_admin_catalog_api.py::test_non_system_admin_role_cannot_create_service_or_key -q
```

Expected: PASS. If local integration database is unavailable, record this exact command as unverified in the final implementation handoff.

- [ ] **Step 4: Run docs contracts**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_admin_workflow_candidate_contract_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Verify prohibited frontend patterns were not introduced**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/Services frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/models/adminSession.ts frontend/intent-routing-console/src/components/AdminShell.tsx frontend/intent-routing-console/config/config.ts
```

Expected: no matches.

- [ ] **Step 6: Manual browser QA**

Run local stack:

```bash
cd /home/haua/workspace/AiIntentRouting
./scripts/run_local_dev_stack.sh
```

Open:

```text
http://127.0.0.1:30140
```

Manual steps:

1. Log in as `local-admin@example.com`.
2. Open `Services` from the sidebar.
3. Create Service:
   - Service ID: `dx-review-helpdesk`
   - Display name: `DX Review Helpdesk`
   - Environment: `dev`
   - Default preset: `balanced`
   - Max input tokens: `256`
4. Confirm success alert appears.
5. Confirm Service picker shows and selects `dx-review-helpdesk`.
6. Confirm Accessible Services table includes `dx-review-helpdesk`.
7. Click `Intent Catalog로 이동`.
8. Confirm Intent Catalog loads under selected Service scope.
9. Open `Audit Logs` and confirm `service.created` is visible for `dx-review-helpdesk` if the local account has audit access for the Service.

Expected: the new Service can be created from UI without command-line setup, the selected Service scope changes to the new Service, and no C-2 role assignment controls are presented as working features.

- [ ] **Step 7: Commit verification doc/test fixes if any**

If verification requires focused fixes, commit them with a scoped message:

```bash
git add frontend/intent-routing-console docs tests
git commit -m "fix: polish c1 service onboarding"
```

---

## Acceptance Criteria

- `system_admin` can open `/services` and create a Service through the browser.
- Non-`system_admin` users can inspect accessible Services but cannot create a Service.
- The create form uses account-session auth through Umi `request`; no trusted browser headers are added.
- After creation, the Admin UI refreshes `/me/services`, selects the new Service, and offers a next action to Intent Catalog.
- Services page shows C-2 Service membership and role assignment as future/informational, not as fake state.
- Existing Intent/Test/Release/API Key pages continue using the selected Service scope.
- Documentation records C-1 as implemented and keeps C-2/C-3 as future slices.
- Focused unit, typecheck, docs, and backend contract verification pass or exact unverified commands are recorded.

## Self-Review Checklist For Implementer

- Every new browser request uses Umi `request` and the existing session cookie path.
- No `Authorization: Bearer`, `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope` header appears in frontend implementation files.
- The Services page does not grant roles, invite users, or simulate C-2 membership state.
- The Service picker still gets options from `/me/services`.
- The plan's C-1 implementation does not alter backend authorization policy.
