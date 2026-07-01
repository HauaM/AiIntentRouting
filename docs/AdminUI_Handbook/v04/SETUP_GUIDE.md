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

Use `/admin/v1` as the request base URL and inject the current Admin API headers from Umi `initialState`, `useModel`, or a small auth/session store.

```ts
import type { RequestConfig } from '@umijs/max';
import { message } from 'antd';

export const request: RequestConfig = {
  baseURL: '/admin/v1',
  timeout: 15000,
  requestInterceptors: [
    (config) => {
      const token = localStorage.getItem('admin_token') ?? '';
      const actorId = localStorage.getItem('actor_id') ?? '';
      const roles = localStorage.getItem('actor_roles') ?? '';
      const serviceScope = localStorage.getItem('service_scope') ?? '';

      config.headers!['X-Admin-Token'] = token;
      config.headers!['X-Actor-Id'] = actorId;
      config.headers!['X-Actor-Roles'] = roles;
      config.headers!['X-Service-Scope'] = serviceScope;
      return config;
    },
  ],
  responseInterceptors: [
    (response) => response,
    (error) => {
      if (error.response?.status === 403) message.error('접근 권한이 없습니다.');
      else message.error(error.response?.data?.detail ?? '서버 오류');
      return Promise.reject(error);
    },
  ],
};
```

## Implementation Order

1. Copy `examples/adminServices.ts`.
2. Add `AdminShell` and `ServiceScopeBar`.
3. Build Phase 0 read screens.
4. Add Phase 1 write actions only after read screens are stable.
5. Render Phase 2 features with `FutureFeatureNotice`.

