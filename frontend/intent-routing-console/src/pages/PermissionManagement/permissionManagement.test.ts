import { describe, expect, it } from 'vitest';
import {
  canAccessPermissionManagement,
  countActiveLoginEligibleSystemAdmins,
  filterSystemAdminRows,
  permissionAdminUserRowKey,
  permissionAuditLogRowKey,
  permissionRoleLabel,
  permissionServiceRoleRowKey,
  permissionServiceRoleOptions,
  permissionTabs,
  riskFindingRowKey,
  riskSeverityColor,
  summarizeRiskEvidence,
  toPermissionAdminGlobalRolesPatchRequest,
  toPermissionAdminStatusPatchRequest,
  toPermissionAdminUsersQueryParams,
  toPermissionAuditLogsQueryParams,
  toPermissionServiceRoleGrantRequest,
  toPermissionServiceRolesQueryParams,
} from './permissionManagement';

describe('Permission Management helpers', () => {
  const systemAdminRow: API.PermissionAdminUserSummary = {
    user_id: 'admin-1',
    email: 'admin1@example.com',
    display_name: 'Admin One',
    status: 'active',
    global_roles: ['system_admin'],
    is_last_active_system_admin: true,
    created_at: '2026-07-14T12:43:24Z',
    updated_at: '2026-07-14T12:43:24Z',
    last_login_at: '2026-07-14T12:43:24Z',
    organization_user: {
      id: 'org-1',
      user_number: '21P0031',
      name: '홍길동',
      use_yn: 'Y',
      department: {
        id: 'dept-1',
        dept_number: '0969',
        name: 'IT지원부',
        use_yn: 'Y',
      },
    },
    service_roles: [],
    risk_flags: [],
  };

  it('guards access to system_admin only', () => {
    expect(canAccessPermissionManagement(['system_admin'])).toBe(true);
    expect(canAccessPermissionManagement(['service_owner'])).toBe(false);
  });

  it('maps risk severity and role labels for table rendering', () => {
    expect(riskSeverityColor('high')).toBe('red');
    expect(permissionRoleLabel('system_admin')).toBe('system_admin');
  });

  it('keeps stable tab keys and table row keys', () => {
    expect(permissionTabs.map((tab) => tab.key)).toEqual([
      'admin-users',
      'global-roles',
      'service-roles',
      'audit-logs',
      'risk-findings',
    ]);
    expect(permissionAdminUserRowKey({ user_id: 'admin/user' })).toBe('admin/user');
    expect(
      permissionServiceRoleRowKey({
        service_id: 'svc/admin',
        user: { user_id: 'admin/user' },
        role: 'service_owner',
      }),
    ).toBe('svc/admin:admin/user:service_owner');
    expect(permissionAuditLogRowKey({ audit_id: 'audit/1' })).toBe('audit/1');
    expect(riskFindingRowKey({ finding_id: 'risk/1' })).toBe('risk/1');
  });

  it('filters global role rows and counts active login-eligible system admins', () => {
    const rows: API.PermissionAdminUserSummary[] = [
      systemAdminRow,
      { ...systemAdminRow, user_id: 'admin-2', global_roles: [], is_last_active_system_admin: false },
      {
        ...systemAdminRow,
        user_id: 'admin-3',
        status: 'disabled',
        is_last_active_system_admin: false,
      },
      {
        ...systemAdminRow,
        user_id: 'admin-4',
        is_last_active_system_admin: false,
        organization_user: systemAdminRow.organization_user
          ? { ...systemAdminRow.organization_user, use_yn: 'N' }
          : null,
      },
    ];

    expect(filterSystemAdminRows(rows).map((row) => row.user_id)).toEqual([
      'admin-1',
      'admin-3',
      'admin-4',
    ]);
    expect(countActiveLoginEligibleSystemAdmins(rows)).toBe(1);
  });

  it('builds admin status and global role patch payloads', () => {
    expect(toPermissionAdminStatusPatchRequest('disabled')).toEqual({ status: 'disabled' });
    expect(toPermissionAdminGlobalRolesPatchRequest(systemAdminRow, false)).toEqual({
      global_roles: [],
    });
    expect(
      toPermissionAdminGlobalRolesPatchRequest(
        { global_roles: [] },
        true,
      ),
    ).toEqual({ global_roles: ['system_admin'] });
  });

  it('exposes service role options and validates grant requests', () => {
    expect(permissionServiceRoleOptions).toEqual([
      { label: 'service_owner', value: 'service_owner' },
      { label: 'service_developer', value: 'service_developer' },
      { label: 'service_operator', value: 'service_operator' },
      { label: 'auditor', value: 'auditor' },
    ]);
    expect(
      toPermissionServiceRoleGrantRequest(' svc-a ', ' admin-1 ', 'service_operator'),
    ).toEqual({
      serviceId: 'svc-a',
      userId: 'admin-1',
      payload: { role: 'service_operator' },
    });
    expect(() =>
      toPermissionServiceRoleGrantRequest('', 'admin-1', 'service_owner'),
    ).toThrow('service_id is required');
    expect(() =>
      toPermissionServiceRoleGrantRequest('svc-a', 'admin-1', 'system_admin'),
    ).toThrow('role is invalid');
  });

  it('maps table params to permission API query params without page fields', () => {
    expect(
      toPermissionAdminUsersQueryParams({
        current: 2,
        pageSize: 20,
        keyword: ' lee ',
        status: 'active',
        global_role: 'system_admin',
        organization_link: 'linked',
        organization_use_yn: 'Y',
      }),
    ).toEqual({
      query: 'lee',
      status: 'active',
      global_role: 'system_admin',
      organization_link: 'linked',
      organization_use_yn: 'Y',
      limit: 100,
    });

    expect(
      toPermissionServiceRolesQueryParams({
        service_id: ' svc-a ',
        keyword: ' owner@example.com ',
        role: 'service_owner',
      }),
    ).toEqual({
      service_id: 'svc-a',
      query: 'owner@example.com',
      role: 'service_owner',
      limit: 100,
    });

    expect(
      toPermissionAuditLogsQueryParams({
        event_group: 'service_membership',
        event_type: ' role_granted ',
        actor_id: ' admin-1 ',
        target_id: ' user-2 ',
        service_id: ' svc-a ',
      }),
    ).toEqual({
      event_group: 'service_membership',
      event_type: 'role_granted',
      actor_id: 'admin-1',
      target_id: 'user-2',
      service_id: 'svc-a',
      limit: 100,
    });
  });

  it('summarizes risk evidence without raw JSON rendering', () => {
    expect(
      summarizeRiskEvidence({
        active_system_admins: 1,
        stale_users: ['admin-3', 'admin-4'],
        details: { source: 'permission-management' },
      }),
    ).toEqual(['active_system_admins: 1', 'stale_users: 2 items', 'details: object']);
  });
});
