import { describe, expect, it } from 'vitest';
import {
  buildExampleFormInitialValues,
  buildIntentFormInitialValues,
} from './intentFormValues';

const intent = {
  service_id: 'svc-1',
  intent_id: 'it_password_reset',
  domain: 'it',
  display_name: 'Password reset',
  description: 'Reset passwords',
  route_key: 'it.password_reset.self_service',
  status: 'active',
  include_keywords: ['password'],
  exclude_keywords: ['billing'],
} satisfies API.Intent;

describe('intent form initial values', () => {
  it('builds create intent defaults without mutating a mounted form instance', () => {
    expect(buildIntentFormInitialValues('create')).toEqual({
      include_keywords: [],
      exclude_keywords: [],
    });
  });

  it('builds edit intent defaults from the selected row', () => {
    expect(buildIntentFormInitialValues('edit', intent)).toEqual({
      intent_id: 'it_password_reset',
      domain: 'it',
      display_name: 'Password reset',
      description: 'Reset passwords',
      route_key: 'it.password_reset.self_service',
      status: 'active',
      include_keywords: ['password'],
      exclude_keywords: ['billing'],
    });
  });

  it('builds example defaults', () => {
    expect(buildExampleFormInitialValues()).toEqual({
      example_type: 'positive',
      source: 'admin_ui',
    });
  });
});
