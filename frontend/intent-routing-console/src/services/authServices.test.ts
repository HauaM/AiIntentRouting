import { request } from '@umijs/max';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchCurrentAdminUser,
  listAccessibleServices,
  listPublicDepartments,
  loginAdmin,
  logoutAdmin,
  submitAdminAccessRequest,
} from './authServices';

vi.mock('@umijs/max', () => ({
  request: vi.fn(),
}));

const requestMock = vi.mocked(request);

describe('auth service cookie session requests', () => {
  beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockResolvedValue({});
  });

  it('logs in with POST payload and cookie credentials', async () => {
    const payload: API.AdminLoginRequest = {
      email: 'admin@example.com',
      password: 'correct-horse-battery-staple',
    };

    await loginAdmin(payload);

    expect(requestMock).toHaveBeenCalledWith('/auth/login', {
      method: 'POST',
      data: payload,
      withCredentials: true,
    });
  });

  it('logs out with cookie credentials', async () => {
    await logoutAdmin();

    expect(requestMock).toHaveBeenCalledWith('/auth/logout', {
      method: 'POST',
      withCredentials: true,
    });
  });

  it('fetches the current admin user with cookie credentials', async () => {
    await fetchCurrentAdminUser();

    expect(requestMock).toHaveBeenCalledWith('/auth/me', {
      method: 'GET',
      withCredentials: true,
    });
  });

  it('fetches accessible services with cookie credentials', async () => {
    await listAccessibleServices();

    expect(requestMock).toHaveBeenCalledWith('/me/services', {
      method: 'GET',
      withCredentials: true,
    });
  });

  it('submits a public admin access request without auth headers', async () => {
    const payload: API.AdminAccessRequestCreateRequest = {
      user_number: '21P0031',
      name: '홍길동',
      department_id: 'dept-1',
      email: 'admin.user@example.com',
      password: 'correct-horse-battery-staple',
      access_reason: 'Need Admin UI access for onboarding',
    };

    await submitAdminAccessRequest(payload);

    expect(requestMock).toHaveBeenCalledWith('/admin-access-requests', {
      method: 'POST',
      data: payload,
      withCredentials: false,
    });
    const [, options] = requestMock.mock.calls[0] as unknown as [
      string,
      Record<string, unknown>,
    ];
    expect(options).not.toHaveProperty('headers');
    expect(options).toHaveProperty('withCredentials', false);
  });

  it('lists public departments without cookie credentials', async () => {
    await listPublicDepartments({ query: '개발', limit: 20 });

    expect(requestMock).toHaveBeenCalledWith('/public/departments', {
      method: 'GET',
      params: { query: '개발', limit: 20 },
      withCredentials: false,
    });
  });
});
