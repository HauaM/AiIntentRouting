# Ant Design Pro v6 셋업 가이드
## Intent Routing Service — 관리 콘솔

> **대상**: Claude Code
> **전제**: FastAPI 백엔드(v1) 완성, OpenAPI 스키마(`/openapi.json`) 접근 가능
> **환경**: 금융권 폐쇄망 — npm 외부 레지스트리 접근 불가. 사내 미러 사용.

---

## 1. 프로젝트 초기화

### 1-1. Umi 4 + Ant Design Pro v6 템플릿

```bash
# 사내 npm 미러가 설정된 환경에서
pnpm create umi@latest intent-routing-console

# 프롬프트에서:
# ✅ 템플릿 선택: ant-design-pro
# ✅ 언어: TypeScript
# ✅ 패키지 매니저: pnpm
```

또는 GitHub에서 직접 클론 후 오프라인 패키지 설치:

```bash
git clone https://github.com/ant-design/ant-design-pro.git intent-routing-console
cd intent-routing-console

# 사내 레지스트리 지정
echo "registry=https://your-internal-npm-registry.internal" > .npmrc

pnpm install
```

### 1-2. 추가 패키지 설치

```bash
pnpm add @ant-design/pro-components @ant-design/charts
pnpm add @tanstack/react-query axios
pnpm add @orioncactus/pretendard  # 폰트 로컬 설치 (CDN 대신)
pnpm add -D openapi-typescript    # API 타입 자동 생성
```

---

## 2. 디렉터리 구조

```
src/
├── access.ts              # 역할별 권한 정의
├── app.tsx                # getInitialState, request interceptor, ConfigProvider
├── theme.ts               # AntD 디자인 토큰
├── global.css             # @font-face (Pretendard), body 리셋
├── constants.ts           # API 엔드포인트, decision 색상, 공통 enum
│
├── components/
│   ├── DecisionTag/       # decision 타입 → 색상 Tag 컴포넌트
│   ├── MaskedQuery/       # masked query 표시 컴포넌트
│   ├── EnvSelector/       # 헤더 env 전환 Select
│   └── StatusTag/         # Active/Draft/Deprecated 등 상태 Tag
│
├── pages/
│   ├── Dashboard/
│   │   └── index.tsx
│   ├── IntentCatalog/
│   │   ├── index.tsx      # 목록
│   │   └── Detail.tsx     # 상세/편집
│   ├── ExamplesApproval/
│   │   └── index.tsx
│   ├── PolicyVersions/
│   │   └── index.tsx
│   ├── CSVTestRuns/
│   │   └── index.tsx
│   ├── Releases/
│   │   └── index.tsx
│   ├── RuntimeLogs/
│   │   └── index.tsx
│   ├── AuditLogs/
│   │   └── index.tsx
│   ├── SecurityKeys/
│   │   └── index.tsx
│   ├── Services/
│   │   └── index.tsx
│   ├── APIKeys/
│   │   └── index.tsx
│   └── DifyIntegration/
│       └── index.tsx
│
└── services/
    ├── api.ts             # axios 인스턴스 + 공통 헤더
    ├── intents.ts         # Intent CRUD API 함수
    ├── examples.ts
    ├── releases.ts
    ├── logs.ts
    └── types.ts           # openapi-typescript 생성 타입 (또는 수동 정의)
```

---

## 3. 핵심 설정 파일

### 3-1. `config/routes.ts`

