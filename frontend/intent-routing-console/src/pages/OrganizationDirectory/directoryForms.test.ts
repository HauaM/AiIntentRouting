import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  EMPTY_DEPARTMENT_TABLE_FILTERS,
  EMPTY_ORGANIZATION_USER_TABLE_FILTERS,
  canAccessOrganizationDirectory,
  formatDepartmentNumber,
  formatOrganizationUserNumber,
  hasIncompleteApplicationAdminAccess,
  hasSystemAdminRole,
  permissionManagementAdminUserUrl,
  toDepartmentOption,
  toDepartmentOptionSearchParams,
  toAdminUserCreateRequest,
  toAdminUserStatusPatchRequest,
  toDepartmentCreateRequest,
  toDepartmentUseYnPatchRequest,
  toOrganizationUserCreateRequest,
  toOrganizationUserUseYnPatchRequest,
  toDepartmentListParamsFromFilters,
  toOrganizationUserListParamsFromFilters,
} from './directoryForms';

const pageSource = () =>
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'),
    'utf8',
  );

describe('directoryForms', () => {
  it('trims department form values', () => {
    expect(
      toDepartmentCreateRequest({ dept_number: ' 0969 ', name: ' IT지원부 ' }),
    ).toEqual({
      dept_number: '0969',
      name: 'IT지원부',
    });
  });

  it('trims organization user form values', () => {
    expect(
      toOrganizationUserCreateRequest({
        user_number: ' 21P0031 ',
        name: ' 홍길동 ',
        department_id: 'dept-1',
      }),
    ).toEqual({
      user_number: '21P0031',
      name: '홍길동',
      department_id: 'dept-1',
    });
  });

  it('allows organization directory access only for system admins', () => {
    expect(canAccessOrganizationDirectory([])).toBe(false);
    expect(canAccessOrganizationDirectory(['service_owner'])).toBe(false);
    expect(canAccessOrganizationDirectory(['service_owner', 'system_admin'])).toBe(true);
  });

  it('builds searchable department option params from the latest query', () => {
    expect(toDepartmentOptionSearchParams()).toEqual({ use_yn: 'Y', limit: 100 });
    expect(toDepartmentOptionSearchParams('   ')).toEqual({ use_yn: 'Y', limit: 100 });
    expect(toDepartmentOptionSearchParams(' 0969 IT지원부 ')).toEqual({
      query: '0969 IT지원부',
      use_yn: 'Y',
      limit: 100,
    });
  });

  it('uses only the department name for department option labels', () => {
    expect(
      toDepartmentOption({
        id: 'dept-1',
        dept_number: '0969',
        name: 'IT지원부',
        use_yn: 'Y',
        created_by: 'system_admin',
        updated_by: 'system_admin',
        created_at: '2026-07-14T12:43:24Z',
        updated_at: '2026-07-14T12:43:24Z',
      }),
    ).toEqual({
      label: 'IT지원부',
      value: 'dept-1',
    });
  });

  it('formats department numbers without local uniqueness suffixes for table display', () => {
    expect(formatDepartmentNumber('0969-06c88b23')).toBe('0969');
    expect(formatDepartmentNumber('0969')).toBe('0969');
    expect(formatDepartmentNumber('')).toBe('');
  });

  it('formats organization user numbers without local uniqueness suffixes for table display', () => {
    expect(formatOrganizationUserNumber('21P0031-089ba09e')).toBe('21P0031');
    expect(formatOrganizationUserNumber('21P0031')).toBe('21P0031');
    expect(formatOrganizationUserNumber('')).toBe('');
  });

  it('builds a department use flag patch request', () => {
    expect(toDepartmentUseYnPatchRequest('N')).toEqual({ use_yn: 'N' });
    expect(toDepartmentUseYnPatchRequest('Y')).toEqual({ use_yn: 'Y' });
  });

  it('builds an organization user use flag patch request', () => {
    expect(toOrganizationUserUseYnPatchRequest('N')).toEqual({ use_yn: 'N' });
    expect(toOrganizationUserUseYnPatchRequest('Y')).toEqual({ use_yn: 'Y' });
  });

  it('builds disabled admin account creation requests for organization users', () => {
    expect(
      toAdminUserCreateRequest(
        { email: ' Admin.User@Example.COM ', display_name: ' 홍길동 Admin ' },
        {
          id: 'org-user-1',
          user_number: '21P0031',
          name: '홍길동',
          department_id: 'dept-1',
          department: {
            id: 'dept-1',
            dept_number: '0969',
            name: 'IT지원부',
            use_yn: 'Y',
            created_by: 'system_admin',
            updated_by: 'system_admin',
            created_at: '2026-07-14T12:43:24Z',
            updated_at: '2026-07-14T12:43:24Z',
          },
          use_yn: 'Y',
          created_by: 'system_admin',
          updated_by: 'system_admin',
          created_at: '2026-07-14T12:43:24Z',
          updated_at: '2026-07-14T12:43:24Z',
        },
      ),
    ).toEqual({
      organization_user_id: 'org-user-1',
      email: 'Admin.User@Example.COM',
      display_name: '홍길동 Admin',
      status: 'disabled',
      global_roles: ['application_admin'],
    });
  });

  it('detects incomplete Admin Console access without application_admin', () => {
    const adminUser: API.ManagedAdminUser = {
      user_id: 'admin-1',
      email: 'admin@example.com',
      display_name: 'Admin One',
      status: 'active',
      organization_user_id: 'org-user-1',
      global_roles: [],
      is_last_active_system_admin: false,
      created_at: '2026-07-14T12:43:24Z',
      updated_at: '2026-07-14T12:43:24Z',
      last_login_at: null,
    };

    expect(hasIncompleteApplicationAdminAccess(adminUser)).toBe(true);
    expect(
      hasIncompleteApplicationAdminAccess({
        ...adminUser,
        global_roles: ['application_admin'],
      }),
    ).toBe(false);
  });

  it('builds admin status patch requests without direct system_admin role patching helpers', () => {
    const adminUser: API.ManagedAdminUser = {
      user_id: 'admin-1',
      email: 'admin@example.com',
      display_name: 'Admin One',
      status: 'active',
      organization_user_id: 'org-user-1',
      global_roles: ['application_admin'],
      is_last_active_system_admin: false,
      created_at: '2026-07-14T12:43:24Z',
      updated_at: '2026-07-14T12:43:24Z',
      last_login_at: null,
    };

    expect(toAdminUserStatusPatchRequest('disabled')).toEqual({ status: 'disabled' });
    expect(hasSystemAdminRole(adminUser)).toBe(false);
  });

  it('builds the Permission Management shortcut URL for linked admin accounts', () => {
    expect(permissionManagementAdminUserUrl(' admin/user 1 ')).toBe(
      '/permission-management?admin_user_id=admin%2Fuser%201',
    );
  });

  it('shows incomplete access and removes direct system_admin grant copy from the modal', () => {
    const source = pageSource();

    expect(source).toContain('incomplete access');
    expect(source).toContain('application_admin');
    expect(source).not.toContain('system_admin 부여');
    expect(source).not.toContain('system_admin 해제');
  });

  it('uses stable modal scroll settings and current Ant Design hidden props', () => {
    const source = pageSource();

    expect(source).toContain('destroyOnHidden');
    expect(source).not.toContain('destroyOnClose');
    expect(source).not.toContain('destroyInactiveTabPane');
    expect(source).toContain("body: { maxHeight: 'calc(100vh - 220px)', overflow: 'auto' }");
    expect(source).toContain("footer: { marginTop: 0 }");
  });

  it('normalizes department toolbar filters into list params', () => {
    expect(toDepartmentListParamsFromFilters(EMPTY_DEPARTMENT_TABLE_FILTERS)).toEqual({
      limit: 100,
    });
    expect(
      toDepartmentListParamsFromFilters({
        keyword: ' 0969 IT지원부 ',
        use_yn: 'Y',
      }),
    ).toEqual({
      query: '0969 IT지원부',
      use_yn: 'Y',
      limit: 100,
    });
  });

  it('normalizes organization user toolbar filters into list params', () => {
    expect(
      toOrganizationUserListParamsFromFilters(EMPTY_ORGANIZATION_USER_TABLE_FILTERS),
    ).toEqual({ limit: 100 });
    expect(
      toOrganizationUserListParamsFromFilters({
        keyword: ' 홍길동 ',
        department_id: ' dept-1 ',
        use_yn: 'N',
      }),
    ).toEqual({
      query: '홍길동',
      department_id: 'dept-1',
      use_yn: 'N',
      limit: 100,
    });
  });
});
