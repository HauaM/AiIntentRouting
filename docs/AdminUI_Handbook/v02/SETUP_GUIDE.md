# Ant Design Pro v6 셋업 가이드
## Intent Routing Service — Admin Console

> **대상**: Claude Code
> **현재 상태**: API-only MVP / Sprint 5 파일럿 리허설 단계
> **Admin UI 구현 단계**: Phase 0(Read-first) → Phase 1(Write) → Phase 2(Governed, 🔮 Future)
> **전제**: 모든 Admin API는 `/admin/v1/services/{service_id}/...` 경로를 사용합니다.

---

## 1. 프로젝트 초기화

```bash
# 사내 npm 미러 설정 후
pnpm create umi@latest intent-routing-console
# 선택: ant-design-pro / TypeScript / pnpm

# 추가 패키지
pnpm add @ant-design/pro-components @ant-design/charts
pnpm add @tanstack/react-query axios
pnpm add @orioncactus/pretendard   # CDN 금지 — 로컬 설치
pnpm add -D openapi-typescript
```

폐쇄망 `.npmrc`:
```
registry=https://your-internal-npm-registry.internal
```

---

## 2. 인증 헤더 모델

현재 Admin API는 JWT Bearer 가 아닌 **커스텀 헤더** 방식을 사용합니다.

```
X-Admin-Token:   <admin_token>
X-Actor-Id:      <user_id>
X-Actor-Roles:   system_admin,service_developer
X-Service-Scope: <service_id>
```

> ⚠️ `Authorization: Bearer` 패턴은 현재 Admin API와 맞지 않습니다. 위 헤더만 사용하세요.

---

## 3. 핵심 설정 파일

### `src/app.tsx` — request 인터셉터

```typescript
import type { RequestConfig } from '@umijs/max';

export const request: RequestConfig = {
  baseURL: '/admin/v1',
  timeout: 15000,
  requestInterceptors: [
    (config) => {
      const token   = localStorage.getItem('admin_token') ?? '';
      const actorId = localStorage.getItem('actor_id') ?? '';
      const roles   = localStorage.getItem('actor_roles') ?? '';
      const svcId   = localStorage.getItem('service_scope') ?? '';

      config.headers!['X-Admin-Token']   = token;
      config.headers!['X-Actor-Id']      = actorId;
      config.headers!['X-Actor-Roles']   = roles;
      config.headers!['X-Service-Scope'] = svcId;
      return config;
    },
  ],
  responseInterceptors: [
    (response) => response,
    (error) => {
      if (error.response?.status === 401) window.location.href = '/login';
      else if (error.response?.status === 403) message.error('접근 권한이 없습니다.');
      else message.error(error.response?.data?.detail ?? '서버 오류');
      return Promise.reject(error);
    },
  ],
};
```

### `src/access.ts` — 역할 기반 권한

```typescript
export default function access(initialState: { currentUser?: API.CurrentUser }) {
  const roles: string[] = initialState?.currentUser?.roles ?? [];
  const has = (r: string) => roles.includes(r);

  return {
    isAdmin:       has('system_admin'),
    isDeveloper:   has('service_developer'),
    isOperator:    has('service_operator'),
    isAuditor:     has('auditor'),

    // Phase 0
    canViewDashboard:  true,
    canViewLogs:       true,
    canViewAudit:      true,
    canViewCatalog:    true,

    // Phase 1
    canEditCatalog:    has('service_developer'),
    canApproveExample: has('auditor'),
    canActivateRelease:has('system_admin') || has('auditor'),
    canRollbackRelease:has('system_admin') || has('auditor'),
    canManageKeys:     has('system_admin'),

    // Phase 2 — 모두 false (future backend required)
    canViewRawQuery:   false,
    canPublishIntent:  false,
    canRejectExample:  false,
  };
}
```

### `src/theme.ts`