```typescript
export default [
  {
    path: '/login',
    component: './Login',
    layout: false,
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    name: 'Dashboard',
    path: '/dashboard',
    icon: 'dashboard',
    component: './Dashboard',
    // 권한 없이 전 역할 접근 가능
  },
  {
    name: '카탈로그 관리',
    path: '/catalog',
    routes: [
      {
        name: 'Intent Catalog',
        path: '/catalog/intents',
        component: './IntentCatalog',
        access: 'canViewCatalog',
      },
      {
        name: 'Intent 편집',
        path: '/catalog/intents/:id/edit',
        component: './IntentCatalog/Detail',
        access: 'canEditCatalog',
        hideInMenu: true,
      },
      {
        name: 'Examples & Approval',
        path: '/catalog/examples',
        component: './ExamplesApproval',
        access: 'canViewCatalog',
      },
      {
        name: 'Policy Versions',
        path: '/catalog/policies',
        component: './PolicyVersions',
        access: 'canViewCatalog',
      },
    ],
  },
  {
    name: '테스트 · 배포',
    path: '/deploy',
    routes: [
      {
        name: 'CSV Test Runs',
        path: '/deploy/test-runs',
        component: './CSVTestRuns',
        access: 'canViewCatalog',
      },
      {
        name: 'Releases',
        path: '/deploy/releases',
        component: './Releases',
        access: 'canViewReleases',
      },
    ],
  },
  {
    name: '운영 모니터링',
    path: '/monitoring',
    routes: [
      {
        name: 'Runtime Logs',
        path: '/monitoring/runtime-logs',
        component: './RuntimeLogs',
        access: 'canViewLogs',
      },
    ],
  },
  {
    name: '보안 · 감사',
    path: '/security',
    routes: [
      {
        name: 'Audit Logs',
        path: '/security/audit-logs',
        component: './AuditLogs',
        access: 'canViewAudit',
      },
      {
        name: 'Security / Key Summary',
        path: '/security/keys',
        component: './SecurityKeys',
        access: 'canViewAudit',
      },
    ],
  },
  {
    name: '시스템',
    path: '/system',
    access: 'isAdmin',
    routes: [
      {
        name: 'Services',
        path: '/system/services',
        component: './Services',
      },
      {
        name: 'API Keys',
        path: '/system/api-keys',
        component: './APIKeys',
      },
      {
        name: 'Dify Integration',
        path: '/system/dify',
        component: './DifyIntegration',
      },
    ],
  },
];
```

### 3-2. `src/access.ts`

```typescript
export default function access(initialState: { currentUser?: API.CurrentUser }) {
  const { currentUser } = initialState ?? {};
  const role = currentUser?.role;

  return {
    isAdmin:        role === 'admin',
    isDeveloper:    role === 'developer',
    isOperator:     role === 'operator',
    isAuditor:      role === 'auditor',

    canViewCatalog:   ['admin', 'developer', 'operator', 'auditor'].includes(role ?? ''),
    canEditCatalog:   ['developer'].includes(role ?? ''),
    canApproveCatalog:['auditor'].includes(role ?? ''),

    canViewReleases:  ['admin', 'developer', 'operator', 'auditor'].includes(role ?? ''),
    canActivateRelease: ['admin', 'auditor'].includes(role ?? ''),

    canViewLogs:      ['admin', 'developer', 'operator', 'auditor'].includes(role ?? ''),
    canViewRawQuery:  false, // 항상 false — 2인 승인 후 API에서 열람 토큰 발급

    canViewAudit:     ['admin', 'operator', 'auditor'].includes(role ?? ''),
    canManageAudit:   ['auditor'].includes(role ?? ''),

    canManageKeys:    ['admin'].includes(role ?? ''),
  };
}
```

### 3-3. `src/theme.ts`

```typescript
import type { ThemeConfig } from 'antd';

export const theme: ThemeConfig = {
  token: {
    colorPrimary:      '#1D5A96',
    colorLink:         '#1D5A96',
    colorLinkHover:    '#2a6daa',
    colorSuccess:      '#2F8F5B',
    colorWarning:      '#D4920B',
    colorError:        '#C0392B',
    colorTextBase:     '#1C2733',
    colorBgContainer:  '#FFFFFF',
    colorBgLayout:     '#F4F6F8',
    borderRadius:      6,
    fontFamily:        "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode:    "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
    boxShadowTertiary: '0 1px 3px rgba(15,30,50,0.07)',
  },
  components: {
    Layout: {
      siderBg: '#0D2438',
    },
    Menu: {
      darkItemBg:           '#0D2438',
      darkSubMenuItemBg:    '#091D2E',
      darkItemSelectedBg:   'rgba(58,127,192,0.22)',
      darkItemSelectedColor: '#FFFFFF',
      darkItemColor:        '#AEBCCD',
      darkGroupTitleColor:  '#5D748F',
    },
    Table: {
      headerBg:     '#F7F9FB',
      headerColor:  '#64748B',
      rowHoverBg:   '#F0F5FA',
    },
    Card: {
      paddingLG: 16,
    },
  },
};
```

