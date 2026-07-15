import { describe, expect, it } from 'vitest';
import type { AdminSession } from './adminSession';
import {
  EMPTY_ADMIN_SESSION,
  canCreateServices,
  canEditCatalog,
  canManageApiKeys,
  canManageReleases,
  canManageRuntimeSetup,
  canManageServiceMembers,
  canSelectServiceFromScope,
  canUseServicesPage,
  getDisplayRoles,
  hasAnyDisplayRole,
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

  it('allows global system admins to open Services before any service exists', () => {
    const session = normalizeAuthSession(currentUser, [], '');

    expect(isAdminSessionReady(session)).toBe(false);
    expect(canUseServicesPage(session)).toBe(true);
  });

  it('requires a selected accessible service for non-system-admin Services access', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [],
      '',
    );

    expect(canUseServicesPage(session)).toBe(false);
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

  it('allows service developers to edit the selected service catalog', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      services,
      'svc-b',
    );

    expect(getDisplayRoles(session)).toEqual(['service_developer']);
    expect(hasAnyDisplayRole(session, ['service_developer'])).toBe(true);
    expect(canEditCatalog(session)).toBe(true);
  });

  it('allows service owners to edit the selected service catalog', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_owner'] }],
      'svc-a',
    );

    expect(getDisplayRoles(session)).toEqual(['service_owner']);
    expect(canEditCatalog(session)).toBe(true);
  });

  it('does not allow service operators to edit the catalog', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      services,
      'svc-a',
    );

    expect(getDisplayRoles(session)).toEqual(['service_operator']);
    expect(canEditCatalog(session)).toBe(false);
  });

  it('allows system admins to manage releases and API keys', () => {
    const session = normalizeAuthSession(currentUser, services, 'svc-a');

    expect(canManageReleases(session)).toBe(true);
    expect(canManageApiKeys(session)).toBe(true);
    expect(canManageRuntimeSetup(session)).toBe(true);
  });

  it('allows selected service owners and developers to manage releases and API keys', () => {
    const serviceOwnerSession = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_owner'] }],
      'svc-a',
    );
    const serviceDeveloperSession = normalizeAuthSession(
      { ...currentUser, global_roles: ['application_admin'], service_roles: [] },
      [{ ...services[1], roles: ['service_developer'] }],
      'svc-b',
    );

    expect(canManageReleases(serviceOwnerSession)).toBe(true);
    expect(canManageApiKeys(serviceOwnerSession)).toBe(true);
    expect(canManageRuntimeSetup(serviceOwnerSession)).toBe(true);
    expect(canManageReleases(serviceDeveloperSession)).toBe(true);
    expect(canManageApiKeys(serviceDeveloperSession)).toBe(true);
    expect(canManageRuntimeSetup(serviceDeveloperSession)).toBe(true);
  });

  it('does not allow read-only service roles to manage releases or API keys', () => {
    const serviceOperatorSession = normalizeAuthSession(
      { ...currentUser, global_roles: ['application_admin'], service_roles: [] },
      [{ ...services[0], roles: ['service_operator'] }],
      'svc-a',
    );
    const auditorSession = normalizeAuthSession(
      { ...currentUser, global_roles: ['application_admin'], service_roles: [] },
      [{ ...services[0], roles: ['auditor'] }],
      'svc-a',
    );

    expect(canManageReleases(serviceOperatorSession)).toBe(false);
    expect(canManageApiKeys(serviceOperatorSession)).toBe(false);
    expect(canManageRuntimeSetup(serviceOperatorSession)).toBe(false);
    expect(canManageReleases(auditorSession)).toBe(false);
    expect(canManageApiKeys(auditorSession)).toBe(false);
    expect(canManageRuntimeSetup(auditorSession)).toBe(false);
  });

  it('does not let application_admin alone manage service-scoped actions', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: ['application_admin'], service_roles: [] },
      [],
      '',
    );

    expect(canManageReleases(session)).toBe(false);
    expect(canManageApiKeys(session)).toBe(false);
    expect(canManageRuntimeSetup(session)).toBe(false);
  });

  it('allows only global system admins to create services', () => {
    const session = normalizeAuthSession(currentUser, services, 'svc-a');

    expect(canCreateServices(session)).toBe(true);
  });

  it('does not allow service-scoped roles to create services', () => {
    const session = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_owner'] }],
      'svc-a',
    );

    expect(getDisplayRoles(session)).toEqual(['service_owner']);
    expect(canCreateServices(session)).toBe(false);
  });

  it('allows only system admins to manage service memberships in C-2 baseline', () => {
    const systemAdminSession = normalizeAuthSession(currentUser, services, 'svc-a');
    const serviceOwnerSession = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_owner'] }],
      'svc-a',
    );
    const serviceDeveloperSession = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_developer'] }],
      'svc-a',
    );
    const serviceOperatorSession = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['service_operator'] }],
      'svc-a',
    );
    const auditorSession = normalizeAuthSession(
      { ...currentUser, global_roles: [], service_roles: [] },
      [{ ...services[0], roles: ['auditor'] }],
      'svc-a',
    );

    expect(canManageServiceMembers(systemAdminSession)).toBe(true);
    expect(canManageServiceMembers(serviceOwnerSession)).toBe(false);
    expect(canManageServiceMembers(serviceDeveloperSession)).toBe(false);
    expect(canManageServiceMembers(serviceOperatorSession)).toBe(false);
    expect(canManageServiceMembers(auditorSession)).toBe(false);
  });

  it('selects created services only when they come from server-derived scope', () => {
    const session = normalizeAuthSession(currentUser, services, 'svc-a');

    expect(canSelectServiceFromScope(session, 'svc-b')).toBe(true);
    expect(canSelectServiceFromScope(session, 'missing')).toBe(false);
    expect(canSelectServiceFromScope(session, '   ')).toBe(false);
  });

  it('does not read legacy Admin header values for role helpers', () => {
    const session = {
      ...EMPTY_ADMIN_SESSION,
      authenticated: true,
      serviceId: 'svc-a',
      headers: {
        'X-Admin-Token': 'legacy-token',
        'X-Actor-Id': 'legacy-admin',
        'X-Actor-Roles': 'system_admin,service_developer',
        'X-Service-Scope': 'svc-a',
      },
    } as AdminSession & { headers: Record<string, string> };

    expect(getDisplayRoles(session)).toEqual([]);
    expect(hasAnyDisplayRole(session, ['system_admin', 'service_developer'])).toBe(false);
    expect(canEditCatalog(session)).toBe(false);
    expect(canManageReleases(session)).toBe(false);
    expect(canManageApiKeys(session)).toBe(false);
    expect(canManageRuntimeSetup(session)).toBe(false);
    expect(canManageServiceMembers(session)).toBe(false);
  });
});
