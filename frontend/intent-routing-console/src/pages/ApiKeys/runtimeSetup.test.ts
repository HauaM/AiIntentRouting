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

const globalStyleSource = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), '../../global.less'), 'utf8');

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
    expect(source).toContain('API Secret Key');
    expect(source).toContain('Routing Key ID');
    expect(source).not.toContain('key_id {createdKey.key_id}');
    expect(source).not.toContain('message="새 API key secret"');
  });

  it('splits API key work into new issue and existing key management tabs', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('const apiKeyTabs');
    expect(source).toContain("label: '신규 발급'");
    expect(source).toContain("label: '기존 키 관리'");
    expect(source).toContain('<Tabs');
    expect(source).not.toContain('<Card title="Manual revoke">');
    expect(source).not.toContain('revokeForm');
  });

  it('puts inventory before runtime guidance and applies the selected key to guidance', () => {
    const source = apiKeysPageSource();
    const inventoryIndex = source.indexOf('API key inventory');
    const guidanceIndex = source.indexOf('Runtime setup guidance');

    expect(inventoryIndex).toBeGreaterThan(-1);
    expect(guidanceIndex).toBeGreaterThan(-1);
    expect(inventoryIndex).toBeLessThan(guidanceIndex);
    expect(source).toContain('selectedApiKey');
    expect(source).toContain('onRow={(row) => ({');
    expect(source).toContain('selectApiKey(row)');
  });

  it('renders setup templates without a browser live test or raw secret input', () => {
    const source = apiKeysPageSource();

    expect(source).not.toContain('Dify variable mapping');
    expect(source).not.toContain('dify_variable_mapping.map');
    expect(source).not.toContain('라이브 테스트');
    expect(source).not.toContain('runRuntimeIntentRoute');
    expect(source).not.toContain('runtimeServices');
    expect(source).not.toContain('/v1/intent-route');
    expect(source).not.toContain('window.fetch');
    expect(source).not.toContain('headers: {');
    expect(source).not.toContain('api_secret');
    expect(source).not.toContain('Input.Password');
    expect(source).not.toContain('fetch(');
  });

  it('supports unlimited expiry from the create form without hiding the finite-day option', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('expiry_mode');
    expect(source).toContain("value: 'none'");
    expect(source).toContain("value: 'days'");
    expect(source).toContain('무기한');
    expect(source).toContain('expires_in_days: null');
  });

  it('uses bounded API key inventory table scroll without fake pagination', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('scroll={{');
    expect(source).toContain('pagination={false}');
  });

  it('keeps API key form controls robust when desktop width is narrowed', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('className="api-key-scope-fields"');
    expect(source).toContain('column={{ xs: 1, md: 2 }}');
    expect(source).toContain('layout="vertical"');
  });

  it('uses a release-owned environment selector and owner-only runtime setup gate', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('Released environment');
    expect(source).toContain("value: 'qa'");
    expect(source).toContain('canManageRuntimeSetup(session)');
    expect(source).not.toContain('selectedService?.environment');
    expect(source).not.toContain('service_owner/service_developer');
  });

  it('guards page data commits by service, environment, and request identity', () => {
    const source = apiKeysPageSource();

    expect(source).toContain('selectedEnvironmentRef');
    expect(source).toContain('apiKeyPageRequestIdRef');
    expect(source).toContain('const environment = selectedEnvironment');
    expect(source).toMatch(/selectedEnvironmentRef\.current\s*===\s*environment/);
    expect(source).toMatch(/apiKeyPageRequestIdRef\.current\s*===\s*requestId/);
  });

  it('wraps runtime setup checklist items inside a bounded container', () => {
    const source = apiKeysPageSource();
    const styles = globalStyleSource();

    expect(source).toContain('className="api-key-checklist"');
    expect(styles).toContain('.api-key-checklist');
    expect(styles).toContain('overflow-wrap: anywhere');
  });
});
