import { describe, expect, it } from 'vitest';
import {
  runtimeSetupBodyTemplateText,
  runtimeSetupContainsRawSecret,
  runtimeSetupHeaderRows,
  runtimeSetupSelectedKeyLabel,
} from './runtimeSetup';

const guidance: API.RuntimeSetupGuidance = {
  service_id: 'svc-a',
  environment: 'prod',
  runtime_endpoint: '/v1/intent-route',
  recommended_timeout_seconds: 8,
  active_release: {
    release_version: 'rel-1',
    policy_version: 'pol-1',
    intent_catalog_version: 'cat-1',
    test_run_id: 'tr-1',
  },
  selected_key: {
    key_id: 'key_live_1',
    key_fingerprint: 'sha256:abcd:efgh',
    app_id: 'dify-helpdesk',
    status: 'active',
    expires_at: '2026-10-07T00:00:00Z',
    allowed_intents: ['billing_refund'],
    allowed_route_keys: ['billing.refund.request'],
  },
  headers_template: {
    Authorization: 'Bearer {{intent_routing_api_key}}',
    'X-Key-Id': 'key_live_1',
    'X-App-Id': 'dify-helpdesk',
    'X-Service-Id': 'svc-a',
    'X-Request-Id': '{{workflow_run_id}}',
    'X-Admin-Token': 'must-not-render',
    'x-actor-id': 'must-not-render',
    'X-Actor-Roles': 'must-not-render',
    'x-Service-Scope': 'must-not-render',
  },
  body_template: {
    query: '{{user_query}}',
    channel: 'chat',
    user_context: { workflow_run_id: '{{workflow_run_id}}' },
  },
  dify_variable_mapping: [],
  checklist: [],
  docs: [],
  warnings: [],
};

describe('runtime setup guidance helpers', () => {
  it('filters trusted Admin headers from rendered runtime header rows', () => {
    expect(runtimeSetupHeaderRows(guidance)).toEqual([
      { name: 'Authorization', value: 'Bearer {{intent_routing_api_key}}' },
      { name: 'X-Key-Id', value: 'key_live_1' },
      { name: 'X-App-Id', value: 'dify-helpdesk' },
      { name: 'X-Service-Id', value: 'svc-a' },
      { name: 'X-Request-Id', value: '{{workflow_run_id}}' },
    ]);
  });

  it('formats body template and selected key metadata without raw secret replay', () => {
    expect(runtimeSetupSelectedKeyLabel(guidance)).toBe('key_live_1');
    expect(runtimeSetupBodyTemplateText(guidance)).toContain('"query": "{{user_query}}"');
    expect(runtimeSetupContainsRawSecret(guidance, 'irt_secret_once')).toBe(false);
  });
});
