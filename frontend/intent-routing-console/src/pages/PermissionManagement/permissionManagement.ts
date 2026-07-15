export type PermissionManagementTabKey =
  | 'admin-users'
  | 'access-requests'
  | 'global-roles'
  | 'service-roles'
  | 'audit-logs'
  | 'risk-findings';

export const permissionTabs: Array<{
  key: PermissionManagementTabKey;
  label: string;
}> = [
  { key: 'admin-users', label: 'Admin 계정' },
  { key: 'access-requests', label: '접근 신청' },
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

const permissionServiceRoles = [
  'service_owner',
  'service_developer',
  'service_operator',
  'auditor',
] as const satisfies API.ServiceRole[];

const permissionRoleLabels: Record<string, string> = {
  system_admin: 'system_admin',
  application_admin: 'application_admin',
  service_owner: 'service_owner',
  service_developer: 'service_developer',
  service_operator: 'service_operator',
  auditor: 'auditor',
};

export const PERMISSION_TABLE_LIMIT = 100;

export const permissionServiceRoleOptions = permissionServiceRoles.map((role) => ({
  label: role,
  value: role,
})) satisfies Array<{ label: API.ServiceRole; value: API.ServiceRole }>;

const trimString = (value: unknown) => (typeof value === 'string' ? value.trim() : '');

const optionalTrimmedString = (value: unknown) => {
  const trimmed = trimString(value);
  return trimmed || undefined;
};

const isServiceRole = (role: string): role is API.ServiceRole =>
  permissionServiceRoles.includes(role as API.ServiceRole);

const isManagedAdminUserStatus = (
  status: unknown,
): status is API.ManagedAdminUserStatus => status === 'active' || status === 'disabled';

const isGlobalAdminRole = (role: unknown): role is API.GlobalAdminRole =>
  role === 'system_admin' || role === 'application_admin';

const isPermissionOrganizationLink = (
  value: unknown,
): value is API.PermissionOrganizationLink => value === 'linked' || value === 'unlinked';

const isUseYn = (value: unknown): value is API.UseYn => value === 'Y' || value === 'N';

const isPermissionAuditEventGroup = (
  value: unknown,
): value is API.PermissionAuditEventGroup =>
  value === 'admin_user' || value === 'service_membership' || value === 'all';

export function canAccessPermissionManagement(roles: readonly string[] = []) {
  return roles.includes('system_admin');
}

export function hasSystemAdminGlobalRole(row: { global_roles: readonly string[] }) {
  return row.global_roles.includes('system_admin');
}

export function isActiveLoginEligibleSystemAdmin(row: API.PermissionAdminUserSummary) {
  return Boolean(
    row.status === 'active' &&
      hasSystemAdminGlobalRole(row) &&
      (!row.organization_user || row.organization_user.use_yn === 'Y'),
  );
}

export function filterSystemAdminRows(rows: API.PermissionAdminUserSummary[]) {
  return rows.filter(hasSystemAdminGlobalRole);
}

export function countActiveLoginEligibleSystemAdmins(
  rows: API.PermissionAdminUserSummary[],
) {
  return rows.filter(isActiveLoginEligibleSystemAdmin).length;
}

export function isLastActiveSystemAdminProtected(row: API.PermissionAdminUserSummary) {
  return Boolean(row.is_last_active_system_admin && isActiveLoginEligibleSystemAdmin(row));
}

export function riskSeverityColor(severity: API.PermissionRiskSeverity | string) {
  return riskSeverityColors[severity as API.PermissionRiskSeverity] ?? 'default';
}

export function permissionRoleLabel(role: string) {
  return permissionRoleLabels[role] ?? role;
}

export function toPermissionAdminStatusPatchRequest(
  status: API.ManagedAdminUserStatus,
): API.ManagedAdminUserPatchRequest {
  return { status };
}

export function toPermissionAdminGlobalRolesPatchRequest(
  row: Pick<API.PermissionAdminUserSummary, 'global_roles'>,
  grant: boolean,
): API.ManagedAdminUserPatchRequest {
  const roleSet = new Set<API.GlobalAdminRole>(row.global_roles);
  if (grant) roleSet.add('application_admin');
  else roleSet.delete('application_admin');
  return { global_roles: Array.from(roleSet).sort() };
}

export function buildSystemAdminTransferRequest(
  fromAdminUserId: string,
  toAdminUserId: string,
  reason: string,
): API.SystemAdminTransferRequest {
  const from_admin_user_id = trimString(fromAdminUserId);
  const to_admin_user_id = trimString(toAdminUserId);
  const trimmedReason = trimString(reason);

  if (!from_admin_user_id) throw new Error('from_admin_user_id is required');
  if (!to_admin_user_id) throw new Error('to_admin_user_id is required');
  if (trimmedReason.length < 10) throw new Error('reason must be at least 10 characters');

  return {
    from_admin_user_id,
    to_admin_user_id,
    reason: trimmedReason,
  };
}

export function toPermissionServiceRoleGrantRequest(
  serviceId: string,
  userId: string,
  role: string,
) {
  const trimmedServiceId = serviceId.trim();
  const trimmedUserId = userId.trim();
  const trimmedRole = role.trim();

  if (!trimmedServiceId) throw new Error('service_id is required');
  if (!trimmedUserId) throw new Error('user_id is required');
  if (!isServiceRole(trimmedRole)) throw new Error('role is invalid');

  return {
    serviceId: trimmedServiceId,
    userId: trimmedUserId,
    payload: { role: trimmedRole },
  };
}

export function toPermissionAdminUsersQueryParams(
  params: Record<string, unknown>,
  focusedAdminUserId?: string,
): API.PermissionAdminUsersQueryParams {
  const keyword = optionalTrimmedString(params.keyword) ?? optionalTrimmedString(focusedAdminUserId);
  return {
    ...(keyword ? { query: keyword } : {}),
    ...(isManagedAdminUserStatus(params.status) ? { status: params.status } : {}),
    ...(isGlobalAdminRole(params.global_role) ? { global_role: params.global_role } : {}),
    ...(isPermissionOrganizationLink(params.organization_link)
      ? { organization_link: params.organization_link }
      : {}),
    ...(isUseYn(params.organization_use_yn)
      ? { organization_use_yn: params.organization_use_yn }
      : {}),
    limit: PERMISSION_TABLE_LIMIT,
  };
}

export function toPermissionServiceRolesQueryParams(
  params: Record<string, unknown>,
): API.PermissionServiceRolesQueryParams {
  const serviceId = optionalTrimmedString(params.service_id);
  const userId = optionalTrimmedString(params.user_id);
  const query = optionalTrimmedString(params.keyword);
  return {
    ...(serviceId ? { service_id: serviceId } : {}),
    ...(userId ? { user_id: userId } : {}),
    ...(isServiceRole(trimString(params.role)) ? { role: trimString(params.role) as API.ServiceRole } : {}),
    ...(query ? { query } : {}),
    limit: PERMISSION_TABLE_LIMIT,
  };
}

export function toPermissionAuditLogsQueryParams(
  params: Record<string, unknown>,
): API.PermissionAuditLogsQueryParams {
  const eventType = optionalTrimmedString(params.event_type);
  const actorId = optionalTrimmedString(params.actor_id);
  const targetId = optionalTrimmedString(params.target_id);
  const serviceId = optionalTrimmedString(params.service_id);

  return {
    ...(isPermissionAuditEventGroup(params.event_group)
      ? { event_group: params.event_group }
      : {}),
    ...(eventType ? { event_type: eventType } : {}),
    ...(actorId ? { actor_id: actorId } : {}),
    ...(targetId ? { target_id: targetId } : {}),
    ...(serviceId ? { service_id: serviceId } : {}),
    limit: PERMISSION_TABLE_LIMIT,
  };
}

export function summarizeRiskEvidence(evidence: Record<string, unknown>) {
  return Object.entries(evidence).map(([key, value]) => {
    if (Array.isArray(value)) return `${key}: ${value.length} items`;
    if (value === null) return `${key}: null`;
    if (typeof value === 'object') return `${key}: object`;
    return `${key}: ${String(value)}`;
  });
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
