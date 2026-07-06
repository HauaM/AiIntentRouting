declare namespace API {
  type AdminUser = {
    user_id: string;
    email: string;
    display_name: string;
    status: string;
    created_at: string;
    updated_at: string;
    last_login_at: string | null;
  };

  type AdminServiceRole = {
    service_id: string;
    role: string;
  };

  type AdminCurrentUserResponse = {
    user: AdminUser;
    global_roles: string[];
    service_roles: AdminServiceRole[];
  };

  type AdminLoginRequest = {
    email: string;
    password: string;
  };

  type AdminLogoutResponse = {
    success: boolean;
  };

  type AccessibleService = {
    service_id: string;
    display_name: string;
    environment: string;
    status: string;
    roles: string[];
  };

  type Intent = {
    id?: string;
    service_id: string;
    intent_id: string;
    domain: string;
    display_name: string;
    description: string;
    route_key: string;
    status: 'active' | 'draft' | 'deprecated' | string;
    include_keywords: string[];
    exclude_keywords: string[];
    created_by?: string;
    updated_by?: string;
    created_at?: string;
    updated_at?: string;
  };

  type RuntimeLog = {
    trace_id: string;
    request_id: string | null;
    app_id: string | null;
    service_id: string | null;
    release_version: string | null;
    policy_version: string | null;
    intent_catalog_version: string | null;
    decision: 'confident' | 'clarify' | 'fallback' | 'off_topic' | 'risk' | string | null;
    intent_id: string | null;
    confidence: number | null;
    margin: number | null;
    threshold_preset: string | null;
    threshold_value: number | null;
    route_key: string | null;
    error_code: string | null;
    error_category: string | null;
    error_layer: string | null;
    http_status: number | null;
    retryable: boolean | null;
    latency_ms: number;
    query_masked: string | null;
    created_at: string;
  };

  type LatencyMetrics = {
    p50: number | null;
    p95: number | null;
    max: number | null;
  };

  type RawQueryRetentionMetrics = {
    encrypted_count: number;
    incomplete_count: number;
    redacted_count: number;
  };

  type TopRouteKey = {
    route_key: string;
    count: number;
  };

  type RuntimeMetrics = {
    service_id: string;
    window_hours: number;
    request_count: number;
    decision_counts: Record<string, number>;
    error_counts: Record<string, number>;
    latency_ms: LatencyMetrics;
    top_route_keys: TopRouteKey[];
    raw_query_retention: RawQueryRetentionMetrics;
  };

  type AuditLog = {
    audit_id: string;
    event_type: string;
    actor_id: string;
    service_id: string;
    trace_id: string | null;
    target_type: string;
    target_id: string;
    view_reason: string | null;
    source_ip: string | null;
    created_at: string;
  };
}
