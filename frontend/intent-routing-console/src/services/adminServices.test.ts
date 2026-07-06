import { request } from '@umijs/max';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  activateRelease,
  approveExample,
  createApiKey,
  createCatalogVersion,
  createExample,
  createIntent,
  createPolicyVersion,
  createRelease,
  createTestRun,
  fetchTestRun,
  fetchTestRunResults,
  listApiKeys,
  listCatalogVersions,
  listExamples,
  listIntentRouteCandidates,
  listPolicyVersions,
  listReleases,
  listReleaseCandidates,
  listTestRuns,
  patchIntent,
  revokeApiKey,
  rollbackRelease,
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
    await createCatalogVersion('svc/admin');

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/catalog-versions', {
      method: 'POST',
    });
  });

  it('creates, fetches, and lists test run results', async () => {
    const payload: API.TestRunCreateRequest = {
      policy_version: 'pol-1',
      intent_catalog_version: 'cat-1',
      threshold_preset: 'strict',
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

  it('loads workflow candidate paths', async () => {
    await listPolicyVersions('svc/admin');
    await listCatalogVersions('svc/admin');
    await listTestRuns('svc/admin', { gate_passed: true, risk_passed: true });
    await listReleaseCandidates('svc/admin');
    await listIntentRouteCandidates('svc/admin', { source: 'active_release' });
    await listApiKeys({ service_id: 'svc/admin' });

    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/policy-versions', {
      method: 'GET',
      params: { limit: 50 },
    });
    expect(requestMock).toHaveBeenCalledWith('/services/svc%2Fadmin/catalog-versions', {
      method: 'GET',
      params: { limit: 50 },
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
    expect(requestMock).toHaveBeenCalledWith('/api-keys', {
      method: 'GET',
      params: {
        service_id: 'svc/admin',
        environment: undefined,
        status: undefined,
        limit: 50,
      },
    });
  });
});
