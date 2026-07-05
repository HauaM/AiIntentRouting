import { describe, expect, it } from 'vitest';
import {
  filterIntents,
  filterRuntimeLogs,
  toReadOnlyTableResult,
  type TableRequestParams,
} from './tableData';

describe('table data helpers', () => {
  it('returns array-backed read-only rows without pretending to server-page data', () => {
    const result = toReadOnlyTableResult([1, 2, 3, 4, 5]);

    expect(result).toEqual({
      data: [1, 2, 3, 4, 5],
      total: 5,
      success: true,
    });
  });

  it('filters intent rows by status, route, and keyword', () => {
    const rows = [
      {
        intent_id: 'password-reset',
        display_name: 'Password reset',
        description: 'Help employees reset passwords.',
        route_key: 'it.password.self_service',
        status: 'active',
      },
      {
        intent_id: 'vpn-access',
        display_name: 'Password reset draft',
        description: 'Help employees reset passwords.',
        route_key: 'it.password.self_service',
        status: 'draft',
      },
      {
        intent_id: 'password-wrong-route',
        display_name: 'Password reset escalated',
        description: 'Help employees reset passwords.',
        route_key: 'it.vpn.manual_lookup',
        status: 'active',
      },
      {
        intent_id: 'vpn-access',
        display_name: 'VPN access',
        description: 'Route VPN setup requests.',
        route_key: 'it.password.self_service',
        status: 'active',
      },
    ] as API.Intent[];

    expect(
      filterIntents(rows, {
        keyword: 'employees',
        route_key: 'it.password.self_service',
        status: 'active',
      }).map((row) => row.intent_id),
    ).toEqual(['password-reset']);
  });

  it('filters runtime logs by masked query, trace id, and decision only', () => {
    const rows = [
      {
        trace_id: 'trace-safe',
        query_masked: 'password reset for ***',
        decision: 'confident',
        route_key: 'it.password.self_service',
      },
      {
        trace_id: 'trace-hidden',
        query_masked: 'network issue for ***',
        decision: 'confident',
        route_key: 'it.vpn.manual_lookup',
        query: 'password reset raw text must not be searched',
      },
      {
        trace_id: 'audit-safe',
        query_masked: 'password reset for ***',
        decision: 'confident',
        route_key: 'it.password.self_service',
      },
      {
        trace_id: 'trace-fallback',
        query_masked: 'password reset for ***',
        decision: 'fallback',
        route_key: 'it.password.self_service',
      },
    ] as unknown as API.RuntimeLog[];

    const params: TableRequestParams = {
      keyword: 'password',
      decision: 'confident',
      trace_id: 'trace',
    };

    expect(filterRuntimeLogs(rows, params).map((row) => row.trace_id)).toEqual(['trace-safe']);
  });
});