### 3-4. `src/app.tsx`

```typescript
import { RunTimeLayoutConfig, RequestConfig } from '@umijs/max';
import { ConfigProvider, message } from 'antd';
import koKR from 'antd/locale/ko_KR';
import { theme } from './theme';
import { getCurrentUser } from './services/api';

// 전역 초기 상태
export async function getInitialState(): Promise<{
  currentUser?: API.CurrentUser;
  currentEnv: 'prod' | 'stg';
}> {
  try {
    const currentUser = await getCurrentUser();
    return { currentUser, currentEnv: 'prod' };
  } catch {
    // 인증 실패 → 로그인 페이지로 리다이렉트는 request 인터셉터에서 처리
    return { currentEnv: 'prod' };
  }
}

// ProLayout 설정
export const layout: RunTimeLayoutConfig = ({ initialState }) => ({
  title: 'Intent Routing',
  logo: false, // 텍스트+컬러박스 커스텀 로고 컴포넌트 사용
  navTheme: 'realDark',
  layout: 'side',
  fixedHeader: true,
  fixSiderbar: true,
  siderWidth: 178,
  colorPrimary: '#1D5A96',
  // 헤더 우측: env 선택 + 사용자 아바타
  rightContentRender: () => <HeaderRight />,
  // 메뉴 하단 추가 항목 없음
});

// Axios 요청 인터셉터
export const request: RequestConfig = {
  baseURL: '/api/v1',
  timeout: 15000,
  requestInterceptors: [
    (config) => {
      const token = localStorage.getItem('access_token');
      if (token) config.headers!['Authorization'] = `Bearer ${token}`;
      // env 헤더 또는 쿼리 파라미터
      const env = localStorage.getItem('current_env') ?? 'prod';
      config.params = { ...config.params, env };
      return config;
    },
  ],
  responseInterceptors: [
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      } else if (error.response?.status === 403) {
        message.error('접근 권한이 없습니다.');
      } else {
        message.error(error.response?.data?.detail ?? '서버 오류가 발생했습니다.');
      }
      return Promise.reject(error);
    },
  ],
};

// ConfigProvider 래핑
export function rootContainer(container: React.ReactNode) {
  return (
    <ConfigProvider theme={theme} locale={koKR}>
      {container}
    </ConfigProvider>
  );
}
```

### 3-5. `src/global.css`

```css
/* Pretendard — 로컬 설치 후 node_modules에서 참조 */
@import '@orioncactus/pretendard/dist/web/static/pretendard.css';

body {
  margin: 0;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 사이드바 그룹 라벨 스타일 */
.ant-menu-item-group-title {
  font-size: 10px !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
}

/* monospace 텍스트 유틸리티 */
.text-mono {
  font-family: var(--ant-font-family-code);
  font-size: 13px;
}
```

---

## 4. FastAPI 연동

### 4-1. 타입 자동 생성

```bash
# openapi-typescript로 FastAPI 스키마에서 TS 타입 생성
npx openapi-typescript http://localhost:8000/openapi.json -o src/services/types.ts
```

폐쇄망에서는 스키마 JSON을 수동 복사:
```bash
curl http://internal-api.internal/openapi.json > openapi.json
npx openapi-typescript ./openapi.json -o src/services/types.ts
```

### 4-2. 서비스 함수 패턴 (`src/services/intents.ts`)

