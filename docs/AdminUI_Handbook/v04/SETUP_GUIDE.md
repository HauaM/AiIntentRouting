# Admin Console v04 Setup Guide

## Dependencies

```bash
pnpm create umi@latest intent-routing-console
pnpm add @ant-design/pro-components @ant-design/charts
pnpm add @orioncactus/pretendard
pnpm add -D openapi-typescript
```

Do not install React Query or axios for the default Admin Console implementation.

## App Configuration

Use `/admin/v1` as the request base URL and include the server-issued
`irt_admin_session` HttpOnly cookie on normal Admin UI requests. The Admin UI
must not store or inject actor headers in localStorage.

```ts
import type { RequestConfig, RequestError } from '@umijs/max';
import { history } from '@umijs/max';
import { message } from 'antd';

export const request: RequestConfig = {
  baseURL: '/admin/v1',
  timeout: 15000,
  withCredentials: true,
  errorConfig: {
    errorHandler: (error: RequestError) => {
      const requestError = error as any;
      if (requestError?.response?.status === 401) {
        history.replace('/login');
      } else if (requestError?.response?.status === 403) {
        message.error('접근 권한이 없습니다.');
      } else {
        message.error('서버 오류가 발생했습니다.');
      }
    },
  },
};
```

Auth service functions should use Umi `request`:

```ts
export async function loginAdmin(payload: API.AdminLoginRequest) {
  return request<API.AdminCurrentUserResponse>('/auth/login', {
    method: 'POST',
    data: payload,
    withCredentials: true,
  });
}

export async function fetchCurrentAdminUser() {
  return request<API.AdminCurrentUserResponse>('/auth/me', {
    method: 'GET',
    withCredentials: true,
  });
}

export async function listAccessibleServices() {
  return request<API.AccessibleService[]>('/me/services', {
    method: 'GET',
    withCredentials: true,
  });
}
```

## Implementation Order

1. Copy `examples/adminServices.ts`.
2. Add login, authenticated session restore, `AdminShell`, and `ServiceScopeBar`.
3. Build Phase 0 read screens.
4. Add Phase 1 write actions after read screens and account RBAC are stable.
5. Render Phase 2 features with `FutureFeatureNotice` until backend contracts exist.
