export type AdminAccessRequestFormValues = {
  user_number: string;
  name: string;
  department_id: string;
  email: string;
  password: string;
  password_confirm: string;
  access_reason: string;
};

export function toAdminAccessRequestCreateRequest(
  values: AdminAccessRequestFormValues,
): API.AdminAccessRequestCreateRequest {
  return {
    user_number: values.user_number.trim(),
    name: values.name.trim(),
    department_id: values.department_id.trim(),
    email: values.email.trim(),
    password: values.password,
    access_reason: values.access_reason.trim(),
  };
}
