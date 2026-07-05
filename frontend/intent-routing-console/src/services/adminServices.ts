import { request } from '@umijs/max';
import {
  filterIntents,
  filterRuntimeLogs,
  toReadOnlyTableResult,
  type TableRequestParams,
} from './tableData';

const RECENT_RUNTIME_LOG_LIMIT = 100;
const RECENT_AUDIT_LOG_LIMIT = 100;

const servicePath = (serviceId: string, suffix: string) =>
  `/services/${encodeURIComponent(serviceId)}${suffix}`;

export async function fetchRuntimeMetrics(serviceId: string, windowHours: number) {
  return request<API.RuntimeMetrics>(servicePath(serviceId, '/runtime-metrics'), {
    method: 'GET',
    params: { window_hours: windowHours },
  });
}

export async function listIntents(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.Intent[]>(servicePath(serviceId, '/intents'), {
    method: 'GET',
  });
  return toReadOnlyTableResult(filterIntents(rows, params));
}

export async function listRuntimeLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.RuntimeLog[]>(servicePath(serviceId, '/runtime-logs'), {
    method: 'GET',
    params: { limit: RECENT_RUNTIME_LOG_LIMIT },
  });
  return toReadOnlyTableResult(filterRuntimeLogs(rows, params));
}

export async function fetchRuntimeLog(serviceId: string, traceId: string) {
  return request<API.RuntimeLog>(
    servicePath(serviceId, `/runtime-logs/${encodeURIComponent(traceId)}`),
    { method: 'GET' },
  );
}

export async function listAuditLogs(serviceId: string, params: TableRequestParams) {
  const rows = await request<API.AuditLog[]>(servicePath(serviceId, '/audit-logs'), {
    method: 'GET',
    params: {
      limit: RECENT_AUDIT_LOG_LIMIT,
      event_type: params.event_type || undefined,
      trace_id: params.trace_id || undefined,
    },
  });
  return toReadOnlyTableResult(rows);
}
