import { request } from '@umijs/max';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  approveAdminAccessRequest,
  activateRelease,
  approveExample,
  createApiKey,
  createCatalogVersion,
  createDepartment,
  createExample,
  createIntent,
  createOrganizationUser,
  createPolicyVersion,
  createRelease,
  createServiceApiKey,
  createService,
  createTestRun,
  createManagedAdminUser,
  fetchRuntimeSetupGuidance,
  fetchTestRun,
  fetchTestRunResults,
  grantServiceRole,
  listApiKeys,
  listAdminAccessRequests,
  listAdminUsers,
  listCatalogVersions,
  listDepartments,
  listManagedAdminUsers,
  listExamples,
  listIntentRouteCandidates,
  listOrganizationUsers,
  listPermissionAdminUsers,
  listPermissionAuditLogs,
  listPermissionRiskFindings,
  listPermissionServiceRoles,
  listPolicyVersions,
  listReleases,
  listReleaseCandidates,
  listServiceMembers,
  listServiceApiKeys,
  listTestRuns,
  deleteExample,
  deleteIntent,
  patchIntent,
  patchExample,
  patchManagedAdminUser,
  patchDepartment,
  patchOrganizationUser,
  rejectAdminAccessRequest,
  revokeApiKey,
  deleteDepartment,
  deleteOrganizationUser,
  revokeServiceRole,
  revokeServiceApiKey,
  rollbackRelease,
  searchAdminUsers,
  transferSystemAdmin,
} from './adminServices';

vi.mock('@umijs/max', () => ({
  request: vi.fn(),
}));

const requestMock = vi.mocked(request);

