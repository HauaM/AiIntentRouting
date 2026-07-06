import { describe, expect, it } from 'vitest';
import {
  EMPTY_ADMIN_SESSION,
  getDisplayRoles,
  isAdminSessionReady,
  normalizeAuthSession,
  selectInitialServiceId,
  toServiceOptions,
} from './adminSession';

const currentUser: API.AdminCurrentUserResponse = {
  user: {
    user_id: 'admin-1',
    email: 'admin@example.com',
    display_name: 'Admin User',
    status: 'active',
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:00Z',
    last_login_at: '2026-07-06T01:00:00Z',
  },
  global_roles: ['system_admin'],
  service_roles: [{ service_id: 'svc-a', role: 'service_operator' }],
};

const services: API.AccessibleService[] = [
  {
    service_id: 'svc-a',
    display_name: 'Service A',
    environment: 'prod',
    status: 'active',
    roles: ['service_operator'],
  },
  {
    service_id: 'svc-b',
    display_name: 'Service B',
    environment: 'stage',
    status: 'active',
    roles: ['service_developer'],
  },
];

describe('admin session model helpers', () => {
  it('starts unauthenticated without local trusted-header defaults', () => {
    expect(EMPTY_ADMIN_SESSION).toEqual({
      authenticated: false,
      user: undefined,
      globalRoles: [],
      serviceRoles: [],
      services: [],
      serviceId: '',
    });
    expect(isAdminSessionReady(EMPTY_ADMIN_SESSION)).toBe(false);
  });

  it('normalizes the current user and accessible service response into session state', () => {
    const session = normalizeAuthSession(currentUser, services, 'svc-b');

    expect(session).toMatchObject({
      authenticated: true,
      user: currentUser.user,
      globalRoles: ['system_admin'],
      serviceRoles: [{ service_id: 'svc-a', role: 'service_operator' }],
      services,
      serviceId: 'svc-b',
    });
    expect(isAdminSessionReady(session)).toBe(true);
  });

  it('falls back to the first accessible service when the requested service is unavailable', () => {
    expect(selectInitialServiceId(services, 'missing')).toBe('svc-a');
    expect(selectInitialServiceId(services, '')).toBe('svc-a');
    expect(selectInitialServiceId([], 'missing')).toBe('');
  });

  it('uses service display names in the selector without losing service ids', () => {
    expect(toServiceOptions(services)).toEqual([
      { label: 'Service A', value: 'svc-a' },
      { label: 'Service B', value: 'svc-b' },
    ]);
  });

  it('shows global roles and current-service roles for the signed-in user', () => {
    const session = normalizeAuthSession(currentUser, services, 'svc-a');

    expect(getDisplayRoles(session)).toEqual(['system_admin', 'service_operator']);
    expect(getDisplayRoles({ ...session, serviceId: 'svc-b' })).toEqual([
      'system_admin',
      'service_developer',
    ]);
  });
});
