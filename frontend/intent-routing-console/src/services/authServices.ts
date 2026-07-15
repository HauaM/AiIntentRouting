import { request } from '@umijs/max';

export async function loginAdmin(payload: API.AdminLoginRequest) {
  return request<API.AdminCurrentUserResponse>('/auth/login', {
    method: 'POST',
    data: payload,
    withCredentials: true,
  });
}

export async function submitAdminAccessRequest(
  payload: API.AdminAccessRequestCreateRequest,
) {
  return request<API.AdminAccessRequest>('/admin-access-requests', {
    method: 'POST',
    data: payload,
    withCredentials: false,
  });
}

export async function listPublicDepartments(params: { query?: string; limit?: number } = {}) {
  return request<API.PublicDepartment[]>('/public/departments', {
    method: 'GET',
    params: {
      query: params.query,
      limit: params.limit ?? 100,
    },
    withCredentials: false,
  });
}

export async function logoutAdmin() {
  return request<API.AdminLogoutResponse>('/auth/logout', {
    method: 'POST',
    withCredentials: true,
  });
}

export async function fetchCurrentAdminUser() {
  return request<API.AdminCurrentUserResponse>('/auth/me', {
    method: 'GET',
    withCredentials: true,
  });
}

export async function listAccessibleServices() {
  return request<API.AccessibleService[]>('/me/services', {
    method: 'GET',
    withCredentials: true,
  });
}