```typescript
import type { ThemeConfig } from 'antd';

export const theme: ThemeConfig = {
  token: {
    colorPrimary:      '#1D5A96',
    colorLink:         '#1D5A96',
    colorSuccess:      '#2F8F5B',
    colorWarning:      '#D4920B',
    colorError:        '#C0392B',
    colorTextBase:     '#1C2733',
    colorBgContainer:  '#FFFFFF',
    colorBgLayout:     '#F4F6F8',
    borderRadius:      6,
    fontFamily:        "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode:    "'JetBrains Mono', ui-monospace, monospace",
  },
  components: {
    Layout: { siderBg: '#0D2438' },
    Menu: {
      darkItemBg:           '#0D2438',
      darkSubMenuItemBg:    '#091D2E',
      darkItemSelectedBg:   'rgba(58,127,192,0.22)',
      darkItemSelectedColor:'#FFFFFF',
      darkItemColor:        '#AEBCCD',
    },
    Table: { headerBg: '#F7F9FB', headerColor: '#64748B', rowHoverBg: '#F0F5FA' },
  },
};
```

### `src/global.css`

```css
/* 로컬 설치 — CDN 절대 사용 금지 (폐쇄망) */
@import '@orioncactus/pretendard/dist/web/static/pretendard.css';

body { margin: 0; -webkit-font-smoothing: antialiased; }
.text-mono { font-family: var(--ant-font-family-code); font-size: 13px; }
.row-risk  { background: #FDF6F5 !important; }
```

---

## 4. 실제 API 경로 (service_id 필수)

모든 경로는 `/admin/v1/services/{service_id}/` 하위에 있습니다.
`service_id`는 전역 Context(헤더 `X-Service-Scope`)로 관리합니다.

| 기능 | Method | 경로 |
|---|---|---|
| Intent 목록 | GET | `/services/{sid}/intents` |
| Intent 상세 | GET | `/services/{sid}/intents/{intent_id}` |
| Intent 생성 | POST | `/services/{sid}/intents` |
| Intent 수정 | PATCH | `/services/{sid}/intents/{intent_id}` |
| Example 목록 | GET | `/services/{sid}/intents/{intent_id}/examples` |
| Example approve | POST | `/services/{sid}/examples/{example_id}:approve` |
| Policy Version 생성 | POST | `/services/{sid}/policy-versions` |
| Catalog Version 생성 | POST | `/services/{sid}/catalog-versions` |
| Test Run 생성 | POST | `/services/{sid}/test-runs` |
| Test Run 결과 | GET | `/services/{sid}/test-runs/{run_id}` |
| Release 목록 | GET | `/services/{sid}/releases` |
| Release 생성 | POST | `/services/{sid}/releases` |
| Release activate | POST | `/services/{sid}/releases/{version}:activate` |
| Release rollback | POST | `/services/{sid}/releases/{version}:rollback` |
| Runtime Logs | GET | `/services/{sid}/runtime-logs` |
| Runtime Metrics | GET | `/services/{sid}/runtime-metrics` |
| Audit Logs | GET | `/services/{sid}/audit-logs` |

---

## 5. 서비스 함수 패턴

```typescript
// src/services/intents.ts
import { request } from '@umijs/max';

const base = (sid: string) => `/services/${sid}/intents`;

export async function listIntents(serviceId: string, params: {
  page?: number; size?: number; status?: string; route_key?: string;
}) {
  return request<{ items: API.Intent[]; total: number }>(base(serviceId), {
    method: 'GET',
    params: { page: params.page ?? 1, size: params.size ?? 20, ...params },
  });
}

export async function activateRelease(serviceId: string, version: string) {
  return request(`/services/${serviceId}/releases/${version}:activate`, { method: 'POST' });
}

export async function approveExample(serviceId: string, exampleId: string) {
  return request(`/services/${serviceId}/examples/${exampleId}:approve`, { method: 'POST' });
}
```

---

## 6. 화면별 핵심 패턴

### Phase 0 — Runtime Logs (마스킹)

```typescript
// masked query는 서버에서 이미 마스킹된 값을 그대로 표시
// 프론트엔드에서 마스킹 로직 구현 금지
const columns = [
  {
    title: 'masked query',
    dataIndex: 'masked_query',  // 서버 응답 필드명 확인 필요
    render: (text: string) => (
      <span style={{ letterSpacing: '0.05em', color: '#334155' }}>{text}</span>
    ),
  },
];

// risk 행 강조
const rowClassName = (record: API.RuntimeLog) =>
  record.decision === 'risk' ? 'row-risk' : '';
```

### Phase 0 — Audit Logs (읽기 전용 강제)

