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

  type ServiceRole = 'service_owner' | 'service_developer' | 'service_operator' | 'auditor';

  type AdminUserLookup = {
    user_id: string;
    email: string;
    display_name: string;
    status: string;
  };

  type ManagedAdminUserStatus = 'active' | 'disabled';
  type GlobalAdminRole = 'system_admin';

  type ManagedAdminUser = {
    user_id: string;
    email: string;
    display_name: string;
    status: ManagedAdminUserStatus;
    organization_user_id: string | null;
    global_roles: GlobalAdminRole[];
    is_last_active_system_admin: boolean;
    created_at: string;
    updated_at: string;
    last_login_at: string | null;
  };

  type ManagedAdminUserCreateRequest = {
    user_id?: string;
    organization_user_id: string;
    email: string;
    display_name: string;
    status?: ManagedAdminUserStatus;
    global_roles?: GlobalAdminRole[];
  };

  type ManagedAdminUserPatchRequest = {
    email?: string;
    display_name?: string;
    status?: ManagedAdminUserStatus;
    global_roles?: GlobalAdminRole[];
  };

  type ServiceMemberRole = {
    role: ServiceRole;
    assigned_by: string;
    assigned_at: string;
  };

  type ServiceMember = {
    service_id: string;
    user: AdminUserLookup;
    roles: ServiceMemberRole[];
  };

  type ServiceRoleGrantRequest = {
    role: ServiceRole;
  };

  type ServiceRoleGrantResponse = {
    service_id: string;
    user_id: string;
    role: ServiceRole;
    assigned_by: string;
    assigned_at: string;
  };

  type ServiceRoleRevokeResponse = {
    service_id: string;
    user_id: string;
    role: ServiceRole;
    revoked_by: string;
    revoked_at: string;
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

  type ServiceCreateRequest = {
    service_id: string;
    display_name: string;
    environment: string;
    default_threshold_preset: ThresholdPreset;
    max_input_tokens: number;
  };

  type Service = {
    service_id: string;
    display_name: string;
    environment: string;
    default_threshold_preset: string;
    max_input_tokens: number;
    status: string;
    created_by: string;
    created_at: string;
    updated_at: string;
  };

  type IntentStatus = 'active' | 'draft' | 'deprecated';
  type RuntimeDecision = 'confident' | 'clarify' | 'fallback' | 'off_topic' | 'risk';
  type ApiKeyStatus = 'active' | 'revoked' | 'expired';
  type UseYn = 'Y' | 'N';

  type Department = {
    id: string;
    dept_number: string;
    name: string;
    use_yn: UseYn;
    created_by: string;
    updated_by: string;
    created_at: string;
    updated_at: string;
  };

  type DepartmentCreateRequest = {
    dept_number: string;
    name: string;
  };

  type DepartmentPatchRequest = Partial<DepartmentCreateRequest> & {
    use_yn?: UseYn;
  };

  type OrganizationUser = {
    id: string;
    user_number: string;
    name: string;
    department_id: string;
    department: Department;
    use_yn: UseYn;
    created_by: string;
    updated_by: string;
    created_at: string;
    updated_at: string;
  };

  type OrganizationUserCreateRequest = {
    user_number: string;
    name: string;
    department_id: string;
  };

  type OrganizationUserPatchRequest = Partial<OrganizationUserCreateRequest> & {
    use_yn?: UseYn;
  };

  type Intent = {
    id?: string;
    service_id: string;
    intent_id: string;
    domain: string;
    display_name: string;
    description: string;
    route_key: string;
    status: IntentStatus;
    include_keywords: string[];
    exclude_keywords: string[];
    created_by?: string;
    updated_by?: string;
    created_at?: string;
    updated_at?: string;
  };

  type ThresholdPreset = 'strict' | 'balanced' | 'exploratory';

  type IntentCreateRequest = {
    intent_id: string;
    domain: string;
    display_name: string;
    description: string;
    route_key: string;
    include_keywords?: string[];
    exclude_keywords?: string[];
  };

  type IntentPatchRequest = {
    domain?: string;
    display_name?: string;
    description?: string;
    route_key?: string;
    status?: IntentStatus;
    include_keywords?: string[];
    exclude_keywords?: string[];
  };

  type ExampleCreateRequest = {
    example_type: 'positive' | 'negative';
    text_raw: string;
    source: string;
    test_case_id?: string | null;
  };

  type Example = {
    example_id: string;
    service_id: string;
    intent_id: string;
    example_type: string;
    text_masked: string;
    embedding: number[] | null;
    source: string;
    test_case_id: string | null;
    approved: boolean;
    created_by: string;
    created_at: string;
  };

  type PolicyToggle = {
    enabled: boolean;
  };

  type FallbackPolicy = {
    type: string;
    retryable?: boolean | null;
    recommended_action?: string | null;
    message?: string | null;
  };

  type OffTopicPolicySettings = {
    enabled: boolean;
    keywords: string[];
    message: string;
    fallback_policy?: FallbackPolicy | null;
  };

  type PolicyVersionCreateRequest = {
    threshold_preset: ThresholdPreset;
    clarify_margin: number;
    min_candidate_score: number;
    fallback_score: number;
    risk_policy?: PolicyToggle;
    off_topic_policy?: OffTopicPolicySettings;
  };

  type PolicyVersion = {
    policy_version: string;
    service_id: string;
    threshold_preset: string;
    threshold_value: number;
    clarify_margin: number;
    min_candidate_score: number;
    fallback_score: number;
    risk_policy: PolicyToggle;
    off_topic_policy: OffTopicPolicySettings;
    created_by: string;
    created_at: string;
  };

  type CatalogVersion = {
    intent_catalog_version: string;
    service_id: string;
    snapshot: Record<string, unknown>;
    created_by: string;
    created_at: string;
  };

  type CatalogVersionListItem = {
    intent_catalog_version: string;
    service_id: string;
    intent_count: number;
    approved_example_count: number;
    created_by: string;
    created_at: string;
  };

  type TestRunCreateRequest = {
    policy_version: string;
    intent_catalog_version: string;
    threshold_preset: ThresholdPreset;
    source_filename: string;
    csv_text: string;
  };

  type TestRunSummary = {
    test_run_id: string;
    test_dataset_version: string;
    threshold_preset: string;
    threshold_value: number;
    pass_rate: number;
    review_rate: number;
    risk_pass_rate: number;
    gate_passed: boolean;
    block_reasons: string[];
    recommendations: string[];
  };

  type TestRunListItem = TestRunSummary & {
    service_id: string;
    source_filename: string;
    policy_version: string;
    intent_catalog_version: string;
    created_by: string;
    created_at: string;
  };

  type TestRunResult = {
    case_id: string;
    query_masked: string;
    case_type: string;
    expected_decision: string;
    expected_intent: string | null;
    actual_decision: string;
    actual_intent: string | null;
    actual_route_key: string | null;
    confidence: number | null;
    result: string;
    reason: string;
  };

  type ReleaseCreateRequest = {
    environment: string;
    policy_version: string;
    intent_catalog_version: string;
    test_run_id: string;
    rollback_target?: string | null;
  };

  type Release = {
    release_version: string;
    service_id: string;
    environment: string;
    policy_version: string;
    intent_catalog_version: string;
    model_version: string;
    vector_index_version: string;
    test_dataset_version: string;
    test_run_id: string;
    pass_rate: number;
    risk_pass_rate: number;
    active: boolean;
    released_by: string;
    released_at: string;
    rollback_target: string | null;
  };

  type ReleaseCandidate = {
    test_run_id: string;
    service_id: string;
    environment: string;
    policy_version: string;
    intent_catalog_version: string;
    test_dataset_version: string;
    source_filename: string;
    threshold_preset: string;
    pass_rate: number;
    risk_pass_rate: number;
    gate_passed: boolean;
    eligible: boolean;
    block_reasons: string[];
    already_released: boolean;
    existing_release_version: string | null;
    created_at: string;
  };

  type IntentRouteCandidate = {
    intent_id: string;
    display_name: string;
    route_key: string;
    status: IntentStatus;
    source: 'current_catalog' | 'active_release';
  };

  type ApiKeyCreateRequest = {
    service_id: string;
    environment: string;
    app_id: string;
    allowed_intents?: string[];
    allowed_route_keys?: string[];
    expires_in_days: number;
  };

  type ServiceApiKeyCreateRequest = Omit<ApiKeyCreateRequest, 'service_id'>;

  type ApiKey = {
    key_id: string;
    key_fingerprint: string;
    environment: string;
    app_id: string;
    service_id: string;
    allowed_intents: string[];
    allowed_route_keys: string[];
    status: ApiKeyStatus;
    expires_at: string;
    revoked_at: string | null;
    created_by: string;
    created_at: string;
  };

  type ApiKeyCreateResponse = {
    key_id: string;
    api_key: string;
    api_key_displayed_once: boolean;
    key_fingerprint: string;
    environment: string;
    app_id: string;
    service_id: string;
    allowed_intents: string[];
    allowed_route_keys: string[];
    status: ApiKeyStatus;
    expires_at: string;
    revoked_at: string | null;
    created_by: string;
    created_at: string;
  };

  type RuntimeSetupActiveRelease = {
    release_version: string;
    policy_version: string;
    intent_catalog_version: string;
    test_run_id: string;
  };

  type RuntimeSetupSelectedKey = {
    key_id: string;
    key_fingerprint: string;
    app_id: string;
    status: ApiKeyStatus;
    expires_at: string;
    allowed_intents: string[];
    allowed_route_keys: string[];
  };

  type RuntimeSetupVariableMapping = {
    field: string;
    source: string;
  };

  type RuntimeSetupGuidance = {
    service_id: string;
    environment: string;
    runtime_endpoint: string;
    recommended_timeout_seconds: number;
    active_release: RuntimeSetupActiveRelease | null;
    selected_key: RuntimeSetupSelectedKey | null;
    headers_template: Record<string, string>;
    body_template: Record<string, unknown>;
    dify_variable_mapping: RuntimeSetupVariableMapping[];
    checklist: string[];
    docs: string[];
    warnings: string[];
  };

  type RuntimeLog = {
    trace_id: string;
    request_id: string | null;
    app_id: string | null;
    service_id: string | null;
    release_version: string | null;
    policy_version: string | null;
    intent_catalog_version: string | null;
    decision: RuntimeDecision | null;
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
