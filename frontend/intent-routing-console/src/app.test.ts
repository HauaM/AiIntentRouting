import { history } from '@umijs/max';
import { message } from 'antd';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { request } from './app';

vi.mock('@umijs/max', () => ({
  history: {
    location: {
      pathname: '/login',
      search: '',
    },
    replace: vi.fn(),
  },
}));

vi.mock('antd', () => ({
  message: {
    error: vi.fn(),
  },
}));

const historyMock = vi.mocked(history);
const messageMock = vi.mocked(message);

const handleRequestError = (pathname: string, search = '') => {
  historyMock.location.pathname = pathname;
  historyMock.location.search = search;
  const errorHandler = request.errorConfig?.errorHandler;
  if (!errorHandler) throw new Error('request error handler is not configured');
  errorHandler(
    {
      response: { status: 401 },
    } as any,
    {} as any,
  );
};

describe('admin request error handling', () => {
  beforeEach(() => {
    historyMock.location.pathname = '/login';
    historyMock.location.search = '';
    vi.mocked(historyMock.replace).mockReset();
    vi.mocked(messageMock.error).mockReset();
  });

  it('keeps the public admin access request page open on session restore 401', () => {
    handleRequestError('/admin-access-request');

    expect(historyMock.replace).not.toHaveBeenCalled();
  });

  it('redirects protected pages to login with the original path', () => {
    handleRequestError('/dashboard', '?tab=overview');

    expect(historyMock.replace).toHaveBeenCalledWith(
      '/login?redirect=%2Fdashboard%3Ftab%3Doverview',
    );
  });
});
