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

type ValidationDetail = {
  loc?: unknown[];
  msg?: unknown;
};

export function adminAccessRequestErrorMessage(error: any): string {
  const payload = error?.response?.data ?? error?.data;
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const first = detail.find(
      (item: ValidationDetail) => typeof item?.msg === 'string',
    ) as ValidationDetail | undefined;
    if (first && typeof first.msg === 'string') {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : undefined;
      return typeof field === 'string' ? `${field}: ${first.msg}` : first.msg;
    }
  }
  if (detail?.error?.message) return detail.error.message;
  if (payload?.error?.message) return payload.error.message;
  return error?.message ?? '신청을 제출하지 못했습니다.';
}
