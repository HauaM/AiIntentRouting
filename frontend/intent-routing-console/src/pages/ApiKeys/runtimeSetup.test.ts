import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  runtimeSetupBodyTemplateText,
  runtimeSetupContainsRawSecret,
  runtimeSetupHeaderRows,
  runtimeSetupSelectedKeyLabel,
} from './runtimeSetup';

const apiKeysPageSource = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');

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

  it('renders the one-time API key secret in a close-to-clear modal, not a page alert', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('<Modal');
    expect(source).toContain('open={Boolean(createdKey)}');
    expect(source).toContain('onCancel={clearCreatedKey}');
    expect(source).toContain('setCreatedKey(undefined)');
    expect(source).toContain('이 secret은 이 모달을 닫으면 다시 볼 수 없습니다.');
    expect(source).not.toContain('message="새 API key secret"');
  });

  it('uses bounded API key inventory table scroll without fake pagination', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('scroll={{');
    expect(source).toContain('pagination={false}');
  });

  it('keeps API key form controls responsive on mobile', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('className="api-key-scope-fields"');
    expect(source).toContain('column={{ xs: 1, md: 2 }}');
    expect(source).toContain("style={{ width: '100%', maxWidth: 320 }}");
    expect(source).toContain('layout="vertical"');
  });
});
