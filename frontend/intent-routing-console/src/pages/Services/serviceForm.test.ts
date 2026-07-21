import { describe, expect, it } from 'vitest';
import {
  serviceFormInitialValues,
  toServiceCreateRequest,
  type ServiceFormValues,
} from './serviceForm';

describe('service onboarding form helpers', () => {
  it('provides safe defaults for C-1 Service creation', () => {
    expect(serviceFormInitialValues).toEqual({
      max_input_tokens: 256,
    });
  });

  it('normalizes form values into the Admin API payload', () => {
    const values: ServiceFormValues = {
      service_id: '  dx-review-helpdesk  ',
      display_name: '  DX Review Helpdesk  ',
      max_input_tokens: 512,
    };

    expect(toServiceCreateRequest(values)).toEqual({
      service_id: 'dx-review-helpdesk',
      display_name: 'DX Review Helpdesk',
      max_input_tokens: 512,
    });
  });

  it('falls back to the default token limit when the input is cleared', () => {
    const values: ServiceFormValues = {
      service_id: 'svc-a',
      display_name: 'Service A',
      max_input_tokens: null,
    };

    expect(toServiceCreateRequest(values).max_input_tokens).toBe(256);
  });
});
