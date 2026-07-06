import type { RequestConfig, RequestError } from '@umijs/max';
import { history } from '@umijs/max';
import { message } from 'antd';

const errorMessage = (error: any) => {
  const payload = error?.response?.data ?? error?.data;
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.error?.message) return detail.error.message;
  if (payload?.error?.message) return payload.error.message;
  return error?.message || '서버 오류가 발생했습니다.';
};

export async function getInitialState() {
  return {};
}

export const request: RequestConfig = {
  baseURL: '/admin/v1',
  timeout: 15000,
  withCredentials: true,
  errorConfig: {
    errorHandler: (error: RequestError) => {
      const requestError = error as any;
      if (requestError?.response?.status === 401) {
        if (history.location.pathname !== '/login') {
          history.replace(
            `/login?redirect=${encodeURIComponent(
              `${history.location.pathname}${history.location.search}`,
            )}`,
          );
        }
      } else if (requestError?.response?.status === 403) {
        message.error('접근 권한이 없습니다.');
      } else {
        message.error(errorMessage(error));
      }
    },
  },
};
