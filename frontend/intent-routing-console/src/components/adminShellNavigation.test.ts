import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { getAdminShellRouteSpecs } from './adminShellNavigation';

const adminShellSource = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'AdminShell.tsx'), 'utf8');

const paths = (roles: readonly string[]) =>
  getAdminShellRouteSpecs(roles).map((route) => route.path);

const names = (roles: readonly string[]) =>
  getAdminShellRouteSpecs(roles).map((route) => route.name);

describe('adminShellNavigation', () => {
  it('hides system-admin-only routes for non-system-admin users', () => {
    expect(paths(['service_developer'])).not.toContain('/organization-directory');
    expect(paths(['service_developer'])).not.toContain('/permission-management');
  });

  it('shows organization directory and permission management for system admins', () => {
    expect(paths(['system_admin'])).toContain('/organization-directory');
    expect(paths(['system_admin'])).toContain('/permission-management');
  });

  it('uses directory-specific Korean copy for the organization directory route', () => {
    expect(names(['system_admin'])).toContain('조직 디렉터리');
    expect(names(['system_admin'])).toContain('권한관리');
  });

  it('does not render the Sprint phase notice globally in AdminShell', () => {
    expect(adminShellSource()).not.toContain('Sprint 11 Admin UI Phase 1');
  });
});