```typescript
import { request } from '@umijs/max';
import type { Components } from './types';

export type Intent = Components['schemas']['IntentResponse'];
export type IntentCreate = Components['schemas']['IntentCreate'];

// ProTable request 함수 — params는 ProTable이 자동 주입
export async function listIntents(params: {
  current?: number;
  pageSize?: number;
  status?: string;
  route_key?: string;
  keyword?: string;
}) {
  const { current = 1, pageSize = 10, ...filters } = params;
  const res = await request<{
    items: Intent[];
    total: number;
  }>('/intents', {
    method: 'GET',
    params: { page: current, size: pageSize, ...filters },
  });
  return {
    data: res.items,
    total: res.total,
    success: true,
  };
}

export async function getIntent(id: string) {
  return request<Intent>(`/intents/${id}`);
}

export async function createIntent(data: IntentCreate) {
  return request<Intent>('/intents', { method: 'POST', data });
}

export async function updateIntent(id: string, data: Partial<IntentCreate>) {
  return request<Intent>(`/intents/${id}`, { method: 'PATCH', data });
}

export async function publishIntent(id: string) {
  return request<Intent>(`/intents/${id}/publish`, { method: 'POST' });
}
```

---

## 5. 화면별 구현 패턴

### 5-1. Intent Catalog 목록 (`ProTable` 패턴)

```typescript
import { ProTable } from '@ant-design/pro-components';
import { Tag, Space } from 'antd';
import { listIntents } from '@/services/intents';
import { useAccess, Access } from '@umijs/max';
import DecisionTag from '@/components/DecisionTag';
import StatusTag from '@/components/StatusTag';

export default function IntentCatalog() {
  const access = useAccess();

  const columns = [
    {
      title: 'intent_id',
      dataIndex: 'intent_id',
      render: (id: string, row: any) => (
        <Space direction="vertical" size={0}>
          <span className="text-mono" style={{ fontWeight: 600, color: '#102234' }}>{id}</span>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>{row.display_name}</span>
        </Space>
      ),
    },
    {
      title: 'route_key',
      dataIndex: 'route_key',
      render: (key: string) => (
        <Tag style={{ fontFamily: 'var(--ant-font-family-code)', color: '#1D5A96', background: '#E8F0F8', border: 'none' }}>
          {key}
        </Tag>
      ),
    },
    {
      title: 'kw',
      dataIndex: 'keywords',
      render: (kw: any) => `${kw?.include?.length ?? 0}/${kw?.exclude?.length ?? 0}`,
      search: false,
    },
    {
      title: 'ex',
      dataIndex: 'example_count',
      search: false,
    },
    {
      title: 'status',
      dataIndex: 'status',
      render: (status: string) => <StatusTag status={status} />,
      valueType: 'select',
      valueEnum: {
        active:     { text: 'Active',     status: 'Success' },
        draft:      { text: 'Draft',      status: 'Warning' },
        deprecated: { text: 'Deprecated', status: 'Default' },
      },
    },
    {
      title: '작업',
      valueType: 'option',
      render: (_: any, row: any) => [
        <Access key="edit" accessible={access.canEditCatalog}>
          <a onClick={() => history.push(`/catalog/intents/${row.intent_id}/edit`)}>편집</a>
        </Access>,
        <a key="clone">복제</a>,
      ],
    },
  ];

  return (
    <ProTable
      columns={columns}
      request={listIntents}
      rowKey="intent_id"
      pagination={{ pageSize: 10, showSizeChanger: false }}
      search={{ labelWidth: 'auto' }}
      toolBarRender={() => [
        <Access key="add" accessible={access.canEditCatalog}>
          <Button type="primary" onClick={() => history.push('/catalog/intents/new')}>
            + Intent 추가
          </Button>
        </Access>,
      ]}
    />
  );
}
```

### 5-2. Intent 상세/편집 (`ProForm` 패턴)

