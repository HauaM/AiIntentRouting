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

type LegacyCatalogVersionDiff = Omit<
  API.CatalogVersionDiff,
  'added_examples' | 'removed_examples' | 'changed_examples'
> & {
  added_examples: unknown[];
  removed_examples: unknown[];
  changed_examples: unknown[];
};

export async function createService(payload: API.ServiceCreateRequest) {
  return request<API.Service>('/services', {
    method: 'POST',
    data: payload,
  });
}

export async function searchAdminUsers(
  params: { query?: string; limit?: number } = {},
) {
  return request<API.AdminUserLookup[]>('/users', {
    method: 'GET',
    params: {
      query: params.query,
      limit: params.limit ?? 25,
    },
  });
}

export async function searchServiceUsers(
  serviceId: string,
  params: { query?: string; limit?: number } = {},
) {
  return request<API.AdminUserLookup[]>(servicePath(serviceId, '/users'), {
    method: 'GET',
    params: {
      query: params.query,
      limit: params.limit ?? 25,
    },
  });
}

export const listAdminUsers = searchAdminUsers;

export async function listManagedAdminUsers(
  params: { organization_user_id?: string; query?: string; limit?: number } = {},
) {
  return request<API.ManagedAdminUser[]>('/admin-users', {
    method: 'GET',
    params: {
      organization_user_id: params.organization_user_id,
      query: params.query,
      limit: params.limit ?? 25,
    },
  });
}

export async function createManagedAdminUser(
  payload: API.ManagedAdminUserCreateRequest,
) {
  return request<API.ManagedAdminUser>('/admin-users', {
    method: 'POST',
    data: payload,
  });
}

export async function patchManagedAdminUser(
  userId: string,
  payload: API.ManagedAdminUserPatchRequest,
) {
  return request<API.ManagedAdminUser>(
    `/admin-users/${encodeURIComponent(userId)}`,
    {
      method: 'PATCH',
      data: payload,
    },
  );
}

export async function listAdminAccessRequests(
  params: { status?: API.AdminAccessRequestStatus; limit?: number } = {},
) {
  return request<API.AdminAccessRequest[]>('/admin-access-requests', {
    method: 'GET',
    params,
  });
}

export async function approveAdminAccessRequest(
  requestId: string,
  payload: { decision_reason: string },
) {
  return request<API.AdminAccessRequest>(
    `/admin-access-requests/${encodeURIComponent(requestId)}/approve`,
    {
      method: 'POST',
      data: payload,
    },
  );
}

export async function rejectAdminAccessRequest(
  requestId: string,
  payload: { decision_reason: string },
) {
  return request<API.AdminAccessRequest>(
    `/admin-access-requests/${encodeURIComponent(requestId)}/reject`,
    {
      method: 'POST',
      data: payload,
    },
  );
}

export async function transferSystemAdmin(
  payload: API.SystemAdminTransferRequest,
) {
  return request<API.ManagedAdminUser>('/system-admin-transfer', {
    method: 'POST',
    data: payload,
  });
}

export async function listDepartments(
  params: { query?: string; use_yn?: API.UseYn; limit?: number } = {},
) {
  return request<API.Department[]>('/departments', {
    method: 'GET',
    params: {
      query: params.query,
      use_yn: params.use_yn,
      limit: params.limit ?? 100,
    },
  });
}

export async function createDepartment(payload: API.DepartmentCreateRequest) {
  return request<API.Department>('/departments', {
    method: 'POST',
    data: payload,
  });
}

export async function patchDepartment(
  departmentId: string,
  payload: API.DepartmentPatchRequest,
) {
  return request<API.Department>(`/departments/${encodeURIComponent(departmentId)}`, {
    method: 'PATCH',
    data: payload,
  });
}

export async function deleteDepartment(departmentId: string) {
  return request<API.Department>(`/departments/${encodeURIComponent(departmentId)}`, {
    method: 'DELETE',
  });
}

export async function listOrganizationUsers(
  params: {
    query?: string;
    department_id?: string;
    use_yn?: API.UseYn;
    limit?: number;
  } = {},
) {
  return request<API.OrganizationUser[]>('/organization-users', {
    method: 'GET',
    params: {
      query: params.query,
      department_id: params.department_id,
      use_yn: params.use_yn,
      limit: params.limit ?? 100,
    },
  });
}

export async function createOrganizationUser(
  payload: API.OrganizationUserCreateRequest,
) {
  return request<API.OrganizationUser>('/organization-users', {
    method: 'POST',
    data: payload,
  });
}

export async function patchOrganizationUser(
  organizationUserId: string,
  payload: API.OrganizationUserPatchRequest,
) {
  return request<API.OrganizationUser>(
    `/organization-users/${encodeURIComponent(organizationUserId)}`,
    {
      method: 'PATCH',
      data: payload,
    },
  );
}

export async function deleteOrganizationUser(organizationUserId: string) {
  return request<API.OrganizationUser>(
    `/organization-users/${encodeURIComponent(organizationUserId)}`,
    {
      method: 'DELETE',
    },
  );
}

