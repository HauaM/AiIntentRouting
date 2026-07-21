export type TableRequestParams = {
  keyword?: string;
  status?: string;
  route_key?: string;
  decision?: string;
  event_type?: string;
  trace_id?: string;
  environment?: string;
};

export type TableResult<T> = {
  data: T[];
  total: number;
  success: true;
};

export const textIncludes = (value: unknown, keyword: string) =>
  String(value ?? '').toLowerCase().includes(keyword);

export function toReadOnlyTableResult<T>(rows: T[]): TableResult<T> {
  return {
    data: rows,
    total: rows.length,
    success: true,
  };
}

export function filterIntents(rows: API.Intent[], params: TableRequestParams) {
  const keyword = params.keyword?.trim().toLowerCase();
  return rows.filter((row) => {
    const matchesStatus = !params.status || row.status === params.status;
    const matchesRoute = !params.route_key || row.route_key === params.route_key;
    const matchesKeyword =
      !keyword ||
      [row.intent_id, row.display_name, row.description, row.route_key].some((value) =>
        textIncludes(value, keyword),
      );
    return matchesStatus && matchesRoute && matchesKeyword;
  });
}

export function filterRuntimeLogs(rows: API.RuntimeLog[], params: TableRequestParams) {
  const keyword = params.keyword?.trim().toLowerCase();
  return rows.filter((row) => {
    const matchesDecision = !params.decision || row.decision === params.decision;
    const matchesTrace = !params.trace_id || row.trace_id.includes(params.trace_id);
    const matchesKeyword =
      !keyword ||
      [row.trace_id, row.query_masked, row.route_key, row.decision].some((value) =>
        textIncludes(value, keyword),
      );
    return matchesDecision && matchesTrace && matchesKeyword;
  });
}
