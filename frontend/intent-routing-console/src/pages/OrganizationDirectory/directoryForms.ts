export type DepartmentFormValues = {
  dept_number: string;
  name: string;
};

export type OrganizationUserFormValues = {
  user_number: string;
  name: string;
  department_id: string;
};

export const DIRECTORY_DEPARTMENT_OPTION_LIMIT = 100;

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

export const toDepartmentCreateRequest = (
  values: DepartmentFormValues,
): API.DepartmentCreateRequest => ({
  dept_number: values.dept_number.trim(),
  name: values.name.trim(),
});

export const toOrganizationUserCreateRequest = (
  values: OrganizationUserFormValues,
): API.OrganizationUserCreateRequest => ({
  user_number: values.user_number.trim(),
  name: values.name.trim(),
  department_id: values.department_id,
});
