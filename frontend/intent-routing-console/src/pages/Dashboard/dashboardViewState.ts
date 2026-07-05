export type DashboardViewState = 'session-required' | 'loading' | 'empty' | 'data';

type DashboardViewStateInput = {
  hasMetrics: boolean;
  loading: boolean;
  ready: boolean;
};

type RuntimeMetricsScopeInput<TMetrics extends Pick<API.RuntimeMetrics, 'service_id' | 'window_hours'>> = {
  metrics: TMetrics | undefined;
  serviceId: string;
  windowHours: number;
};

export function getScopedRuntimeMetrics<
  TMetrics extends Pick<API.RuntimeMetrics, 'service_id' | 'window_hours'>,
>({ metrics, serviceId, windowHours }: RuntimeMetricsScopeInput<TMetrics>) {
  if (!metrics) return undefined;
  if (metrics.service_id !== serviceId) return undefined;
  if (metrics.window_hours !== windowHours) return undefined;
  return metrics;
}

export function getDashboardViewState({
  hasMetrics,
  loading,
  ready,
}: DashboardViewStateInput): DashboardViewState {
  if (!ready) return 'session-required';
  if (loading && !hasMetrics) return 'loading';
  if (!hasMetrics) return 'empty';
  return 'data';
}
