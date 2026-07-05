import { describe, expect, it } from 'vitest';

import { getDashboardViewState, getScopedRuntimeMetrics } from './dashboardViewState';

describe('getDashboardViewState', () => {
  it('keeps dashboard data panels hidden until the admin session is ready', () => {
    expect(
      getDashboardViewState({
        hasMetrics: false,
        loading: false,
        ready: false,
      }),
    ).toBe('session-required');
  });

  it('shows the initial loading state after a ready session starts fetching metrics', () => {
    expect(
      getDashboardViewState({
        hasMetrics: false,
        loading: true,
        ready: true,
      }),
    ).toBe('loading');
  });

  it('keeps dashboard data hidden when the metrics request has no result', () => {
    expect(
      getDashboardViewState({
        hasMetrics: false,
        loading: false,
        ready: true,
      }),
    ).toBe('empty');
  });

  it('shows dashboard data once metrics exist', () => {
    expect(
      getDashboardViewState({
        hasMetrics: true,
        loading: false,
        ready: true,
      }),
    ).toBe('data');
  });
});

describe('getScopedRuntimeMetrics', () => {
  const metrics = {
    service_id: 'svc-a',
    window_hours: 24,
  };

  it('returns metrics only for the active service and window', () => {
    expect(
      getScopedRuntimeMetrics({
        metrics,
        serviceId: 'svc-a',
        windowHours: 24,
      }),
    ).toBe(metrics);
  });

  it('hides stale metrics from a previous service or window', () => {
    expect(
      getScopedRuntimeMetrics({
        metrics,
        serviceId: 'svc-b',
        windowHours: 24,
      }),
    ).toBeUndefined();
    expect(
      getScopedRuntimeMetrics({
        metrics,
        serviceId: 'svc-a',
        windowHours: 168,
      }),
    ).toBeUndefined();
  });
});
