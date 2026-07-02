import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_ADMIN_SESSION,
  isAdminSessionReady,
  normalizeEnvironment,
  readAdminSession,
  writeAdminSession,
} from './adminSession';

class MemoryStorage {
  private values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

describe('admin session storage', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', new MemoryStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uses v04-compatible local defaults for Admin API headers', () => {
    expect(readAdminSession()).toEqual({
      ...DEFAULT_ADMIN_SESSION,
      serviceId: 'it-helpdesk-pilot-sprint10-operation-monitoring',
      serviceScope: 'it-helpdesk-pilot-sprint10-operation-monitoring',
      environment: 'local',
    });
  });

  it('persists actor, roles, token, environment, and service scope', () => {
    writeAdminSession({
      adminToken: 'local-admin-token',
      actorId: 'auditor-user',
      actorRoles: ['auditor'],
      serviceId: 'svc-ops',
      serviceScope: 'svc-ops',
      environment: 'prod',
    });

    expect(readAdminSession()).toEqual({
      adminToken: 'local-admin-token',
      actorId: 'auditor-user',
      actorRoles: ['auditor'],
      serviceId: 'svc-ops',
      serviceScope: 'svc-ops',
      environment: 'prod',
    });
  });

  it('normalizes a blank environment to the local default', () => {
    expect(normalizeEnvironment('')).toBe('local');
    expect(normalizeEnvironment('   ')).toBe('local');
    expect(normalizeEnvironment(' prod ')).toBe('prod');
  });

  it('requires an admin token and service scope before read APIs run', () => {
    expect(isAdminSessionReady(readAdminSession())).toBe(false);

    expect(
      isAdminSessionReady({
        ...readAdminSession(),
        adminToken: 'local-admin-token',
        serviceScope: '',
      }),
    ).toBe(false);

    writeAdminSession({
      adminToken: 'local-admin-token',
      actorId: 'auditor-user',
      actorRoles: ['auditor'],
      serviceId: 'svc-ops',
      serviceScope: 'svc-ops',
      environment: 'prod',
    });

    expect(isAdminSessionReady(readAdminSession())).toBe(true);
  });
});
