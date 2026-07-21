import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  buildSystemAdminTransferRequest,
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
  riskSeverityStatus,
  summarizeRiskEvidence,
  toPermissionAdminGlobalRolesPatchRequest,
  toPermissionAdminStatusPatchRequest,
  toPermissionAdminUsersQueryParams,
  toPermissionAuditLogsQueryParams,
  toPermissionServiceRoleGrantRequest,
  toPermissionServiceRolesQueryParams,
} from './permissionManagement';

const pageSource = () =>
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'),
    'utf8',
  );

const globalStyleSource = () =>
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '../../global.less'),
    'utf8',
  );

const proTableSourceContaining = (source: string, marker: string) => {
  const markerIndex = source.indexOf(marker);
  expect(markerIndex).toBeGreaterThan(-1);
  const tableStart = source.lastIndexOf('<ProTable', markerIndex);
  const tableEnd = source.indexOf('/>', markerIndex);
  expect(tableStart).toBeGreaterThan(-1);
  expect(tableEnd).toBeGreaterThan(tableStart);
  return source.slice(tableStart, tableEnd);
};

const validAdminCurrentUser = {
  user: {
    user_id: 'admin-1',
    email: 'admin1@example.com',
    display_name: 'Admin One',
    status: 'active',
    created_at: '2026-07-14T12:43:24Z',
    updated_at: '2026-07-14T12:43:24Z',
    last_login_at: '2026-07-14T12:43:24Z',
  },
  global_roles: ['application_admin'],
  service_roles: [],
} satisfies API.AdminCurrentUserResponse;

