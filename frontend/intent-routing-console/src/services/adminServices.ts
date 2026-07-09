import { request } from '@umijs/max';
import {
  filterIntents,
  filterRuntimeLogs,
  toReadOnlyTableResult,
  type TableRequestParams,
} from './tableData';

const RECENT_RUNTIME_LOG_LIMIT = 100;
const RECENT_AUDIT_LOG_LIMIT = 100;

const servicePath = (serviceId: string, suffix: string) =>
  `/services/${encodeURIComponent(serviceId)}${suffix}`;

export async function createService(payload: API.ServiceCreateRequest) {
  return request<API.Service>('/services', {
    method: 'POST',
    data: payload,
  });
}

export async function fetchRuntimeMetrics(serviceId: string, windowHours: number) {
  return request<API.RuntimeMetrics>(servicePath(serviceId, '/runtime-metrics'), {
    method: 'GET',
    params: { window_hours: windowHours },
  });
}

export async function listIntents(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.Intent[]>(servicePath(serviceId, '/intents'), {
    method: 'GET',
  });
  return toReadOnlyTableResult(filterIntents(rows, params));
}

export async function createIntent(serviceId: string, payload: API.IntentCreateRequest) {
  return request<API.Intent>(servicePath(serviceId, '/intents'), {
    method: 'POST',
    data: payload,
  });
}

export async function patchIntent(
  serviceId: string,
  intentId: string,
  payload: API.IntentPatchRequest,
) {
  return request<API.Intent>(
    servicePath(serviceId, `/intents/${encodeURIComponent(intentId)}`),
    {
      method: 'PATCH',
      data: payload,
    },
  );
}

export async function listExamples(serviceId: string, intentId: string) {
  return request<API.Example[]>(
    servicePath(serviceId, `/intents/${encodeURIComponent(intentId)}/examples`),
    { method: 'GET' },
  );
}

export async function createExample(
  serviceId: string,
  intentId: string,
  payload: API.ExampleCreateRequest,
) {
  return request<API.Example>(
    servicePath(serviceId, `/intents/${encodeURIComponent(intentId)}/examples`),
    {
      method: 'POST',
      data: payload,
    },
  );
}

export async function approveExample(serviceId: string, exampleId: string) {
  return request<API.Example>(
    servicePath(serviceId, `/examples/${encodeURIComponent(exampleId)}:approve`),
    { method: 'PATCH' },
  );
}

export async function createPolicyVersion(
  serviceId: string,
  payload: API.PolicyVersionCreateRequest,
) {
  return request<API.PolicyVersion>(servicePath(serviceId, '/policy-versions'), {
    method: 'POST',
    data: payload,
  });
}

export async function listPolicyVersions(serviceId: string, limit = 50) {
  return request<API.PolicyVersion[]>(servicePath(serviceId, '/policy-versions'), {
    method: 'GET',
    params: { limit },
  });
}

export async function createCatalogVersion(serviceId: string) {
  return request<API.CatalogVersion>(servicePath(serviceId, '/catalog-versions'), {
    method: 'POST',
  });
}

export async function listCatalogVersions(serviceId: string, limit = 50) {
  return request<API.CatalogVersionListItem[]>(
    servicePath(serviceId, '/catalog-versions'),
    {
      method: 'GET',
      params: { limit },
    },
  );
}

export async function createTestRun(serviceId: string, payload: API.TestRunCreateRequest) {
  return request<API.TestRunSummary>(servicePath(serviceId, '/test-runs'), {
    method: 'POST',
    data: payload,
  });
}

export async function listTestRuns(
  serviceId: string,
  params: { gate_passed?: boolean; risk_passed?: boolean; limit?: number } = {},
) {
  return request<API.TestRunListItem[]>(servicePath(serviceId, '/test-runs'), {
    method: 'GET',
    params: {
      gate_passed: params.gate_passed,
      risk_passed: params.risk_passed,
      limit: params.limit ?? 50,
    },
  });
}

export async function fetchTestRun(serviceId: string, testRunId: string) {
  return request<API.TestRunSummary>(
    servicePath(serviceId, `/test-runs/${encodeURIComponent(testRunId)}`),
    { method: 'GET' },
  );
}

export async function fetchTestRunResults(serviceId: string, testRunId: string) {
  return request<API.TestRunResult[]>(
    servicePath(serviceId, `/test-runs/${encodeURIComponent(testRunId)}/results`),
    { method: 'GET' },
  );
}

