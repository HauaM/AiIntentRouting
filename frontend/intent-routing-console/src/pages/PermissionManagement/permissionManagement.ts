export type PermissionManagementTabKey =
  | 'admin-users'
  | 'global-roles'
  | 'service-roles'
  | 'audit-logs'
  | 'risk-findings';

export const permissionTabs: Array<{
  key: PermissionManagementTabKey;
  label: string;
}> = [
  { key: 'admin-users', label: 'Admin 계정' },
  { key: 'global-roles', label: '전역 권한' },
  { key: 'service-roles', label: '서비스 권한' },
  { key: 'audit-logs', label: '권한 변경 이력' },
  { key: 'risk-findings', label: '운영 점검' },
];

const riskSeverityColors: Record<API.PermissionRiskSeverity, string> = {
  low: 'blue',
  medium: 'orange',
  high: 'red',
};

const permissionRoleLabels: Record<string, string> = {
  system_admin: 'system_admin',
  service_owner: 'service_owner',
  service_developer: 'service_developer',
  service_operator: 'service_operator',
  auditor: 'auditor',
};

export function canAccessPermissionManagement(roles: readonly string[] = []) {
  return roles.includes('system_admin');
}

export function riskSeverityColor(severity: API.PermissionRiskSeverity | string) {
  return riskSeverityColors[severity as API.PermissionRiskSeverity] ?? 'default';
}

export function permissionRoleLabel(role: string) {
  return permissionRoleLabels[role] ?? role;
}

export function permissionAdminUserRowKey(
  row: Pick<API.PermissionAdminUserSummary, 'user_id'>,
) {
  return row.user_id;
}

export function permissionGlobalRoleRowKey(row: { user_id: string; role: string }) {
  return `${row.user_id}:${row.role}`;
}

export function permissionServiceRoleRowKey(
  row: Pick<API.PermissionServiceRoleSummary, 'service_id' | 'role'> & {
    user: Pick<API.PermissionServiceRoleUserSummary, 'user_id'>;
  },
) {
  return `${row.service_id}:${row.user.user_id}:${row.role}`;
}

export function permissionAuditLogRowKey(row: Pick<API.AuditLog, 'audit_id'>) {
  return row.audit_id;
}

export function riskFindingRowKey(row: Pick<API.PermissionRiskFinding, 'finding_id'>) {
  return row.finding_id;
}
