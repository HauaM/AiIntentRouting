export type RuntimeIntentRouteLiveTestInput = {
  runtimeEndpoint: string;
  apiSecret: string;
  keyId: string;
  appId: string;
  serviceId: string;
  requestId: string;
  query: string;
};

type RedactedJson =
  | string
  | number
  | boolean
  | null
  | RedactedJson[]
  | { [key: string]: RedactedJson };

export type RuntimeHttpExchange = {
  request: {
    method: 'POST';
    url: string;
    headers: Record<string, string>;
    body: RedactedJson;
  };
  response: {
    status: number;
    body: RedactedJson;
  };
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
      exchange: RuntimeHttpExchange;
      body: API.RuntimeIntentRouteResponse;
    }
  | {
      ok: false;
      status: number;
      exchange: RuntimeHttpExchange;
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

const redactRuntimeJson = (value: unknown, apiSecret: string): RedactedJson => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return redactRuntimeText(value, apiSecret) ?? '';
  if (typeof value === 'number' || typeof value === 'boolean') return value;
  if (Array.isArray(value)) {
    return value.map((item) => redactRuntimeJson(item, apiSecret));
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).reduce<Record<string, RedactedJson>>(
      (acc, [key, item]) => {
        acc[key] = redactRuntimeJson(item, apiSecret);
        return acc;
      },
      {},
    );
  }
  return String(value);
};

const runtimeRequestBody = (query: string, requestId: string): RedactedJson => ({
  query: query.trim(),
  channel: 'admin-ui-live-test',
  user_context: {
    workflow_run_id: requestId,
    source: 'admin-ui-live-test',
  },
});

const runtimeRequestHeaders = ({
  apiSecret,
  keyId,
  appId,
  serviceId,
  requestId,
  redact,
}: {
  apiSecret: string;
  keyId: string;
  appId: string;
  serviceId: string;
  requestId: string;
  redact: boolean;
}) => ({
  Authorization: redact ? 'Bearer [REDACTED]' : `Bearer ${apiSecret}`,
  'X-Key-Id': keyId,
  'X-App-Id': appId,
  'X-Service-Id': serviceId,
  'X-Request-Id': requestId,
  'Content-Type': 'application/json',
});

const runtimeExchange = ({
  runtimeEndpoint,
  apiSecret,
  keyId,
  appId,
  serviceId,
  requestId,
  requestBody,
  responseStatus,
  responseBody,
}: {
  runtimeEndpoint: string;
  apiSecret: string;
  keyId: string;
  appId: string;
  serviceId: string;
  requestId: string;
  requestBody: RedactedJson;
  responseStatus: number;
  responseBody: unknown;
}): RuntimeHttpExchange => ({
  request: {
    method: 'POST',
    url: runtimeEndpoint,
    headers: runtimeRequestHeaders({
      apiSecret,
      keyId,
      appId,
      serviceId,
      requestId,
      redact: true,
    }),
    body: redactRuntimeJson(requestBody, apiSecret),
  },
  response: {
    status: responseStatus,
    body: redactRuntimeJson(responseBody, apiSecret),
  },
});

const toRuntimeErrorResult = (
  status: number,
  body: Record<string, unknown>,
  apiSecret: string,
  exchange: RuntimeHttpExchange,
): RuntimeIntentRouteLiveTestResult => {
  const envelope = body as RuntimeErrorEnvelope;
  return {
    ok: false,
    status,
    exchange,
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

const toRuntimeSuccessResult = (
  status: number,
  body: Record<string, unknown>,
  apiSecret: string,
  exchange: RuntimeHttpExchange,
): RuntimeIntentRouteLiveTestResult => {
  const envelope = body as Partial<API.RuntimeIntentRouteResponse>;
  return {
    ok: true,
    status,
    exchange,
    body: {
      trace_id: redactRuntimeText(envelope.trace_id, apiSecret) ?? '',
      decision: envelope.decision ?? 'fallback',
      request_id: redactRuntimeText(envelope.request_id, apiSecret),
      domain: redactRuntimeText(envelope.domain, apiSecret),
      intent_id: redactRuntimeText(envelope.intent_id, apiSecret),
      confidence: envelope.confidence,
      route_key: redactRuntimeText(envelope.route_key, apiSecret),
      clarify_question: redactRuntimeText(envelope.clarify_question, apiSecret),
      release_version: redactRuntimeText(envelope.release_version, apiSecret),
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
  const secret = apiSecret.trim();
  const requestBody = runtimeRequestBody(query, requestId);
  try {
    const response = await fetch(runtimeEndpoint, {
      method: 'POST',
      credentials: 'omit',
      headers: runtimeRequestHeaders({
        apiSecret: secret,
        keyId,
        appId,
        serviceId,
        requestId,
        redact: false,
      }),
      body: JSON.stringify(requestBody),
    });
    const body = await readJsonBody(response);
    const exchange = runtimeExchange({
      runtimeEndpoint,
      apiSecret: secret,
      keyId,
      appId,
      serviceId,
      requestId,
      requestBody,
      responseStatus: response.status,
      responseBody: body,
    });
    if (!response.ok || body.status === 'error') {
      return toRuntimeErrorResult(response.status, body, secret, exchange);
    }
    return toRuntimeSuccessResult(response.status, body, secret, exchange);
  } catch (error) {
    const errorBody = {
      error: {
        code: 'NETWORK_ERROR',
        message:
          redactRuntimeText(
            error instanceof Error ? error.message : 'Runtime call failed.',
            secret,
          ) ?? 'Runtime call failed.',
        retryable: true,
      },
    };
    return {
      ok: false,
      status: 0,
      exchange: runtimeExchange({
        runtimeEndpoint,
        apiSecret: secret,
        keyId,
        appId,
        serviceId,
        requestId,
        requestBody,
        responseStatus: 0,
        responseBody: errorBody,
      }),
      error: {
        code: 'NETWORK_ERROR',
        message: errorBody.error.message,
        retryable: true,
      },
    };
  }
}