```typescript
<ProTable
  columns={auditColumns}
  request={fetchAuditLogs}
  toolBarRender={() => false}   // 추가/편집 버튼 없음
  search={false}                // 기간·actor 필터는 별도 컴포넌트로
  pagination={{ pageSize: 20 }}
/>
// 하단 고지 필수:
// "append-only · 변경 불가 · 보존 7년"
```

### Phase 1 — Destructive Action (Modal.confirm 필수)

```typescript
// release activate
const handleActivate = (version: string) => {
  Modal.confirm({
    title: 'Release 활성화',
    content: `${version}을 prod에 활성화합니다. 현재 활성 release가 대체됩니다.`,
    okText: '활성화',
    okButtonProps: { danger: false, type: 'primary' },
    cancelText: '취소',
    onOk: async () => {
      await activateRelease(serviceId, version);
      message.success('활성화되었습니다.');
      reload();
    },
  });
};

// API key revoke
const handleRevoke = (keyId: string, keyLabel: string) => {
  Modal.confirm({
    title: 'API Key 회수',
    content: `"${keyLabel}" 키를 즉시 회수합니다. 연결된 서비스 호출이 차단됩니다.`,
    okText: '회수',
    okButtonProps: { danger: true },
    onOk: async () => { await revokeKey(keyId); },
  });
};
```

### Phase 2 — Future 기능 UI 처리

Phase 2 기능(raw query 원문 조회, publish pending, example 반려 등)은 UI에 진입점을 두되 실행 시 안내 메시지로 처리합니다:

```typescript
const handleRawQueryView = () => {
  message.info('raw query 원문 조회는 2인 승인 시스템 구축 후 지원 예정입니다.');
};
```

---

## 7. 폐쇄망 체크리스트

| 항목 | 조치 |
|---|---|
| npm 레지스트리 | `.npmrc`에 사내 미러 URL 설정 |
| Pretendard 폰트 | `@orioncactus/pretendard` 로컬 설치, **CDN 참조 전면 금지** |
| @ant-design/charts | 로컬 설치. ECharts CDN 로드 설정 제거 |
| openapi-typescript | JSON 파일로 오프라인 생성 (`openapi.json` 수동 복사) |
| CSP 헤더 | `script-src 'self'` 만 허용 확인 |
| Umi 빌드 | `dist/` → 내부 Nginx 서빙 |
| support.js | Umi 빌드 시 자동 번들됨 (별도 배포 불필요) |

---

## 8. 구현 순서

### Phase 0 (Read-first) — 먼저 구현
1. Umi 초기화 + `.npmrc` + ConfigProvider 네이비 토큰
2. `app.tsx` 커스텀 헤더 인터셉터 (X-Admin-Token 등)
3. `access.ts` 역할 정의 + `config/routes.ts`
4. ProLayout 다크 사이드바 + service_id Context
5. **Runtime Logs** — masked query ProTable + Drawer
6. **Audit Logs** — 읽기 전용 ProTable + append-only 고지
7. **Dashboard** — runtime-metrics 스탯 타일 + 차트
8. **Intent Catalog 조회** — ProTable 목록 + 상세 읽기

### Phase 1 (Write) — Phase 0 완성 후
9. Intent 생성/수정 ProForm
10. Example approve (Modal.confirm)
11. Release 생성/activate/rollback (Modal.confirm)
12. API Key 생성/revoke (Modal.confirm)
13. Policy Version / Catalog Version 생성
14. CSV Test Run 생성·결과 조회

### Phase 2 (🔮 Future) — 백엔드 계약 후
- Publish pending 상태 / Example 반려
- raw query 2인 승인 대기열
- Release diff 뷰 / CSV export
- 서버 페이지네이션 / 복합 필터 / Live polling

---

## 9. 주의사항

- **raw query는 서버에서 마스킹된 값만 표시.** 프론트 마스킹 로직 구현 금지.
- **Audit Logs에 수정/삭제 버튼 없음.** `toolBarRender={() => false}` 필수.
- **Destructive action은 반드시 `Modal.confirm`.** 1-클릭 실행 금지.
- **Phase 2 기능은 UI에 진입점만 두고 미구현 안내 처리.** 가짜 구현 금지.
- **env 전환 시 전체 캐시 무효화** (`queryClient.invalidateQueries()`).
- **`X-Service-Scope` 헤더 누락 시** API 403. 전역 Context에서 반드시 주입.