```typescript
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea } from '@ant-design/pro-components';
import { Modal, message } from 'antd';
import { getIntent, updateIntent, publishIntent } from '@/services/intents';

export default function IntentDetail({ id }: { id: string }) {
  const [form] = ProForm.useForm();

  const onPublish = async () => {
    await form.validateFields();
    Modal.confirm({
      title: '검토 요청 (Publish)',
      content: '임베딩 재생성이 트리거됩니다. 승인 후 배포 가능합니다.',
      okText: '요청',
      cancelText: '취소',
      onOk: async () => {
        await publishIntent(id);
        message.success('검토 요청이 완료되었습니다.');
      },
    });
  };

  return (
    <ProForm
      form={form}
      request={async () => getIntent(id)}
      onFinish={async (values) => {
        await updateIntent(id, values);
        message.success('임시저장되었습니다.');
        return true;
      }}
      submitter={{
        render: () => [
          <Button key="save" onClick={() => form.submit()}>임시저장</Button>,
          <Button key="publish" type="primary" onClick={onPublish}>검토 요청 (Publish)</Button>,
        ],
      }}
    >
      <ProFormText name="intent_id" label="intent_id" disabled />
      <ProFormSelect name="route_key" label="route_key"
        request={async () => routeKeys.map(k => ({ label: k, value: k }))} />
      <ProFormTextArea name="description" label="설명" />
      {/* include/exclude keywords: Select mode="tags" */}
      <ProFormSelect name="include_keywords" label="include keywords"
        mode="tags" fieldProps={{ tokenSeparators: [',', ' '] }} />
      <ProFormSelect name="exclude_keywords" label="exclude keywords"
        mode="tags" fieldProps={{ tokenSeparators: [',', ' '] }} />
      <ProFormSelect name="threshold_preset" label="threshold preset"
        options={[{ label: 'standard (0.72)', value: 'standard' }, { label: 'strict (0.85)', value: 'strict' }]} />
    </ProForm>
  );
}
```

### 5-3. Runtime Logs — 마스킹 처리

```typescript
// src/components/MaskedQuery/index.tsx
// query는 API에서 이미 서버 측 마스킹 처리된 값을 표시.
// 원문 열람은 별도 API 엔드포인트 + 감사 승인 토큰 필요.

const MaskedQuery = ({ maskedText }: { maskedText: string }) => (
  <span style={{ letterSpacing: '0.05em', color: '#334155' }}>
    {maskedText}  {/* 예: "카드 한도 ●●● 올려줘" */}
  </span>
);

// ProTable에서 risk 행 강조
const rowClassName = (record: RuntimeLog) =>
  record.decision === 'risk' ? 'row-risk' : '';

// global.css에 추가:
// .row-risk { background: #FDF6F5 !important; }
```

### 5-4. Audit Logs — 읽기 전용 + 2인 승인

```typescript
// raw query 조회 승인 대기 배너
const ApprovalBanner = ({ requests, onApprove, onReject }) => (
  requests.length > 0 ? (
    <Alert
      type="warning"
      message={`raw query 조회 승인 대기 (${requests.length})`}
      description={`요청자: ${requests[0].requester} · trace: ${requests[0].trace_id} · 사유: ${requests[0].reason}`}
      action={
        <Space>
          <Button size="small" type="primary" onClick={() => onApprove(requests[0].id)}>승인</Button>
          <Button size="small" danger onClick={() => onReject(requests[0].id)}>거부</Button>
        </Space>
      }
    />
  ) : null
);

// 거부 시 사유 입력 모달
const onReject = (requestId: string) => {
  let reason = '';
  Modal.confirm({
    title: '거부 사유 입력',
    content: <Input.TextArea onChange={(e) => reason = e.target.value} placeholder="거부 사유를 입력하세요 (필수)" />,
    okButtonProps: { disabled: !reason },
    onOk: async () => {
      if (!reason) return Promise.reject('사유를 입력하세요');
      await rejectRawQueryRequest(requestId, reason);
    },
  });
};
```

---

## 6. Decision Tag 공통 컴포넌트

