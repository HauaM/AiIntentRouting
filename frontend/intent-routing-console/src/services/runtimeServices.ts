export type RuntimeIntentRouteLiveTestInput = {
  runtimeEndpoint: string;
  apiSecret: string;
  keyId: string;
  appId: string;
  serviceId: string;
  requestId: string;
  query: string;
};

type RuntimeErrorEnvelope = {
  status?: 'error';
  trace_id?: string;
  request_id?: string | null;
  release_version?: string | null;
  error?: {
    code?: string;
    message?: string;
    retryable?: boolean;
    category?: string | null;
    layer?: string | null;
  };
};

export type RuntimeIntentRouteLiveTestResult =
  | {
      ok: true;
      status: number;
      body: API.RuntimeIntentRouteResponse;
    }
  | {
      ok: false;
      status: number;
      trace_id?: string;
      request_id?: string | null;
      release_version?: string | null;
      error: {
        code: string;
        message: string;
        retryable?: boolean;
        category?: string | null;
        layer?: string | null;
      };
    };

const readJsonBody = async (response: Response): Promise<Record<string, unknown>> => {
  try {
    const parsed = await response.json();
    return parsed && typeof parsed === 'object'
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
};

const redactRuntimeText = <T extends string | null | undefined>(
  value: T,
  apiSecret: string,
): T => {
  if (!value || !apiSecret) return value;
  return value.split(apiSecret).join('[REDACTED]') as T;
};

const toRuntimeErrorResult = (
  status: number,
  body: Record<string, unknown>,
  apiSecret: string,
): RuntimeIntentRouteLiveTestResult => {
  const envelope = body as RuntimeErrorEnvelope;
  return {
    ok: false,
    status,
    trace_id: redactRuntimeText(envelope.trace_id, apiSecret),
    request_id: redactRuntimeText(envelope.request_id, apiSecret),
    release_version: redactRuntimeText(envelope.release_version, apiSecret),
    error: {
      code: redactRuntimeText(envelope.error?.code, apiSecret) ?? `HTTP_${status}`,
      message:
        redactRuntimeText(envelope.error?.message, apiSecret) ?? 'Runtime call failed.',
      retryable: envelope.error?.retryable,
      category: redactRuntimeText(envelope.error?.category, apiSecret),
      layer: redactRuntimeText(envelope.error?.layer, apiSecret),
    },
  };
};

export async function runRuntimeIntentRoute({
  runtimeEndpoint,
  apiSecret,
  keyId,
  appId,
  serviceId,
  requestId,
  query,
}: RuntimeIntentRouteLiveTestInput): Promise<RuntimeIntentRouteLiveTestResult> {
  try {
    const response = await fetch(runtimeEndpoint, {
      method: 'POST',
      credentials: 'omit',
      headers: {
        Authorization: `Bearer ${apiSecret.trim()}`,
        'X-Key-Id': keyId,
        'X-App-Id': appId,
        'X-Service-Id': serviceId,
        'X-Request-Id': requestId,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query.trim(),
        channel: 'admin-ui-live-test',
        user_context: {
          workflow_run_id: requestId,
          source: 'admin-ui-live-test',
        },
      }),
    });
    const body = await readJsonBody(response);
    if (!response.ok || body.status === 'error') {
      return toRuntimeErrorResult(response.status, body, apiSecret.trim());
    }
    return {
      ok: true,
      status: response.status,
      body: body as API.RuntimeIntentRouteResponse,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      error: {
        code: 'NETWORK_ERROR',
        message: redactRuntimeText(
          error instanceof Error ? error.message : 'Runtime call failed.',
          apiSecret.trim(),
        ) ?? 'Runtime call failed.',
        retryable: true,
      },
    };
  }
}
