export type ServiceMemberTableRow = {
  rowKey: string;
  service_id: string;
  user_id: string;
  email: string;
  display_name: string;
  status: string;
  role: API.ServiceRole;
  assigned_by: string;
  assigned_at: string;
};

const serviceRoles = [
  'service_owner',
  'service_developer',
  'service_operator',
  'auditor',
] as const satisfies API.ServiceRole[];

export const serviceRoleOptions = serviceRoles.map((role) => ({
  label: role,
  value: role,
})) satisfies Array<{ label: API.ServiceRole; value: API.ServiceRole }>;

const isServiceRole = (role: string): role is API.ServiceRole =>
  serviceRoles.includes(role as API.ServiceRole);

export const toServiceRoleGrantRequest = (userId: string, role: string) => {
  const trimmedUserId = userId.trim();
  const trimmedRole = role.trim();

  if (!trimmedUserId) {
    throw new Error('user_id is required');
  }
  if (!isServiceRole(trimmedRole)) {
    throw new Error('role is invalid');
  }

  return {
    userId: trimmedUserId,
    payload: { role: trimmedRole },
  };
};

export const memberRowsForTable = (
  members: API.ServiceMember[],
): ServiceMemberTableRow[] =>
  members.flatMap((member) =>
    member.roles.map((roleGrant) => ({
      rowKey: `${member.user.user_id}:${roleGrant.role}`,
      service_id: member.service_id,
      user_id: member.user.user_id,
      email: member.user.email,
      display_name: member.user.display_name,
      status: member.user.status,
      role: roleGrant.role,
      assigned_by: roleGrant.assigned_by,
      assigned_at: roleGrant.assigned_at,
    })),
  );

export const shouldClearMembershipState = (
  previousServiceId: string,
  nextServiceId: string,
) => previousServiceId.trim() !== nextServiceId.trim();

export type CurrentServiceRequestCheck = {
  requestSeq: number;
  latestRequestSeq: number;
  expectedServiceId: string;
  currentServiceId: string;
  expectedQuery?: string;
  currentQuery?: string;
};

export const isCurrentServiceRequest = ({
  requestSeq,
  latestRequestSeq,
  expectedServiceId,
  currentServiceId,
  expectedQuery,
  currentQuery,
}: CurrentServiceRequestCheck) => {
  const normalizedExpectedServiceId = expectedServiceId.trim();
  const normalizedCurrentServiceId = currentServiceId.trim();
  const matchesQuery =
    expectedQuery === undefined ||
    currentQuery === undefined ||
    expectedQuery === currentQuery;

  return (
    requestSeq === latestRequestSeq &&
    normalizedExpectedServiceId.length > 0 &&
    normalizedExpectedServiceId === normalizedCurrentServiceId &&
    matchesQuery
  );
};

export const isCurrentServiceRow = (rowServiceId: string, currentServiceId: string) =>
  rowServiceId.trim().length > 0 && rowServiceId.trim() === currentServiceId.trim();
