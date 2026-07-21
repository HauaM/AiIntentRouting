import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { runRuntimeIntentRoute } from './runtimeServices';

const fetchMock = vi.fn();

describe('runtime live test service', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('calls the runtime endpoint with revealed API-key auth and no Admin UI credentials', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          trace_id: 'irt-live-1',
          decision: 'confident',
          request_id: 'admin-live-1',
          intent_id: 'password_reset',
          route_key: 'it.password.self_service',
          confidence: 0.93,
          release_version: 'rel-1',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    const result = await runRuntimeIntentRoute({
      runtimeEndpoint: '/v1/intent-route',
      apiSecret: ' irt_secret_live ',
      keyId: 'key_live_1',
      appId: 'checkout-web',
      serviceId: 'svc-a',
      requestId: 'admin-live-1',
      query: ' 비밀번호를 재설정하고 싶어요 ',
    });

    expect(fetchMock).toHaveBeenCalledWith('/v1/intent-route', {
      method: 'POST',
      credentials: 'omit',
      headers: {
        Authorization: 'Bearer irt_secret_live',
        'X-Key-Id': 'key_live_1',
        'X-App-Id': 'checkout-web',
        'X-Service-Id': 'svc-a',
        'X-Request-Id': 'admin-live-1',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: '비밀번호를 재설정하고 싶어요',
        channel: 'admin-ui-live-test',
        user_context: {
          workflow_run_id: 'admin-live-1',
          source: 'admin-ui-live-test',
        },
      }),
    });
    expect(result).toEqual({
      ok: true,
      status: 200,
      body: {
        trace_id: 'irt-live-1',
        decision: 'confident',
        request_id: 'admin-live-1',
        intent_id: 'password_reset',
        route_key: 'it.password.self_service',
        confidence: 0.93,
        release_version: 'rel-1',
      },
    });
  });

  it('redacts the revealed API Secret from runtime error fields before returning them', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'error irt_secret_live',
          trace_id: 'irt-live-error-irt_secret_live',
          request_id: 'admin-live-2-irt_secret_live',
          release_version: 'rel-irt_secret_live',
          error: {
            code: 'AUTHENTICATION_FAILED_irt_secret_live',
            message: 'API key authentication failed for Bearer irt_secret_live.',
            retryable: false,
            category: 'authentication_irt_secret_live',
            layer: 'api_key_irt_secret_live',
          },
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    const result = await runRuntimeIntentRoute({
      runtimeEndpoint: '/v1/intent-route',
      apiSecret: 'irt_secret_live',
      keyId: 'key_live_1',
      appId: 'checkout-web',
      serviceId: 'svc-a',
      requestId: 'admin-live-2',
      query: 'test query',
    });

    expect(result).toEqual({
      ok: false,
      status: 401,
      trace_id: 'irt-live-error-[REDACTED]',
      request_id: 'admin-live-2-[REDACTED]',
      release_version: 'rel-[REDACTED]',
      error: {
        code: 'AUTHENTICATION_FAILED_[REDACTED]',
        message: 'API key authentication failed for Bearer [REDACTED].',
        retryable: false,
        category: 'authentication_[REDACTED]',
        layer: 'api_key_[REDACTED]',
      },
    });
    expect(JSON.stringify(result)).not.toContain('irt_secret_live');
  });

  it('redacts the revealed API Secret from successful runtime fields before returning them', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          trace_id: 'irt-live-irt_secret_live',
          decision: 'confident',
          request_id: 'admin-live-4-irt_secret_live',
          domain: 'it_irt_secret_live',
          intent_id: 'password_reset_irt_secret_live',
          route_key: 'it.password.irt_secret_live',
          clarify_question: 'retry without irt_secret_live?',
          confidence: 0.88,
          release_version: 'rel-irt_secret_live',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    const result = await runRuntimeIntentRoute({
      runtimeEndpoint: '/v1/intent-route',
      apiSecret: 'irt_secret_live',
      keyId: 'key_live_1',
      appId: 'checkout-web',
      serviceId: 'svc-a',
      requestId: 'admin-live-4',
      query: 'test query',
    });

    expect(result).toEqual({
      ok: true,
      status: 200,
      body: {
        trace_id: 'irt-live-[REDACTED]',
        decision: 'confident',
        request_id: 'admin-live-4-[REDACTED]',
        domain: 'it_[REDACTED]',
        intent_id: 'password_reset_[REDACTED]',
        route_key: 'it.password.[REDACTED]',
        clarify_question: 'retry without [REDACTED]?',
        confidence: 0.88,
        release_version: 'rel-[REDACTED]',
      },
    });
    expect(JSON.stringify(result)).not.toContain('irt_secret_live');
  });

  it('redacts the revealed API Secret from a network error before returning it', async () => {
    fetchMock.mockRejectedValue(new Error('Request failed for Bearer irt_secret_live.'));

    const result = await runRuntimeIntentRoute({
      runtimeEndpoint: '/v1/intent-route',
      apiSecret: 'irt_secret_live',
      keyId: 'key_live_1',
      appId: 'checkout-web',
      serviceId: 'svc-a',
      requestId: 'admin-live-3',
      query: 'test query',
    });

    expect(result).toEqual({
      ok: false,
      status: 0,
      error: {
        code: 'NETWORK_ERROR',
        message: 'Request failed for Bearer [REDACTED].',
        retryable: true,
      },
    });
    expect(JSON.stringify(result)).not.toContain('irt_secret_live');
  });
});