const invalidAdminCurrentUser = {
  ...validAdminCurrentUser,
  // @ts-expect-error AdminCurrentUserResponse.global_roles must reject arbitrary strings.
  global_roles: ['not_a_real_role'],
} satisfies API.AdminCurrentUserResponse;

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
    expect(canAccessPermissionManagement(['application_admin'])).toBe(false);
    expect(canAccessPermissionManagement(['service_owner'])).toBe(false);
  });

  it('maps risk severity and role labels for table rendering', () => {
    expect(riskSeverityStatus('high')).toBe('high');
    expect(permissionRoleLabel('application_admin')).toBe('application_admin');
    expect(permissionRoleLabel('system_admin')).toBe('system_admin');
  });

  it('keeps stable tab keys and table row keys', () => {
    expect(permissionTabs.map((tab) => tab.key)).toEqual([
      'admin-users',
      'access-requests',
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
    expect(
      toPermissionAdminGlobalRolesPatchRequest(
        { ...systemAdminRow, global_roles: ['application_admin', 'system_admin'] },
        false,
      ),
    ).toEqual({
      global_roles: ['system_admin'],
    });
    expect(
      toPermissionAdminGlobalRolesPatchRequest(
        { global_roles: [] },
        true,
      ),
    ).toEqual({ global_roles: ['application_admin'] });
  });

  it('builds a guarded system_admin transfer payload from operator-entered reason', () => {
    expect(
      buildSystemAdminTransferRequest(' admin-1 ', ' admin-2 ', ' Transfer platform ownership '),
    ).toEqual({
      from_admin_user_id: 'admin-1',
      to_admin_user_id: 'admin-2',
      reason: 'Transfer platform ownership',
    });
    expect(() =>
      buildSystemAdminTransferRequest('admin-1', 'admin-2', 'too short'),
    ).toThrow('reason must be at least 10 characters');
    expect(() =>
      buildSystemAdminTransferRequest('admin-1', 'admin-2', '          '),
    ).toThrow('reason must be at least 10 characters');
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

  it('requires confirmation before granting a service role', () => {
    const grantCardSource = pageSource().match(
      /<Card title="Service role grant">[\s\S]*?<\/Card>/,
    )?.[0];

    expect(grantCardSource).toContain('<ConfirmActionButton');
    expect(grantCardSource).toContain('onConfirm={handleGrantServiceRole}');
    expect(grantCardSource).not.toContain('onClick={handleGrantServiceRole}');
  });

  it('renders access request review and application_admin-based role actions', () => {
    const source = pageSource();

    expect(permissionTabs.map((tab) => tab.label)).toContain('접근 신청');
    expect(source).toContain('listAdminAccessRequests');
    expect(source).toContain('approveAdminAccessRequest');
    expect(source).toContain('rejectAdminAccessRequest');
    expect(source).toContain('requested_at');
    expect(source).toContain('user_number');
    expect(source).toContain('access_reason');
    expect(source).toContain('decision_reason');
    expect(source).toContain('application_admin 부여');
    expect(source).toContain('application_admin 해제');
    expect(source).toContain('system_admin 이관');
    expect(source).not.toContain('system_admin 부여');
    expect(source).not.toContain('active login-eligible system_admin이 1명뿐입니다.');
    expect(source).not.toContain('로그인 가능한 system_admin 계정을 2개 이상');
  });

  it('requires confirm flows for approval and decision-reason rejection', () => {
    const source = pageSource();

    expect(source).toContain('okText="승인"');
    expect(source).toContain('applicant.name');
    expect(source).toContain('applicant.email');
    expect(source).toContain('applicant.access_reason');
    expect(source).toContain('Modal.confirm({');
    expect(source).toContain("name=\"decision_reason\"");
    expect(source).toContain('rejectAdminAccessRequest');
  });

  it('requires operator-entered transfer reason instead of a canned string', () => {
    const source = pageSource();

    expect(source).toContain('openSystemAdminTransferModal');
    expect(source).toContain("name=\"reason\"");
    expect(source).toContain('buildSystemAdminTransferRequest');
    expect(source).toContain('values.reason');
    expect(source).not.toContain(
      '`Transfer system_admin ownership to ${row.user_id} from Permission Management.`',
    );
  });

  it('keeps admin user row actions compact and moves overflow actions into a dropdown', () => {
    const source = pageSource();
    const adminUserColumnsSource = source.match(
      /const adminUserColumns[\s\S]*?const globalRoleColumns/,
    )?.[0];

    expect(source).toContain('Dropdown');
    expect(source).toContain('MoreOutlined');
    expect(source).toContain('adminUserMoreMenuItems');
    expect(source).toContain('scroll={{');
    expect(adminUserColumnsSource).toContain('width: 180');
    expect(adminUserColumnsSource).not.toContain('width: 240');
  });

  it('keeps service role grant controls bounded while compacting admin actions', () => {
    const source = pageSource();
    const grantCardSource = source.match(
      /<Card title="Service role grant">[\s\S]*?<\/Card>/,
    )?.[0];

    expect(grantCardSource).toContain('className="permission-service-role-grant"');
    expect(grantCardSource).toContain("style={{ width: '100%', maxWidth: 240 }}");
    expect(grantCardSource).toContain("style={{ width: '100%', maxWidth: 340 }}");
  });

  it('adds a scrollable tabs class for mobile Permission Management tabs', () => {
    const source = pageSource();

    expect(source).toContain('className="permission-management-tabs"');
  });

  it('bounds every Permission Management tab table with internal scroll', () => {
    const source = pageSource();
    const tableMarkers = [
      'actionRef={adminActionRef}',
      'rowKey="request_id"',
      'actionRef={globalRoleActionRef}',
      'actionRef={serviceRoleActionRef}',
      'actionRef={auditActionRef}',
      'actionRef={riskActionRef}',
    ];

    tableMarkers.forEach((marker) => {
      const tableSource = proTableSourceContaining(source, marker);

      expect(tableSource).toContain('className="admin-scroll-table"');
      expect(tableSource).toContain('scroll={{');
    });
  });

  it('clips the Permission Management tab rail inside the viewport on mobile', () => {
    const source = globalStyleSource();

    expect(source).toContain('.permission-management-tabs .ant-tabs-nav-wrap');
    expect(source).toContain('overflow-x: auto');
    expect(source).toContain('min-width: 0');
  });
});