describe('admin service Phase 1 write flow requests', () => {
  beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockResolvedValue({});
  });

  it('creates services with POST body and session-cookie auth', async () => {
    const payload: API.ServiceCreateRequest = {
      service_id: 'svc-c1-onboarding',
      display_name: 'C1 Onboarding',
      environment: 'dev',
      default_threshold_preset: 'balanced',
      max_input_tokens: 256,
    };

    await createService(payload);

    expect(requestMock).toHaveBeenCalledWith('/services', {
      method: 'POST',
      data: payload,
    });
  });

  it('creates intents with encoded service id and POST body', async () => {
    const payload: API.IntentCreateRequest = {
      intent_id: 'password-reset',
      domain: 'it',
      display_name: 'Password reset',
      description: 'Reset passwords.',
      route_key: 'it.password.self_service',
    };

    await createIntent('svc/admin', payload);

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/intents', {
      method: 'POST',
      data: payload,
    });
  });

  it('patches intents with encoded service and intent ids', async () => {
    const payload: API.IntentPatchRequest = { status: 'active' };

    await patchIntent('svc/admin', 'intent/a', payload);

    expect(requestMock).toHaveBeenCalledWith(
      '/services/svc%2Fadmin/intents/intent%2Fa',
      {
        method: 'PATCH',
        data: payload,
      },
    );
  });

  it('lists and creates examples under an intent', async () => {
    const payload: API.ExampleCreateRequest = {
      example_type: 'positive',
      text_raw: 'Need to reset my password',
      source: 'admin',
    };

    await listExamples('svc/admin', 'intent/a');
    await createExample('svc/admin', 'intent/a', payload);

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/services/svc%2Fadmin/intents/intent%2Fa/examples',
      { method: 'GET' },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/services/svc%2Fadmin/intents/intent%2Fa/examples',
      {
        method: 'POST',
        data: payload,
      },
    );
  });

  it('approves examples with PATCH', async () => {
    await approveExample('svc/admin', 'example/a');

    expect(requestMock).toHaveBeenCalledWith(
      '/services/svc%2Fadmin/examples/example%2Fa:approve',
      { method: 'PATCH' },
    );
  });

  it('patches examples and deletes embedded catalog rows with encoded ids', async () => {
    const payload: API.ExamplePatchRequest = {
      example_type: 'negative',
      text_raw: 'Password reset needed',
      source: 'admin-edit',
      test_case_id: null,
    };

    await patchExample('svc/admin', 'example/a', payload);
    await deleteExample('svc/admin', 'example/a');
    await deleteIntent('svc/admin', 'intent/a');

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/services/svc%2Fadmin/examples/example%2Fa',
      {
        method: 'PATCH',
        data: payload,
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/services/svc%2Fadmin/examples/example%2Fa',
      { method: 'DELETE' },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      '/services/svc%2Fadmin/intents/intent%2Fa',
      { method: 'DELETE' },
    );
  });

  it('creates policy versions', async () => {
    const payload: API.PolicyVersionCreateRequest = {
      threshold_preset: 'balanced',
      clarify_margin: 0.1,
      min_candidate_score: 0.2,
      fallback_score: 0.3,
    };

    await createPolicyVersion('svc/admin', payload);

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/policy-versions', {
      method: 'POST',
      data: payload,
    });
  });

  it('creates catalog versions', async () => {
    const payload: API.CatalogVersionCreateRequest = {
      description: 'Catalog baseline for regression tests',
    };

    await createCatalogVersion('svc/admin', payload);

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/catalog-versions', {
      method: 'POST',
      data: payload,
    });
  });

  it('creates, fetches, and lists test run results', async () => {
    const payload: API.TestRunCreateRequest = {
      policy_version: 'pol-1',
      intent_catalog_version: 'cat-1',
      source_filename: 'cases.csv',
      csv_text: 'case_id,query',
    };

    await createTestRun('svc/admin', payload);
    await fetchTestRun('svc/admin', 'run/a');
    await fetchTestRunResults('svc/admin', 'run/a');

    expect(requestMock).toHaveBeenNthCalledWith(1, '/services/svc%2Fadmin/test-runs', {
      method: 'POST',
      data: payload,
    });
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/services/svc%2Fadmin/test-runs/run%2Fa',
      { method: 'GET' },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      '/services/svc%2Fadmin/test-runs/run%2Fa/results',
      { method: 'GET' },
    );
  });

  it('lists and creates releases', async () => {
    const payload: API.ReleaseCreateRequest = {
      environment: 'prod',
      policy_version: 'pol-1',
      intent_catalog_version: 'cat-1',
      test_run_id: 'run-1',
    };

    await listReleases('svc/admin', 'prod');
    await createRelease('svc/admin', payload);

    expect(requestMock).toHaveBeenNthCalledWith(1, '/services/svc%2Fadmin/releases', {
      method: 'GET',
      params: { environment: 'prod' },
    });
    expect(requestMock).toHaveBeenNthCalledWith(2, '/services/svc%2Fadmin/releases', {
      method: 'POST',
      data: payload,
    });
  });

  it('activates and rolls back releases', async () => {
    await activateRelease('svc/admin', 'rel/a');
    await rollbackRelease('svc/admin', 'rel/a');

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/services/svc%2Fadmin/releases/rel%2Fa:activate',
      { method: 'POST' },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/services/svc%2Fadmin/releases/rel%2Fa:rollback',
      { method: 'POST' },
    );
  });

  it('creates and revokes API keys', async () => {
    const payload: API.ApiKeyCreateRequest = {
      service_id: 'svc/admin',
      environment: 'prod',
      app_id: 'app-web',
      expires_in_days: 30,
    };

    await createApiKey(payload);
    await revokeApiKey('key/a');

    expect(requestMock).toHaveBeenNthCalledWith(1, '/api-keys', {
      method: 'POST',
      data: payload,
    });
    expect(requestMock).toHaveBeenNthCalledWith(2, '/api-keys/key%2Fa:revoke', {
      method: 'POST',
    });
  });

  it('uses service-scoped API key lifecycle endpoints without trusted headers', async () => {
    const payload: API.ServiceApiKeyCreateRequest = {
      environment: 'prod',
      app_id: 'app-web',
      allowed_intents: ['billing_refund'],
      allowed_route_keys: ['billing.refund.request'],
      expires_in_days: 30,
    };

    await createServiceApiKey('svc/admin', payload);
    await listServiceApiKeys('svc/admin', { environment: 'prod', status: 'active' });
    await revokeServiceApiKey('svc/admin', 'key/a');
    await fetchRuntimeSetupGuidance('svc/admin', {
      environment: 'prod',
      app_id: 'app-web',
      key_id: 'key/a',
    });

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/services/svc%2Fadmin/api-keys',
      {
        method: 'POST',
        data: payload,
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/services/svc%2Fadmin/api-keys',
      {
        method: 'GET',
        params: { environment: 'prod', status: 'active', limit: 50 },
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      '/services/svc%2Fadmin/api-keys/key%2Fa:revoke',
      { method: 'POST' },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      4,
      '/services/svc%2Fadmin/runtime-setup',
      {
        method: 'GET',
        params: {
          environment: 'prod',
          app_id: 'app-web',
          key_id: 'key/a',
        },
      },
    );
    const calls = requestMock.mock.calls as unknown as Array<
      [string, Record<string, unknown>]
    >;
    for (const [, options] of calls) {
      expect(options).not.toHaveProperty('headers');
    }
  });

  it('uses C-2 membership endpoints without trusted headers', async () => {
    await searchAdminUsers({ query: 'developer@example.com' });
    await listServiceMembers('svc/admin');
    await grantServiceRole('svc/admin', 'user/a', { role: 'service_developer' });
    await revokeServiceRole('svc/admin', 'user/a', 'service_developer');

    expect(requestMock).toHaveBeenNthCalledWith(1, '/users', {
      method: 'GET',
      params: { query: 'developer@example.com', limit: 25 },
    });
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/services/svc%2Fadmin/members',
      { method: 'GET' },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      '/services/svc%2Fadmin/members/user%2Fa/roles',
      {
        method: 'POST',
        data: { role: 'service_developer' },
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      4,
      '/services/svc%2Fadmin/members/user%2Fa/roles/service_developer',
      { method: 'DELETE' },
    );
    const calls = requestMock.mock.calls as unknown as Array<
      [string, Record<string, unknown>]
    >;
    for (const [, options] of calls) {
      expect(options).not.toHaveProperty('headers');
    }
  });

  it('uses organization directory endpoints without trusted headers', async () => {
    await createDepartment({ dept_number: '0969', name: 'IT지원부' });
    await listDepartments({ query: 'IT', use_yn: 'Y' });
    await createOrganizationUser({
      user_number: '21P0031',
      name: '홍길동',
      department_id: 'dept-1',
    });
    await patchDepartment('dept/1', { name: '정보지원부', use_yn: 'N' });
    await deleteDepartment('dept/1');
    await listOrganizationUsers({ query: '홍길동', department_id: 'dept-1', use_yn: 'Y' });
    await patchOrganizationUser('user/1', { department_id: 'dept-2', use_yn: 'N' });
    await deleteOrganizationUser('user/1');

    expect(requestMock).toHaveBeenNthCalledWith(1, '/departments', {
      method: 'POST',
      data: { dept_number: '0969', name: 'IT지원부' },
    });
    expect(requestMock).toHaveBeenNthCalledWith(2, '/departments', {
      method: 'GET',
      params: { query: 'IT', use_yn: 'Y', limit: 100 },
    });
    expect(requestMock).toHaveBeenNthCalledWith(3, '/organization-users', {
      method: 'POST',
      data: {
        user_number: '21P0031',
        name: '홍길동',
        department_id: 'dept-1',
      },
    });
    expect(requestMock).toHaveBeenNthCalledWith(4, '/departments/dept%2F1', {
      method: 'PATCH',
      data: { name: '정보지원부', use_yn: 'N' },
    });
    expect(requestMock).toHaveBeenNthCalledWith(5, '/departments/dept%2F1', {
      method: 'DELETE',
    });
    expect(requestMock).toHaveBeenNthCalledWith(6, '/organization-users', {
      method: 'GET',
      params: {
        query: '홍길동',
        department_id: 'dept-1',
        use_yn: 'Y',
        limit: 100,
      },
    });
    expect(requestMock).toHaveBeenNthCalledWith(7, '/organization-users/user%2F1', {
      method: 'PATCH',
      data: { department_id: 'dept-2', use_yn: 'N' },
    });
    expect(requestMock).toHaveBeenNthCalledWith(8, '/organization-users/user%2F1', {
      method: 'DELETE',
    });
    const calls = requestMock.mock.calls as unknown as Array<
      [string, Record<string, unknown>]
    >;
    for (const [, options] of calls) {
      expect(options).not.toHaveProperty('headers');
    }
  });

  it('uses admin user management endpoints without trusted headers', async () => {
    const createPayload: API.ManagedAdminUserCreateRequest = {
      organization_user_id: 'org/user/1',
      email: 'admin@example.com',
      display_name: 'Admin User',
      status: 'disabled',
      global_roles: [],
    };

    await listManagedAdminUsers({ organization_user_id: 'org/user/1' });
    await createManagedAdminUser(createPayload);
    await patchManagedAdminUser('admin/user/1', {
      status: 'active',
      global_roles: ['system_admin'],
    });

    expect(requestMock).toHaveBeenNthCalledWith(1, '/admin-users', {
      method: 'GET',
      params: { organization_user_id: 'org/user/1', query: undefined, limit: 25 },
    });
    expect(requestMock).toHaveBeenNthCalledWith(2, '/admin-users', {
      method: 'POST',
      data: createPayload,
    });
    expect(requestMock).toHaveBeenNthCalledWith(3, '/admin-users/admin%2Fuser%2F1', {
      method: 'PATCH',
      data: { status: 'active', global_roles: ['system_admin'] },
    });
    const calls = requestMock.mock.calls as unknown as Array<
      [string, Record<string, unknown>]
    >;
    for (const [, options] of calls) {
      expect(options).not.toHaveProperty('headers');
    }
  });

  it('uses admin access request endpoints without trusted headers', async () => {
    await listAdminAccessRequests({ status: 'pending', limit: 25 });
    await approveAdminAccessRequest('request/1', {
      decision_reason: 'Approved for scoped Admin UI access',
    });
    await rejectAdminAccessRequest('request/2', {
      decision_reason: 'Missing onboarding prerequisites',
    });

    expect(requestMock).toHaveBeenNthCalledWith(1, '/admin-access-requests', {
      method: 'GET',
      params: { status: 'pending', limit: 25 },
    });
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/admin-access-requests/request%2F1/approve',
      {
        method: 'POST',
        data: { decision_reason: 'Approved for scoped Admin UI access' },
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      '/admin-access-requests/request%2F2/reject',
      {
        method: 'POST',
        data: { decision_reason: 'Missing onboarding prerequisites' },
      },
    );
    const calls = requestMock.mock.calls as unknown as Array<
      [string, Record<string, unknown>]
    >;
    for (const [, options] of calls) {
      expect(options).not.toHaveProperty('headers');
    }
  });

  it('uses the guarded system_admin transfer endpoint without trusted headers', async () => {
    await transferSystemAdmin({
      from_admin_user_id: 'admin-1',
      to_admin_user_id: 'admin-2',
      reason: 'Transfer platform ownership',
    });

    expect(requestMock).toHaveBeenCalledWith('/system-admin-transfer', {
      method: 'POST',
      data: {
        from_admin_user_id: 'admin-1',
        to_admin_user_id: 'admin-2',
        reason: 'Transfer platform ownership',
      },
    });
    const [, options] = requestMock.mock.calls[0] as unknown as [
      string,
      Record<string, unknown>,
    ];
    expect(options).not.toHaveProperty('headers');
  });

  it('lists admin users with a default limit and optional empty query', async () => {
    await searchAdminUsers();

    expect(requestMock).toHaveBeenCalledWith('/users', {
      method: 'GET',
      params: { query: undefined, limit: 25 },
    });
  });

  it('keeps listAdminUsers as a compatibility alias for user search', async () => {
    await listAdminUsers({ query: 'owner@example.com', limit: 10 });

    expect(requestMock).toHaveBeenCalledWith('/users', {
      method: 'GET',
      params: { query: 'owner@example.com', limit: 10 },
    });
  });

  it('loads workflow candidate paths', async () => {
    await listPolicyVersions('svc/admin');
    await listCatalogVersions('svc/admin');
    await listTestRuns('svc/admin', { gate_passed: true, risk_passed: true });
    await listReleaseCandidates('svc/admin');
    await listIntentRouteCandidates('svc/admin', { source: 'active_release' });
    await listServiceApiKeys('svc/admin');

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/policy-versions', {
      method: 'GET',
      params: { limit: 50 },
    });
    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/catalog-versions', {
      method: 'GET',
      params: { limit: 50, status: undefined },
    });
    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/test-runs', {
      method: 'GET',
      params: { gate_passed: true, risk_passed: true, limit: 50 },
    });
    expect(requestMock).toHaveBeenCalledWith(
      '/services/svc%2Fadmin/release-candidates',
      {
        method: 'GET',
        params: { environment: undefined, limit: 50 },
      },
    );
    expect(requestMock).toHaveBeenCalledWith(
      '/services/svc%2Fadmin/intent-route-candidates',
      {
        method: 'GET',
        params: { source: 'active_release', environment: undefined },
      },
    );
    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/api-keys', {
      method: 'GET',
      params: {
        environment: undefined,
        status: undefined,
        limit: 50,
      },
    });
  });

  it('lists active catalog versions with explicit lifecycle filters', async () => {
    await listCatalogVersions('svc/admin', { limit: 100, status: 'active' });

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/catalog-versions', {
      method: 'GET',
      params: { limit: 100, status: 'active' },
    });
  });

  it('uses Permission Management read endpoints with GET query params only', async () => {
    await listPermissionAdminUsers({
      query: 'admin@example.com',
      status: 'active',
      global_role: 'system_admin',
      organization_link: 'linked',
      organization_use_yn: 'Y',
      limit: 100,
    });
    await listPermissionServiceRoles({
      service_id: 'svc/admin',
      user_id: 'admin/user',
      role: 'service_owner',
      query: 'IT지원부',
      limit: 200,
    });
    await listPermissionAuditLogs({
      event_group: 'service_membership',
      event_type: 'service_membership.role_granted',
      actor_id: 'system-admin',
      target_id: 'svc/admin:admin/user:service_owner',
      service_id: 'svc/admin',
      limit: 100,
    });
    await listPermissionRiskFindings();

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/permission-management/admin-users',
      {
        method: 'GET',
        params: {
          query: 'admin@example.com',
          status: 'active',
          global_role: 'system_admin',
          organization_link: 'linked',
          organization_use_yn: 'Y',
          limit: 100,
        },
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/permission-management/service-roles',
      {
        method: 'GET',
        params: {
          service_id: 'svc/admin',
          user_id: 'admin/user',
          role: 'service_owner',
          query: 'IT지원부',
          limit: 200,
        },
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      '/permission-management/audit-logs',
      {
        method: 'GET',
        params: {
          event_group: 'service_membership',
          event_type: 'service_membership.role_granted',
          actor_id: 'system-admin',
          target_id: 'svc/admin:admin/user:service_owner',
          service_id: 'svc/admin',
          limit: 100,
        },
      },
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      4,
      '/permission-management/risk-findings',
      {
        method: 'GET',
        params: {},
      },
    );
    const calls = requestMock.mock.calls as unknown as Array<
      [string, Record<string, unknown>]
    >;
    for (const [, options] of calls) {
      expect(options).not.toHaveProperty('data');
      expect(options).not.toHaveProperty('headers');
    }
  });
});
