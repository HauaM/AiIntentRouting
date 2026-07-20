import { request } from '@umijs/max';

export type TableRequestParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
  status?: string;
  route_key?: string;
  decision?: string;
  event_type?: string;
  trace_id?: string;
};

const page = <T,>(rows: T[], current = 1, pageSize = 20) => ({
  data: rows.slice((current - 1) * pageSize, current * pageSize),
  total: rows.length,
  success: true,
});

const textIncludes = (value: unknown, keyword: string) =>
  String(value ?? '').toLowerCase().includes(keyword);

export async function listIntents(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.Intent[]>(`/services/${serviceId}/intents`, {
    method: 'GET',
  });
  const keyword = params.keyword?.trim().toLowerCase();
  const filtered = rows.filter((row) => {
    const matchesStatus = !params.status || row.status === params.status;
    const matchesRoute = !params.route_key || row.route_key === params.route_key;
    const matchesKeyword =
      !keyword ||
      [row.intent_id, row.display_name, row.description, row.route_key].some((value) =>
        textIncludes(value, keyword),
      );
    return matchesStatus && matchesRoute && matchesKeyword;
  });
  return page(filtered, params.current, params.pageSize);
}

export async function listRuntimeLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.RuntimeLog[]>(`/services/${serviceId}/runtime-logs`, {
    method: 'GET',
    params: { limit: 100 },
  });
  const keyword = params.keyword?.trim().toLowerCase();
  const filtered = rows.filter((row) => {
    const matchesDecision = !params.decision || row.decision === params.decision;
    const matchesTrace = !params.trace_id || row.trace_id?.includes(params.trace_id);
    const matchesKeyword =
      !keyword ||
      [row.trace_id, row.query_masked, row.route_key, row.decision].some((value) =>
        textIncludes(value, keyword),
      );
    return matchesDecision && matchesTrace && matchesKeyword;
  });
  return page(filtered, params.current, params.pageSize);
}

export async function listAuditLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.AuditLog[]>(`/services/${serviceId}/audit-logs`, {
    method: 'GET',
    params: {
      limit: 100,
      event_type: params.event_type || undefined,
      trace_id: params.trace_id || undefined,
    },
  });
  return page(rows, params.current, params.pageSize);
}

export async function fetchRuntimeLog(serviceId: string, traceId: string) {
  return request<API.RuntimeLog>(`/services/${serviceId}/runtime-logs/${traceId}`, {
    method: 'GET',
  });
}

export async function approveExample(serviceId: string, exampleId: string) {
  return request<API.Example>(`/services/${serviceId}/examples/${exampleId}:approve`, {
    method: 'PATCH',
  });
}

export async function patchExample(
  serviceId: string,
  exampleId: string,
  payload: API.ExamplePatchRequest,
) {
  return request<API.Example>(`/services/${serviceId}/examples/${exampleId}`, {
    method: 'PATCH',
    data: payload,
  });
}

export async function deleteExample(serviceId: string, exampleId: string) {
  return request<void>(`/services/${serviceId}/examples/${exampleId}`, {
    method: 'DELETE',
  });
}

export async function deleteIntent(serviceId: string, intentId: string) {
  return request<void>(`/services/${serviceId}/intents/${intentId}`, {
    method: 'DELETE',
  });
}

export async function activateRelease(serviceId: string, releaseVersion: string) {
  return request<API.Release>(
    `/services/${serviceId}/releases/${releaseVersion}:activate`,
    { method: 'POST' },
  );
}

export async function rollbackRelease(serviceId: string, releaseVersion: string) {
  return request<API.Release>(
    `/services/${serviceId}/releases/${releaseVersion}:rollback`,
    { method: 'POST' },
  );
}

export async function revokeApiKey(keyId: string) {
  return request<API.ApiKey>(`/api-keys/${keyId}:revoke`, { method: 'POST' });
}

export async function createServiceApiKey(
  serviceId: string,
  payload: API.ServiceApiKeyCreateRequest,
) {
  return request<API.ApiKeyCreateResponse>(`/services/${serviceId}/api-keys`, {
    method: 'POST',
    data: payload,
  });
}

export async function listServiceApiKeys(serviceId: string) {
  return request<API.ApiKey[]>(`/services/${serviceId}/api-keys`, {
    method: 'GET',
  });
}

export async function revokeServiceApiKey(serviceId: string, keyId: string) {
  return request<API.ApiKey>(`/services/${serviceId}/api-keys/${keyId}:revoke`, {
    method: 'POST',
  });
}

export async function fetchRuntimeSetupGuidance(serviceId: string) {
  return request<API.RuntimeSetupGuidance>(`/services/${serviceId}/runtime-setup`, {
    method: 'GET',
  });
}