export async function listReleases(serviceId: string, environment?: string) {
  return request<API.Release[]>(servicePath(serviceId, '/releases'), {
    method: 'GET',
    params: { environment },
  });
}

export async function listReleaseCandidates(
  serviceId: string,
  params: { environment?: string; limit?: number } = {},
) {
  return request<API.ReleaseCandidate[]>(
    servicePath(serviceId, '/release-candidates'),
    {
      method: 'GET',
      params: {
        environment: params.environment,
        limit: params.limit ?? 50,
      },
    },
  );
}

export async function createRelease(serviceId: string, payload: API.ReleaseCreateRequest) {
  return request<API.Release>(servicePath(serviceId, '/releases'), {
    method: 'POST',
    data: payload,
  });
}

export async function activateRelease(serviceId: string, releaseVersion: string) {
  return request<API.Release>(
    servicePath(serviceId, `/releases/${encodeURIComponent(releaseVersion)}:activate`),
    { method: 'POST' },
  );
}

export async function rollbackRelease(serviceId: string, releaseVersion: string) {
  return request<API.Release>(
    servicePath(serviceId, `/releases/${encodeURIComponent(releaseVersion)}:rollback`),
    { method: 'POST' },
  );
}

export async function listIntentRouteCandidates(
  serviceId: string,
  params: { source?: 'current_catalog' | 'active_release'; environment?: string } = {},
) {
  return request<API.IntentRouteCandidate[]>(
    servicePath(serviceId, '/intent-route-candidates'),
    {
      method: 'GET',
      params: {
        source: params.source ?? 'current_catalog',
        environment: params.environment,
      },
    },
  );
}

export async function createApiKey(payload: API.ApiKeyCreateRequest) {
  return request<API.ApiKeyCreateResponse>('/api-keys', {
    method: 'POST',
    data: payload,
  });
}

export async function createServiceApiKey(
  serviceId: string,
  payload: API.ServiceApiKeyCreateRequest,
) {
  return request<API.ApiKeyCreateResponse>(servicePath(serviceId, '/api-keys'), {
    method: 'POST',
    data: payload,
  });
}

export async function listApiKeys(
  params: {
    service_id?: string;
    environment?: string;
    status?: API.ApiKeyStatus;
    limit?: number;
  } = {},
) {
  return request<API.ApiKey[]>('/api-keys', {
    method: 'GET',
    params: {
      service_id: params.service_id,
      environment: params.environment,
      status: params.status,
      limit: params.limit ?? 50,
    },
  });
}

export async function listServiceApiKeys(
  serviceId: string,
  params: {
    environment?: string;
    status?: API.ApiKeyStatus;
    limit?: number;
  } = {},
) {
  return request<API.ApiKey[]>(servicePath(serviceId, '/api-keys'), {
    method: 'GET',
    params: {
      environment: params.environment,
      status: params.status,
      limit: params.limit ?? 50,
    },
  });
}

export async function revokeApiKey(keyId: string) {
  return request<API.ApiKey>(`/api-keys/${encodeURIComponent(keyId)}:revoke`, {
    method: 'POST',
  });
}

export async function revokeServiceApiKey(serviceId: string, keyId: string) {
  return request<API.ApiKey>(
    servicePath(serviceId, `/api-keys/${encodeURIComponent(keyId)}:revoke`),
    {
      method: 'POST',
    },
  );
}

export async function fetchRuntimeSetupGuidance(
  serviceId: string,
  params: {
    environment?: string;
    app_id?: string;
    key_id?: string;
  } = {},
) {
  return request<API.RuntimeSetupGuidance>(servicePath(serviceId, '/runtime-setup'), {
    method: 'GET',
    params,
  });
}

export async function listRuntimeLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.RuntimeLog[]>(servicePath(serviceId, '/runtime-logs'), {
    method: 'GET',
    params: { limit: RECENT_RUNTIME_LOG_LIMIT },
  });
  return toReadOnlyTableResult(filterRuntimeLogs(rows, params));
}

export async function fetchRuntimeLog(serviceId: string, traceId: string) {
  return request<API.RuntimeLog>(
    servicePath(serviceId, `/runtime-logs/${encodeURIComponent(traceId)}`),
    { method: 'GET' },
  );
}

export async function listAuditLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.AuditLog[]>(servicePath(serviceId, '/audit-logs'), {
    method: 'GET',
    params: {
      limit: RECENT_AUDIT_LOG_LIMIT,
      event_type: params.event_type || undefined,
      trace_id: params.trace_id || undefined,
    },
  });
  return toReadOnlyTableResult(rows);
}