export async function listServiceMembers(serviceId: string) {
  return request<API.ServiceMember[]>(servicePath(serviceId, '/members'), {
    method: 'GET',
  });
}

export async function grantServiceRole(
  serviceId: string,
  userId: string,
  payload: API.ServiceRoleGrantRequest,
) {
  return request<API.ServiceRoleGrantResponse>(
    servicePath(serviceId, `/members/${encodeURIComponent(userId)}/roles`),
    {
      method: 'POST',
      data: payload,
    },
  );
}

export async function revokeServiceRole(
  serviceId: string,
  userId: string,
  role: API.ServiceRole,
) {
  return request<API.ServiceRoleRevokeResponse>(
    servicePath(
      serviceId,
      `/members/${encodeURIComponent(userId)}/roles/${encodeURIComponent(role)}`,
    ),
    { method: 'DELETE' },
  );
}

export async function fetchRuntimeMetrics(
  serviceId: string,
  windowHours: number,
  environment?: 'dev' | 'qa' | 'prod',
) {
  const params: { window_hours: number; environment?: 'dev' | 'qa' | 'prod' } = {
    window_hours: windowHours,
  };
  if (environment) {
    params.environment = environment;
  }
  return request<API.RuntimeMetrics>(servicePath(serviceId, '/runtime-metrics'), {
    method: 'GET',
    params,
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

export async function deleteIntent(serviceId: string, intentId: string) {
  return request<void>(
    servicePath(serviceId, `/intents/${encodeURIComponent(intentId)}`),
    {
      method: 'DELETE',
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

export async function patchExample(
  serviceId: string,
  exampleId: string,
  payload: API.ExamplePatchRequest,
) {
  return request<API.Example>(
    servicePath(serviceId, `/examples/${encodeURIComponent(exampleId)}`),
    {
      method: 'PATCH',
      data: payload,
    },
  );
}

export async function deleteExample(serviceId: string, exampleId: string) {
  return request<void>(
    servicePath(serviceId, `/examples/${encodeURIComponent(exampleId)}`),
    {
      method: 'DELETE',
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

export async function createCatalogVersion(
  serviceId: string,
  payload: API.CatalogVersionCreateRequest,
) {
  return request<API.CatalogVersion>(servicePath(serviceId, '/catalog-versions'), {
    method: 'POST',
    data: payload,
  });
}

export async function listCatalogVersions(
  serviceId: string,
  params: { limit?: number; status?: API.CatalogVersionStatus } = {},
) {
  return request<API.CatalogVersionListItem[]>(
    servicePath(serviceId, '/catalog-versions'),
    {
      method: 'GET',
      params: {
        limit: params.limit ?? 50,
        status: params.status,
      },
    },
  );
}

export async function fetchCatalogVersion(serviceId: string, catalogVersion: string) {
  return request<API.CatalogVersion>(
    servicePath(serviceId, `/catalog-versions/${encodeURIComponent(catalogVersion)}`),
    { method: 'GET' },
  );
}

export async function fetchCatalogVersionDiff(
  serviceId: string,
  catalogVersion: string,
  params: { compare_to?: string | null } = {},
) {
  const diff = await request<API.CatalogVersionDiff | LegacyCatalogVersionDiff>(
    servicePath(
      serviceId,
      `/catalog-versions/${encodeURIComponent(catalogVersion)}/diff`,
    ),
    {
      method: 'GET',
      params: { compare_to: params.compare_to || undefined },
    },
  );
  return hydrateLegacyCatalogVersionDiff(serviceId, catalogVersion, params.compare_to, diff);
}

const isCatalogVersionDiffExample = (
  value: unknown,
): value is API.CatalogVersionDiffExample => {
  if (!value || typeof value !== 'object') return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.intent_id === 'string' &&
    typeof record.intent_display_name === 'string' &&
    typeof record.route_key === 'string' &&
    (record.example_type === 'positive' || record.example_type === 'negative') &&
    typeof record.text_masked === 'string'
  );
};

const usesLegacyExampleIds = (diff: LegacyCatalogVersionDiff) =>
  ['added_examples', 'removed_examples', 'changed_examples'].some((key) => {
    const values = diff[key as keyof Pick<
      LegacyCatalogVersionDiff,
      'added_examples' | 'removed_examples' | 'changed_examples'
    >] as unknown[];
    return Array.isArray(values) && values.some((value) => typeof value === 'string');
  });

const catalogVersionExampleMap = (snapshot: unknown) => {
  const examples = new Map<string, API.CatalogVersionDiffExample>();
  if (!snapshot || typeof snapshot !== 'object') return examples;
  const intents = (snapshot as Record<string, unknown>).intents;
  if (!Array.isArray(intents)) return examples;

  intents.forEach((intent) => {
    if (!intent || typeof intent !== 'object') return;
    const intentRecord = intent as Record<string, unknown>;
    const intentExamples = intentRecord.examples;
    if (!Array.isArray(intentExamples)) return;

    intentExamples.forEach((example) => {
      if (!example || typeof example !== 'object') return;
      const exampleRecord = example as Record<string, unknown>;
      const exampleId = exampleRecord.example_id;
      const exampleType = exampleRecord.example_type;
      const textMasked = exampleRecord.text_masked;
      if (
        typeof exampleId !== 'string' ||
        (exampleType !== 'positive' && exampleType !== 'negative') ||
        typeof textMasked !== 'string'
      ) {
        return;
      }
      examples.set(exampleId, {
        intent_id: String(intentRecord.intent_id ?? '-'),
        intent_display_name: String(intentRecord.display_name ?? '-'),
        route_key: String(intentRecord.route_key ?? '-'),
        example_type: exampleType,
        text_masked: textMasked,
      });
    });
  });

  return examples;
};

const hydrateExampleDiffItems = (
  items: unknown[],
  primary: Map<string, API.CatalogVersionDiffExample>,
  fallback?: Map<string, API.CatalogVersionDiffExample>,
) =>
  items.flatMap((item) => {
    if (isCatalogVersionDiffExample(item)) return [item];
    if (typeof item !== 'string') return [];
    const hydrated = primary.get(item) ?? fallback?.get(item);
    return hydrated ? [hydrated] : [];
  });

async function hydrateLegacyCatalogVersionDiff(
  serviceId: string,
  catalogVersion: string,
  compareTo: string | null | undefined,
  diff: API.CatalogVersionDiff | LegacyCatalogVersionDiff,
): Promise<API.CatalogVersionDiff> {
  const legacyDiff = diff as LegacyCatalogVersionDiff;
  if (!usesLegacyExampleIds(legacyDiff)) return diff as API.CatalogVersionDiff;

  const [targetVersion, baselineVersion] = await Promise.all([
    fetchCatalogVersion(serviceId, catalogVersion),
    compareTo ? fetchCatalogVersion(serviceId, compareTo) : Promise.resolve(undefined),
  ]);
  const targetExamples = catalogVersionExampleMap(targetVersion.snapshot);
  const baselineExamples = catalogVersionExampleMap(baselineVersion?.snapshot);

  return {
    ...diff,
    added_examples: hydrateExampleDiffItems(legacyDiff.added_examples, targetExamples),
    removed_examples: hydrateExampleDiffItems(
      legacyDiff.removed_examples,
      baselineExamples,
    ),
    changed_examples: hydrateExampleDiffItems(
      legacyDiff.changed_examples,
      targetExamples,
      baselineExamples,
    ),
  };
}

export async function deactivateCatalogVersion(
  serviceId: string,
  catalogVersion: string,
) {
  return request<API.CatalogVersionLifecycle>(
    servicePath(
      serviceId,
      `/catalog-versions/${encodeURIComponent(catalogVersion)}:deactivate`,
    ),
    { method: 'POST' },
  );
}

export async function loadCatalogVersionToDraft(
  serviceId: string,
  catalogVersion: string,
) {
  return request<API.CatalogVersion>(
    servicePath(
      serviceId,
      `/catalog-versions/${encodeURIComponent(catalogVersion)}:load-to-draft`,
    ),
    { method: 'POST' },
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

export async function fetchTestRunDiagnostics(serviceId: string, testRunId: string) {
  return request<API.TestRunDiagnostics>(
    servicePath(
      serviceId,
      `/test-runs/${encodeURIComponent(testRunId)}/diagnostics`,
    ),
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
  params: {
    source?: 'current_catalog' | 'active_release' | 'released_catalog';
    environment?: string;
  } = {},
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

export async function revealServiceApiKey(serviceId: string, keyId: string) {
  return request<API.ApiKeyRevealResponse>(
    servicePath(serviceId, `/api-keys/${encodeURIComponent(keyId)}:reveal`),
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
  const requestParams: { limit: number; environment?: string } = {
    limit: RECENT_RUNTIME_LOG_LIMIT,
  };
  if (params.environment) {
    requestParams.environment = params.environment;
  }
  const rows = await request<API.RuntimeLog[]>(servicePath(serviceId, '/runtime-logs'), {
    method: 'GET',
    params: requestParams,
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

export async function listPermissionAdminUsers(
  params: API.PermissionAdminUsersQueryParams = {},
) {
  return request<API.PermissionAdminUserSummary[]>(
    '/permission-management/admin-users',
    {
      method: 'GET',
      params,
    },
  );
}

export async function listPermissionServiceRoles(
  params: API.PermissionServiceRolesQueryParams = {},
) {
  return request<API.PermissionServiceRoleSummary[]>(
    '/permission-management/service-roles',
    {
      method: 'GET',
      params,
    },
  );
}

export async function listPermissionAuditLogs(
  params: API.PermissionAuditLogsQueryParams = {},
) {
  return request<API.AuditLog[]>('/permission-management/audit-logs', {
    method: 'GET',
    params,
  });
}

export async function listPermissionRiskFindings(
  params: API.PermissionRiskFindingsQueryParams = {},
) {
  return request<API.PermissionRiskFinding[]>(
    '/permission-management/risk-findings',
    {
      method: 'GET',
      params,
    },
  );
}
