import { describe, expect, it } from 'vitest';
import {
  canAccessPermissionManagement,
  permissionAdminUserRowKey,
  permissionAuditLogRowKey,
  permissionRoleLabel,
  permissionServiceRoleRowKey,
  permissionTabs,
  riskFindingRowKey,
  riskSeverityColor,
} from './permissionManagement';

describe('Permission Management helpers', () => {
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
});
