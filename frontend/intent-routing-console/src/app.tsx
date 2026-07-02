import type { RequestConfig, RequestError } from '@umijs/max';
import { message } from 'antd';
import { readAdminSession } from './models/adminSession';

const errorMessage = (error: any) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.error?.message) return detail.error.message;
  return error?.message || '서버 오류가 발생했습니다.';
};

export async function getInitialState() {
  return readAdminSession();
}

export const request: RequestConfig = {
  baseURL: '/admin/v1',
  timeout: 15000,
  requestInterceptors: [
    (config: RequestConfig) => {
      const session = readAdminSession();
      const headers = (config.headers ?? {}) as Record<string, unknown>;
      config.headers = {
        ...headers,
        'X-Admin-Token': session.adminToken,
        'X-Actor-Id': session.actorId,
        'X-Actor-Roles': session.actorRoles.join(','),
        'X-Service-Scope': session.serviceScope,
      } as RequestConfig['headers'];
      return config;
    },
  ],
  errorConfig: {
    errorHandler: (error: RequestError) => {
      const requestError = error as any;
      if (requestError?.response?.status === 403) {
        message.error('접근 권한이 없습니다.');
      } else {
        message.error(errorMessage(error));
      }
    },
  },
};
