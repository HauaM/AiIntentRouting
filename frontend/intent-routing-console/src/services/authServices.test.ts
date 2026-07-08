import { request } from '@umijs/max';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchCurrentAdminUser,
  listAccessibleServices,
  loginAdmin,
  logoutAdmin,
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
});
