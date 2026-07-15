export type DepartmentFormValues = {
  dept_number: string;
  name: string;
};

export type OrganizationUserFormValues = {
  user_number: string;
  name: string;
  department_id: string;
};

export type DepartmentTableFilters = {
  keyword?: string;
  use_yn?: API.UseYn;
};

export type OrganizationUserTableFilters = {
  keyword?: string;
  department_id?: string;
  use_yn?: API.UseYn;
};

export type AdminAccessCreateFormValues = {
  email: string;
  display_name: string;
};

export type DepartmentOption = {
  label: string;
  value: string;
};

export const DIRECTORY_DEPARTMENT_OPTION_LIMIT = 100;
export const EMPTY_DEPARTMENT_TABLE_FILTERS: DepartmentTableFilters = {};
export const EMPTY_ORGANIZATION_USER_TABLE_FILTERS: OrganizationUserTableFilters = {};

export const canAccessOrganizationDirectory = (globalRoles: string[]) =>
  globalRoles.includes('system_admin');

export const toDepartmentOptionSearchParams = (query?: string) => {
  const trimmedQuery = query?.trim();

  return {
    ...(trimmedQuery ? { query: trimmedQuery } : {}),
    use_yn: 'Y' as const,
    limit: DIRECTORY_DEPARTMENT_OPTION_LIMIT,
  };
};

export const toDepartmentOption = (department: API.Department): DepartmentOption => ({
  label: department.name,
  value: department.id,
});

const stripLocalUniquenessSuffix = (value: string) =>
  value.trim().replace(/-[0-9a-f]{8}$/i, '');

export const formatDepartmentNumber = (deptNumber: string) =>
  stripLocalUniquenessSuffix(deptNumber);

export const formatOrganizationUserNumber = (userNumber: string) =>
  stripLocalUniquenessSuffix(userNumber);

export const toDepartmentCreateRequest = (
  values: DepartmentFormValues,
): API.DepartmentCreateRequest => ({
  dept_number: values.dept_number.trim(),
  name: values.name.trim(),
});

export const toDepartmentUseYnPatchRequest = (
  useYn: API.UseYn,
): API.DepartmentPatchRequest => ({
  use_yn: useYn,
});

export const toOrganizationUserCreateRequest = (
  values: OrganizationUserFormValues,
): API.OrganizationUserCreateRequest => ({
  user_number: values.user_number.trim(),
  name: values.name.trim(),
  department_id: values.department_id,
});

export const toOrganizationUserUseYnPatchRequest = (
  useYn: API.UseYn,
): API.OrganizationUserPatchRequest => ({
  use_yn: useYn,
});

const optionalTrimmedString = (value: string | undefined) => {
  const trimmed = value?.trim();
  return trimmed || undefined;
};

export const toDepartmentListParamsFromFilters = (
  filters: DepartmentTableFilters,
) => ({
  ...(optionalTrimmedString(filters.keyword)
    ? { query: optionalTrimmedString(filters.keyword) }
    : {}),
  ...(filters.use_yn ? { use_yn: filters.use_yn } : {}),
  limit: 100,
});

export const toOrganizationUserListParamsFromFilters = (
  filters: OrganizationUserTableFilters,
) => ({
  ...(optionalTrimmedString(filters.keyword)
    ? { query: optionalTrimmedString(filters.keyword) }
    : {}),
  ...(optionalTrimmedString(filters.department_id)
    ? { department_id: optionalTrimmedString(filters.department_id) }
    : {}),
  ...(filters.use_yn ? { use_yn: filters.use_yn } : {}),
  limit: 100,
});

export const toAdminUserCreateRequest = (
  values: AdminAccessCreateFormValues,
  organizationUser: API.OrganizationUser,
): API.ManagedAdminUserCreateRequest => ({
  organization_user_id: organizationUser.id,
  email: values.email.trim(),
  display_name: values.display_name.trim(),
  status: 'disabled',
  global_roles: ['application_admin'],
});

export const permissionManagementAdminUserUrl = (adminUserId: string) =>
  `/permission-management?admin_user_id=${encodeURIComponent(adminUserId.trim())}`;

export const toAdminUserStatusPatchRequest = (
  status: API.ManagedAdminUserStatus,
): API.ManagedAdminUserPatchRequest => ({
  status,
});

export const hasSystemAdminRole = (adminUser: API.ManagedAdminUser) =>
  adminUser.global_roles.includes('system_admin');

export const hasIncompleteApplicationAdminAccess = (
  adminUser: Pick<API.ManagedAdminUser, 'global_roles'>,
) => !adminUser.global_roles.includes('application_admin');