```typescript
// src/components/DecisionTag/index.tsx
import { Tag } from 'antd';

const decisionColors: Record<string, { bg: string; color: string; label: string }> = {
  confident: { bg: '#E8F5EE', color: '#1F7A4D', label: 'confident' },
  clarify:   { bg: '#FBF2E0', color: '#B97A09', label: 'clarify'   },
  fallback:  { bg: '#EEF1F4', color: '#5A7A99', label: 'fallback'  },
  off_topic: { bg: '#EEF1F4', color: '#64748B', label: 'off_topic' },
  risk:      { bg: '#FBEAEA', color: '#C0392B', label: 'risk'      },
};

export default function DecisionTag({ decision }: { decision: string }) {
  const cfg = decisionColors[decision] ?? { bg: '#EEF1F4', color: '#64748B', label: decision };
  return (
    <Tag style={{ background: cfg.bg, color: cfg.color, border: 'none', fontWeight: 700, borderRadius: 4 }}>
      {cfg.label}
    </Tag>
  );
}
```

---

## 7. 폐쇄망 체크리스트

| 항목 | 조치 |
|---|---|
| npm 레지스트리 | `.npmrc`에 사내 미러 URL 설정 |
| Pretendard 폰트 | `@orioncactus/pretendard` npm 패키지 로컬 설치, CDN 참조 제거 |
| @ant-design/icons | 번들 포함 (외부 CDN 없음, 기본 OK) |
| @ant-design/charts | 로컬 설치. ECharts 런타임 CDN 로드 설정 제거 (`ECHARTS_THEME` 환경변수 확인) |
| openapi-typescript | 스키마 JSON 파일로 오프라인 생성 |
| 지도/외부 API | 미사용 |
| Umi 빌드 아웃풋 | `dist/` 폴더를 Nginx/내부 웹서버로 서빙 |
| CSP 헤더 | `script-src 'self'`만 허용. CDN 제거 후 통과 확인 |

---

## 8. 구현 순서 (권장)

**Phase 1: 셸 + 인증 (1~2일)**
1. 프로젝트 초기화 + `.npmrc` 설정
2. `theme.ts` ConfigProvider 적용 → 네이비 토큰 확인
3. `app.tsx` `getInitialState` + 로그인/토큰 플로우
4. `access.ts` 역할 정의 + `config/routes.ts`
5. ProLayout 사이드바 다크 테마 + 로고 + env 선택

**Phase 2: Intent Catalog (2~3일)**
1. `listIntents` 서비스 함수 + ProTable 목록 (필터/페이지네이션)
2. 상세/편집 ProForm + 임시저장/Publish 플로우
3. StatusTag / include·exclude keywords Tag input

**Phase 3: 로그 + Dashboard (2~3일)**
1. Runtime Logs ProTable + 마스킹 + 행 클릭 Drawer
2. Dashboard 스탯 타일 + Decision 분포 바 + Latency 차트

**Phase 4: 승인·배포·감사 (3~4일)**
1. Examples & Approval Steps + 일괄 승인 Modal.confirm
2. Releases Steps 마법사 + 활성화 확인 + 이력 테이블
3. Audit Logs 읽기전용 ProTable + 2인 승인 배너
4. API Keys / Services / Policy Versions (Phase 2 패턴 재사용)

---

## 9. 주의사항 요약

- **raw query는 절대 프론트엔드에서 마스킹하지 않는다.** 서버에서 마스킹된 값을 수신·표시. 원문 열람은 별도 엔드포인트 + 시한부 토큰 방식.
- **되돌릴 수 없는 작업**(release 활성화, key revoke, example 일괄 승인)은 반드시 `Modal.confirm` + 영향 범위 요약 텍스트 포함.
- **감사 로그 화면에는 수정/삭제 버튼을 두지 않는다.** ProTable `toolBarRender={() => false}` 또는 작업 컬럼 미포함.
- **env 전환 시** 모든 React Query 캐시 무효화 (`queryClient.invalidateQueries()`).
- **사이드 메뉴** 역할별 `access` 설정이 누락되면 Umi가 해당 경로를 숨기지 않음 — 반드시 `routes.ts`의 `access` 키와 `access.ts` 반환 키를 일치시킬 것.
