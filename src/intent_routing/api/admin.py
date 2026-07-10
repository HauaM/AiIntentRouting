from __future__ import annotations

import csv
import hashlib
import json
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO
from os import environ
from typing import Annotated, Any, Literal, NoReturn
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from intent_routing.api.admin_dependencies import (
    admin_context_from_session_record,
    get_admin_session,
    require_admin_context,
    require_admin_session_context,
)
from intent_routing.config import DEFAULT_RAW_TEXT_KEK_ID, MissingRawTextKekError
from intent_routing.db.models import (
    AdminUser,
    ApiKey,
    GovernedActionRequest,
    Intent,
    IntentCatalogVersion,
    IntentExample,
    PolicyVersion,
    Release,
    Service,
    TestDataset,
    TestResult,
    TestRun,
    UserServiceRole,
)
from intent_routing.db.repositories import (
    MASKED_RUNTIME_LOG_FIELD_NAMES,
    AdminSessionContextRecord,
    IntentRoutingRepository,
)
from intent_routing.domain.enums import (
    ApiKeyStatus,
    ErrorCode,
    ExampleType,
    IntentStatus,
    ThresholdPreset,
)
from intent_routing.domain.schemas import (
    ErrorEnvelope,
    ErrorInfo,
    FallbackPolicy,
    validate_route_key,
)
from intent_routing.embedding.provider import get_embedding_provider
from intent_routing.logging.audit import (
    decrypt_runtime_raw_query,
    raw_query_view_after_state,
    runtime_log_encrypted_raw_query,
    source_ip_from_request,
)
from intent_routing.ops.metrics import (
    raw_text_key_summary_from_counts,
    safe_audit_log_item,
)
from intent_routing.security.admin_auth import (
    AdminContext,
    raise_admin_forbidden,
)
from intent_routing.security.api_keys import (
    fingerprint_secret,
    generate_api_key_secret,
    hash_secret,
)
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring, load_raw_text_keyring
from intent_routing.security.pii import mask_pii
from intent_routing.testing.csv_runner import (
    CsvTestRunSummary,
    CsvValidationError,
    run_csv_tests,
    summarize_test_run,
)
from intent_routing.versions import releases as release_service

router = APIRouter(prefix="/admin/v1", tags=["admin"])

__all__ = ("get_admin_session", "router")


class ServiceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    default_threshold_preset: ThresholdPreset = ThresholdPreset.balanced
    max_input_tokens: int = Field(default=256, ge=1)


class ServiceResponse(BaseModel):
    service_id: str
    display_name: str
    environment: str
    default_threshold_preset: str
    max_input_tokens: int
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class AccessibleServiceResponse(BaseModel):
    service_id: str
    display_name: str
    environment: str
    status: str
    roles: list[str]


class AdminUserLookupResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    status: str


class ServiceMemberRoleResponse(BaseModel):
    role: str
    assigned_by: str
    assigned_at: datetime


class ServiceMemberResponse(BaseModel):
    service_id: str
    user: AdminUserLookupResponse
    roles: list[ServiceMemberRoleResponse]


ServiceAdminRole = Literal[
    "service_owner",
    "service_developer",
    "service_operator",
    "auditor",
]


class ServiceRoleGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ServiceAdminRole

    @field_validator("role", mode="before")
    @classmethod
    def role_must_be_stripped(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ServiceRoleGrantResponse(BaseModel):
    service_id: str
    user_id: str
    role: str
    assigned_by: str
    assigned_at: datetime


class ServiceRoleRevokeResponse(BaseModel):
    service_id: str
    user_id: str
    role: str
    revoked_by: str
    revoked_at: datetime


class ApiKeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    app_id: str = Field(min_length=1)
    allowed_intents: list[str] = Field(default_factory=list)
    allowed_route_keys: list[str] = Field(default_factory=list)
    expires_in_days: int = Field(ge=1)


class ServiceApiKeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: str = Field(min_length=1)
    app_id: str = Field(min_length=1)
    allowed_intents: list[str] = Field(default_factory=list)
    allowed_route_keys: list[str] = Field(default_factory=list)
    expires_in_days: int = Field(ge=1)


class ApiKeyCreateResponse(BaseModel):
    key_id: str
    api_key: str
    api_key_displayed_once: bool
    key_fingerprint: str
    environment: str
    app_id: str
    service_id: str
    allowed_intents: list[str]
    allowed_route_keys: list[str]
    status: str
    expires_at: datetime
    revoked_at: datetime | None
    created_by: str
    created_at: datetime


class ApiKeyResponse(BaseModel):
    key_id: str
    key_fingerprint: str
    environment: str
    app_id: str
    service_id: str
    allowed_intents: list[str]
    allowed_route_keys: list[str]
    status: str
    expires_at: datetime
    revoked_at: datetime | None
    created_by: str
    created_at: datetime


class RuntimeSetupActiveReleaseResponse(BaseModel):
    release_version: str
    policy_version: str
    intent_catalog_version: str
    test_run_id: str


class RuntimeSetupSelectedKeyResponse(BaseModel):
    key_id: str
    key_fingerprint: str
    app_id: str
    status: str
    expires_at: datetime
    allowed_intents: list[str]
    allowed_route_keys: list[str]


class RuntimeSetupVariableMappingResponse(BaseModel):
    field: str
    source: str


class RuntimeSetupResponse(BaseModel):
    service_id: str
    environment: str
    runtime_endpoint: str
    recommended_timeout_seconds: int
    active_release: RuntimeSetupActiveReleaseResponse | None
    selected_key: RuntimeSetupSelectedKeyResponse | None = None
    headers_template: dict[str, str]
    body_template: dict[str, object]
    dify_variable_mapping: list[RuntimeSetupVariableMappingResponse]
    checklist: list[str]
    docs: list[str]
    warnings: list[str]


class IntentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    route_key: str
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)

    @field_validator("route_key")
    @classmethod
    def route_key_must_be_valid(cls, value: str) -> str:
        return validate_route_key(value)


class IntentPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str | None = Field(default=None, min_length=1)
    display_name: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    route_key: str | None = None
    status: IntentStatus | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None

    @field_validator(
        "domain",
        "display_name",
        "description",
        "route_key",
        "status",
        "include_keywords",
        "exclude_keywords",
        mode="before",
    )
    @classmethod
    def patch_fields_must_not_be_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("intent patch fields must not be null")
        return value

    @field_validator("route_key")
    @classmethod
    def route_key_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_route_key(value)


class IntentResponse(BaseModel):
    id: UUID
    service_id: str
    intent_id: str
    domain: str
    display_name: str
    description: str
    route_key: str
    status: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class ExampleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    example_type: ExampleType
    text_raw: str = Field(min_length=1)
    source: str = Field(min_length=1)
    test_case_id: str | None = None


class ExampleResponse(BaseModel):
    example_id: UUID
    service_id: str
    intent_id: str
    example_type: str
    text_masked: str
    embedding: list[float] | None
    source: str
    test_case_id: str | None
    approved: bool
    created_by: str
    created_at: datetime


class PolicyToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


class OffTopicPolicySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    keywords: list[str] = Field(default_factory=list)
    message: str = ""
    fallback_policy: FallbackPolicy | None = None

    @field_validator("keywords")
    @classmethod
    def keywords_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for keyword in value:
            if not keyword.strip():
                raise ValueError("off-topic keywords must not be blank")
        return value


class PolicyVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold_preset: ThresholdPreset
    clarify_margin: float = Field(ge=0.0, le=1.0)
    min_candidate_score: float = Field(ge=0.0, le=1.0)
    fallback_score: float = Field(ge=0.0, le=1.0)
    risk_policy: PolicyToggle = Field(default_factory=PolicyToggle)
    off_topic_policy: OffTopicPolicySettings = Field(
        default_factory=OffTopicPolicySettings
    )


class PolicyVersionResponse(BaseModel):
    policy_version: str
    service_id: str
    threshold_preset: str
    threshold_value: float
    clarify_margin: float
    min_candidate_score: float
    fallback_score: float
    risk_policy: PolicyToggle
    off_topic_policy: OffTopicPolicySettings
    created_by: str
    created_at: datetime


class CatalogVersionResponse(BaseModel):
    intent_catalog_version: str
    service_id: str
    snapshot: dict[str, Any]
    created_by: str
    created_at: datetime


class CatalogVersionListItemResponse(BaseModel):
    intent_catalog_version: str
    service_id: str
    intent_count: int
    approved_example_count: int
    created_by: str
    created_at: datetime


class TestRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(min_length=1)
    intent_catalog_version: str = Field(min_length=1)
    threshold_preset: ThresholdPreset
    source_filename: str = Field(min_length=1)
    csv_text: str = Field(min_length=1)


class TestRunSummaryResponse(BaseModel):
    test_run_id: str
    test_dataset_version: str
    threshold_preset: str
    threshold_value: float
    pass_rate: float
    review_rate: float
    risk_pass_rate: float
    gate_passed: bool
    block_reasons: list[str]
    recommendations: list[str]


class TestRunListItemResponse(BaseModel):
    test_run_id: str
    service_id: str
    test_dataset_version: str
    source_filename: str
    policy_version: str
    intent_catalog_version: str
    threshold_preset: str
    threshold_value: float
    pass_rate: float
    review_rate: float
    risk_pass_rate: float
    gate_passed: bool
    block_reasons: list[str]
    recommendations: list[str]
    created_by: str
    created_at: datetime


class TestRunResultResponse(BaseModel):
    case_id: str
    query_masked: str
    case_type: str
    expected_decision: str
    expected_intent: str | None
    actual_decision: str
    actual_intent: str | None
    actual_route_key: str | None
    confidence: float | None
    result: str
    reason: str


class ReleaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    intent_catalog_version: str = Field(min_length=1)
    test_run_id: str = Field(min_length=1)
    rollback_target: str | None = None

    @field_validator("environment", mode="before")
    @classmethod
    def environment_must_not_be_blank(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("release environment must not be blank")
            return stripped
        return value


class ReleaseResponse(BaseModel):
    release_version: str
    service_id: str
    environment: str
    policy_version: str
    intent_catalog_version: str
    model_version: str
    vector_index_version: str
    test_dataset_version: str
    test_run_id: str
    pass_rate: float
    risk_pass_rate: float
    active: bool
    released_by: str
    released_at: datetime
    rollback_target: str | None


class ReleaseDiffResponse(BaseModel):
    service_id: str
    release_version: str
    compare_to: str | None
    policy_version_diff: dict[str, object]
    catalog_version_diff: dict[str, object]
    model_version_diff: dict[str, object]
    test_run_diff: dict[str, object]
    rollback_target: str | None


class PublishRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: Literal["intent", "example", "release"]
    resource_id: str = Field(min_length=1)
    action: Literal["request", "activate", "rollback"]
    target_version: str | None = Field(default=None, min_length=1)
    reason: str = Field(min_length=10)

    @field_validator("resource_id", "reason")
    @classmethod
    def publish_request_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("publish request text must not be blank")
        return stripped

    @field_validator("target_version")
    @classmethod
    def target_version_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("target_version must not be blank")
        return stripped


class PublishRequestDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, min_length=1)

    @field_validator("reason")
    @classmethod
    def decision_reason_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class PublishRequestResponse(BaseModel):
    request_id: str
    service_id: str
    resource_type: str
    resource_id: str
    action: str
    status: str
    requested_by: str
    requested_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    reason: str
    decision_reason: str | None = None


class ReleaseCandidateResponse(BaseModel):
    test_run_id: str
    service_id: str
    environment: str
    policy_version: str
    intent_catalog_version: str
    test_dataset_version: str
    source_filename: str
    threshold_preset: str
    pass_rate: float
    risk_pass_rate: float
    gate_passed: bool
    eligible: bool
    block_reasons: list[str]
    already_released: bool
    existing_release_version: str | None
    created_at: datetime


class ExportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: Literal["intent", "example", "release", "runtime_log", "export"]
    format: Literal["csv", "jsonl"]
    filters: dict[str, object] = Field(default_factory=dict)
    reason: str = Field(min_length=10)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("reason must be at least 10 characters")
        return stripped


class ExportResponse(BaseModel):
    export_id: str
    service_id: str
    resource_type: str
    status: Literal["completed", "rejected"]
    format: str
    content: str | None = None
    rejection_reason: str | None = None
    requested_by: str
    requested_at: datetime


class IntentRouteCandidateResponse(BaseModel):
    intent_id: str
    display_name: str
    route_key: str
    status: str
    source: str


class RuntimeLogResponse(BaseModel):
    trace_id: str
    request_id: str | None
    app_id: str | None
    service_id: str | None
    release_version: str | None
    policy_version: str | None
    intent_catalog_version: str | None
    decision: str | None
    intent_id: str | None
    confidence: float | None
    margin: float | None
    threshold_preset: str | None
    threshold_value: float | None
    route_key: str | None
    error_code: str | None
    error_category: str | None
    error_layer: str | None
    http_status: int | None
    retryable: bool | None
    latency_ms: int
    query_masked: str | None
    created_at: datetime


class LatencyMetricsResponse(BaseModel):
    p50: int | None
    p95: int | None
    max: int | None


class RawQueryRetentionMetricsResponse(BaseModel):
    encrypted_count: int
    incomplete_count: int
    redacted_count: int


class TopRouteKeyResponse(BaseModel):
    route_key: str
    count: int


class RuntimeMetricsResponse(BaseModel):
    service_id: str
    window_hours: int
    request_count: int
    decision_counts: dict[str, int]
    error_counts: dict[str, int]
    latency_ms: LatencyMetricsResponse
    top_route_keys: list[TopRouteKeyResponse]
    raw_query_retention: RawQueryRetentionMetricsResponse


class AuditLogResponse(BaseModel):
    audit_id: UUID
    event_type: str
    actor_id: str
    service_id: str
    trace_id: str | None
    target_type: str
    target_id: str
    view_reason: str | None
    source_ip: str | None
    created_at: datetime


class RawTextStoredKeyCountResponse(BaseModel):
    key_id: str
    count: int


class RawTextRedactedCountResponse(BaseModel):
    key_id: None
    count: int
    state: Literal["raw_query_redacted"]


class RawTextIncompleteCountResponse(BaseModel):
    key_id: None
    count: int
    state: Literal["raw_query_incomplete"]


class RawTextKeySummaryResponse(BaseModel):
    service_id: str
    active_key_id: str | None
    intent_examples: list[RawTextStoredKeyCountResponse]
    runtime_logs: list[
        RawTextStoredKeyCountResponse
        | RawTextRedactedCountResponse
        | RawTextIncompleteCountResponse
    ]


class RawQueryDecryptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_reason: str = Field(min_length=10)
    raw_query_view_token: str | None = Field(default=None, min_length=1)

    @field_validator("view_reason")
    @classmethod
    def view_reason_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("view_reason must be at least 10 characters")
        return stripped

    @field_validator("raw_query_view_token")
    @classmethod
    def raw_query_view_token_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("raw_query_view_token must not be blank")
        return stripped


class RawQueryDecryptResponse(BaseModel):
    trace_id: str
    service_id: str
    query_raw: str
    viewed_by: str
    viewed_at: datetime


class RawQueryViewRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=10)
    ticket_ref: str | None = Field(default=None, min_length=1)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("reason must be at least 10 characters")
        return stripped

    @field_validator("ticket_ref")
    @classmethod
    def ticket_ref_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("ticket_ref must not be blank")
        return stripped


class RawQueryViewRequestDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, min_length=1)

    @field_validator("reason")
    @classmethod
    def decision_reason_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class RawQueryViewTokenIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ttl_seconds: int = Field(default=300, ge=1, le=900)


class RawQueryViewRequestResponse(BaseModel):
    request_id: str
    service_id: str
    trace_id: str
    resource_type: Literal["raw_query"]
    action: Literal["decrypt"]
    status: str
    requested_by: str
    requested_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    reason: str
    decision_reason: str | None = None


class RawQueryTokenResponse(BaseModel):
    request_id: str
    token: str
    expires_at: datetime


def _trace_id() -> str:
    return f"irt-{uuid4().hex}"


def _raise_not_found(message: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INVALID_REQUEST,
                message=message,
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _raise_raw_query_unavailable() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.RAW_QUERY_UNAVAILABLE,
                message="Runtime log raw query is unavailable.",
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _raise_conflict(message: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INVALID_REQUEST,
                message=message,
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _raise_bad_request(message: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INVALID_REQUEST,
                message=message,
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _raise_validation_failed(message: str = "Request validation failed.") -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INVALID_REQUEST,
                message=message,
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _raise_internal_error(message: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INTERNAL_ERROR,
                message=message,
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _require_system_admin(context: AdminContext) -> None:
    if not context.has_role("system_admin"):
        raise_admin_forbidden("system_admin role is required for this action.")


def _require_service_catalog_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_owner", "service_developer"},
    ):
        return
    raise_admin_forbidden("Service catalog scope is required for this action.")


def _require_release_review_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_developer", "service_owner", "auditor"},
    ):
        return
    raise_admin_forbidden("Release review scope is required for this action.")


def _require_publish_request_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_developer", "service_owner"},
    ):
        return
    raise_admin_forbidden("Publish request scope is required for this action.")


def _require_publish_decision_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_service_role(service_id, "service_owner"):
        return
    raise_admin_forbidden("Publish approval scope is required for this action.")


def _require_publish_activation_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_developer", "service_owner"},
    ):
        return
    raise_admin_forbidden("Publish activation scope is required for this action.")


def _require_runtime_log_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(service_id, {"service_operator", "auditor"}):
        return
    raise_admin_forbidden("Runtime log scope is required for this action.")


def _require_runtime_metrics_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_service_role(service_id, "service_operator"):
        return
    raise_admin_forbidden("Runtime metrics scope is required for this action.")


def _require_security_lifecycle_read_access(
    context: AdminContext,
    service_id: str,
) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_service_role(service_id, "auditor"):
        return
    raise_admin_forbidden("Security lifecycle audit scope is required for this action.")


def _require_raw_query_request_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_operator", "auditor", "service_owner"},
    ):
        return
    raise_admin_forbidden("Raw query request scope is required for this action.")


def _require_raw_query_decision_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(service_id, {"auditor", "service_owner"}):
        return
    raise_admin_forbidden("Raw query approval scope is required for this action.")


def _require_export_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(service_id, {"auditor", "service_owner"}):
        return
    raise_admin_forbidden("Export scope is required for this action.")


def _require_raw_query_token_requester(
    context: AdminContext,
    request: GovernedActionRequest,
) -> None:
    if context.has_role("system_admin"):
        return
    if context.actor_id == request.requested_by and context.can_access_service(
        request.service_id
    ):
        return
    raise_admin_forbidden("Raw query token requester scope is required for this action.")


def _create_raw_query_view_token() -> str:
    return f"rqv_{secrets.token_urlsafe(32)}"


def _hash_raw_query_view_token(token: str) -> str:
    if not token.strip():
        raise ValueError("raw query view token must not be blank")
    return f"sha256:{hashlib.sha256(token.encode('utf-8')).hexdigest()}"


_PHASE2_SAFE_AUDIT_REASON = "governed workflow reason supplied"


def _safe_phase2_audit_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return _PHASE2_SAFE_AUDIT_REASON


def _safe_phase2_audit_state(
    state: BaseModel | Mapping[str, Any],
) -> dict[str, Any]:
    values = (
        state.model_dump(mode="json")
        if isinstance(state, BaseModel)
        else dict(state)
    )
    for field_name in ("reason", "decision_reason"):
        if field_name in values:
            value = values.pop(field_name)
            values[f"{field_name}_present"] = (
                isinstance(value, str) and bool(value.strip())
            )
    return values


def _raw_query_token_audit_state(
    token: Any,
    *,
    include_terminal_timestamps: bool = True,
    status_override: str | None = None,
) -> dict[str, Any]:
    state = {
        "request_id": token.request_id,
        "service_id": token.service_id,
        "trace_id": token.trace_id,
        "status": status_override or token.request.status,
        "expires_at": token.expires_at.isoformat(),
    }
    if include_terminal_timestamps and token.expired_at is not None:
        state["expired_at"] = token.expired_at.isoformat()
    if include_terminal_timestamps and token.viewed_at is not None:
        state["viewed_at"] = token.viewed_at.isoformat()
    return state


def _raw_query_view_request_response(
    request: GovernedActionRequest,
) -> RawQueryViewRequestResponse:
    return RawQueryViewRequestResponse(
        request_id=request.request_id,
        service_id=request.service_id,
        trace_id=request.resource_id,
        resource_type="raw_query",
        action="decrypt",
        status=request.status,
        requested_by=request.requested_by,
        requested_at=request.requested_at,
        decided_by=request.decided_by,
        decided_at=request.decided_at,
        reason=request.reason,
        decision_reason=request.decision_reason,
    )


def _raw_query_view_request_or_404(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    request_id: str,
) -> GovernedActionRequest:
    request = repository.get_governed_action_request(request_id)
    if (
        request is None
        or request.service_id != service_id
        or request.resource_type != "raw_query"
        or request.action != "decrypt"
    ):
        _raise_not_found("Raw query view request does not exist.")
    return request


def _service_response(service: Service) -> ServiceResponse:
    return ServiceResponse(
        service_id=service.service_id,
        display_name=service.display_name,
        environment=service.environment,
        default_threshold_preset=service.default_threshold_preset,
        max_input_tokens=service.max_input_tokens,
        status=service.status,
        created_by=service.created_by,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )


def _accessible_service_response(
    service: Service,
    *,
    roles: frozenset[str],
) -> AccessibleServiceResponse:
    return AccessibleServiceResponse(
        service_id=service.service_id,
        display_name=service.display_name,
        environment=service.environment,
        status=service.status,
        roles=sorted(roles),
    )


def _admin_user_lookup_response(user: AdminUser) -> AdminUserLookupResponse:
    return AdminUserLookupResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
    )


def _service_member_responses(
    role_rows: list[UserServiceRole],
) -> list[ServiceMemberResponse]:
    members: dict[str, ServiceMemberResponse] = {}
    for role_row in role_rows:
        member = members.get(role_row.user_id)
        if member is None:
            member = ServiceMemberResponse(
                service_id=role_row.service_id,
                user=_admin_user_lookup_response(role_row.user),
                roles=[],
            )
            members[role_row.user_id] = member
        member.roles.append(
            ServiceMemberRoleResponse(
                role=role_row.role,
                assigned_by=role_row.assigned_by,
                assigned_at=role_row.assigned_at,
            )
        )
    return list(members.values())


def _service_role_grant_response(
    role_record: UserServiceRole,
) -> ServiceRoleGrantResponse:
    return ServiceRoleGrantResponse(
        service_id=role_record.service_id,
        user_id=role_record.user_id,
        role=role_record.role,
        assigned_by=role_record.assigned_by,
        assigned_at=role_record.assigned_at,
    )


def _service_role_revoke_response(
    role_record: UserServiceRole,
    *,
    revoked_by: str,
    revoked_at: datetime,
) -> ServiceRoleRevokeResponse:
    return ServiceRoleRevokeResponse(
        service_id=role_record.service_id,
        user_id=role_record.user_id,
        role=role_record.role,
        revoked_by=revoked_by,
        revoked_at=revoked_at,
    )


def _api_key_response(api_key: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        key_id=api_key.key_id,
        key_fingerprint=api_key.key_fingerprint,
        environment=api_key.environment,
        app_id=api_key.app_id,
        service_id=api_key.service_id,
        allowed_intents=list(api_key.allowed_intents or []),
        allowed_route_keys=list(api_key.allowed_route_keys or []),
        status=api_key.status,
        expires_at=api_key.expires_at,
        revoked_at=api_key.revoked_at,
        created_by=api_key.created_by,
        created_at=api_key.created_at,
    )


def _api_key_after_state(api_key: ApiKey) -> dict[str, object]:
    return _api_key_response(api_key).model_dump(mode="json", exclude_none=True) | {
        "api_key": "REDACTED"
    }


def _runtime_setup_environment(service: Service, environment: str | None) -> str:
    target_environment = environment or service.environment
    if target_environment != service.environment:
        _raise_validation_failed("environment must match the selected Service environment.")
    return target_environment


def _active_release_intent_route_candidates(
    repository: IntentRoutingRepository,
    service: Service,
    environment: str,
) -> tuple[Release | None, list[IntentRouteCandidateResponse]]:
    release = repository.get_active_release(service.service_id, environment)
    if release is None:
        return None, []

    catalog_version = repository.get_catalog_version(
        service.service_id,
        release.intent_catalog_version,
    )
    if catalog_version is None:
        return release, []
    intents = catalog_version.snapshot.get("intents", [])
    if not isinstance(intents, list):
        return release, []

    candidates: list[IntentRouteCandidateResponse] = []
    for intent in intents:
        if not isinstance(intent, Mapping):
            continue
        if intent.get("status") != IntentStatus.active.value:
            continue
        candidates.append(
            IntentRouteCandidateResponse(
                intent_id=str(intent.get("intent_id", "")),
                display_name=str(intent.get("display_name", "")),
                route_key=str(intent.get("route_key", "")),
                status=str(intent.get("status", "")),
                source="active_release",
            )
        )
    return release, candidates


def _validate_runtime_api_key_scope(
    repository: IntentRoutingRepository,
    service: Service,
    request: ServiceApiKeyCreateRequest,
) -> Release:
    environment = _runtime_setup_environment(service, request.environment)
    release, candidates = _active_release_intent_route_candidates(
        repository,
        service,
        environment,
    )
    if release is None:
        _raise_validation_failed(
            "active release is required for scoped API key creation."
        )

    candidate_intents = {candidate.intent_id for candidate in candidates}
    candidate_route_keys = {candidate.route_key for candidate in candidates}
    unknown_intents = sorted(set(request.allowed_intents) - candidate_intents)
    unknown_route_keys = sorted(set(request.allowed_route_keys) - candidate_route_keys)
    if unknown_intents:
        _raise_validation_failed(
            "allowed_intents must come from active release candidates: "
            + ", ".join(unknown_intents)
        )
    if unknown_route_keys:
        _raise_validation_failed(
            "allowed_route_keys must come from active release candidates: "
            + ", ".join(unknown_route_keys)
        )
    return release


def _create_api_key_for_service(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    environment: str,
    app_id: str,
    allowed_intents: list[str],
    allowed_route_keys: list[str],
    expires_in_days: int,
    actor_id: str,
    now: datetime,
) -> tuple[ApiKey, str]:
    api_key_secret = f"irt_{generate_api_key_secret()}"
    api_key = repository.create_api_key(
        key_id=f"key_live_{uuid4().hex}",
        key_hash=hash_secret(api_key_secret),
        key_fingerprint=fingerprint_secret(api_key_secret),
        environment=environment,
        app_id=app_id,
        service_id=service_id,
        allowed_intents=allowed_intents,
        allowed_route_keys=allowed_route_keys,
        status=ApiKeyStatus.active.value,
        expires_at=now + timedelta(days=expires_in_days),
        revoked_at=None,
        created_by=actor_id,
        created_at=now,
    )
    repository.insert_audit_log(
        event_type="api_key.created",
        actor_id=actor_id,
        service_id=api_key.service_id,
        trace_id=None,
        target_type="api_key",
        target_id=api_key.key_id,
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=_api_key_after_state(api_key),
        created_at=now,
    )
    return api_key, api_key_secret


def _revoke_api_key_record(
    repository: IntentRoutingRepository,
    *,
    api_key: ApiKey,
    actor_id: str,
    now: datetime,
) -> ApiKey:
    if api_key.status == ApiKeyStatus.revoked.value:
        return api_key
    before_state = _api_key_after_state(api_key)
    repository.revoke_api_key(api_key, revoked_at=now)
    repository.insert_audit_log(
        event_type="api_key.revoked",
        actor_id=actor_id,
        service_id=api_key.service_id,
        trace_id=None,
        target_type="api_key",
        target_id=api_key.key_id,
        view_reason=None,
        source_ip=None,
        before_state=before_state,
        after_state=_api_key_after_state(api_key),
        created_at=now,
    )
    return api_key


def _runtime_setup_active_release_response(
    release: Release | None,
) -> RuntimeSetupActiveReleaseResponse | None:
    if release is None:
        return None
    return RuntimeSetupActiveReleaseResponse(
        release_version=release.release_version,
        policy_version=release.policy_version,
        intent_catalog_version=release.intent_catalog_version,
        test_run_id=release.test_run_id,
    )


def _runtime_setup_selected_key_response(
    api_key: ApiKey | None,
) -> RuntimeSetupSelectedKeyResponse | None:
    if api_key is None:
        return None
    return RuntimeSetupSelectedKeyResponse(
        key_id=api_key.key_id,
        key_fingerprint=api_key.key_fingerprint,
        app_id=api_key.app_id,
        status=api_key.status,
        expires_at=api_key.expires_at,
        allowed_intents=list(api_key.allowed_intents or []),
        allowed_route_keys=list(api_key.allowed_route_keys or []),
    )


def _intent_response(intent: Intent) -> IntentResponse:
    return IntentResponse(
        id=intent.id,
        service_id=intent.service_id,
        intent_id=intent.intent_id,
        domain=intent.domain,
        display_name=intent.display_name,
        description=intent.description,
        route_key=intent.route_key,
        status=intent.status,
        include_keywords=list(intent.include_keywords or []),
        exclude_keywords=list(intent.exclude_keywords or []),
        created_by=intent.created_by,
        updated_by=intent.updated_by,
        created_at=intent.created_at,
        updated_at=intent.updated_at,
    )


def _example_response(example: IntentExample) -> ExampleResponse:
    return ExampleResponse(
        example_id=example.example_id,
        service_id=example.service_id,
        intent_id=example.intent_id,
        example_type=example.example_type,
        text_masked=example.text_masked,
        embedding=example.embedding,
        source=example.source,
        test_case_id=example.test_case_id,
        approved=example.approved,
        created_by=example.created_by,
        created_at=example.created_at,
    )


def _policy_version_response(policy_version: PolicyVersion) -> PolicyVersionResponse:
    return PolicyVersionResponse(
        policy_version=policy_version.policy_version,
        service_id=policy_version.service_id,
        threshold_preset=policy_version.threshold_preset,
        threshold_value=float(policy_version.threshold_value),
        clarify_margin=float(policy_version.clarify_margin),
        min_candidate_score=float(policy_version.min_candidate_score),
        fallback_score=float(policy_version.fallback_score),
        risk_policy=PolicyToggle.model_validate(policy_version.risk_policy),
        off_topic_policy=OffTopicPolicySettings.model_validate(
            policy_version.off_topic_policy
        ),
        created_by=policy_version.created_by,
        created_at=policy_version.created_at,
    )


def _catalog_version_response(
    catalog_version: IntentCatalogVersion,
) -> CatalogVersionResponse:
    return CatalogVersionResponse(
        intent_catalog_version=catalog_version.intent_catalog_version,
        service_id=catalog_version.service_id,
        snapshot=catalog_version.snapshot,
        created_by=catalog_version.created_by,
        created_at=catalog_version.created_at,
    )


def _catalog_version_list_item_response(
    catalog_version: IntentCatalogVersion,
) -> CatalogVersionListItemResponse:
    snapshot = catalog_version.snapshot or {}
    intents = snapshot.get("intents", [])
    intent_count = len(intents) if isinstance(intents, list) else 0
    approved_example_count = 0
    if isinstance(intents, list):
        for intent in intents:
            if not isinstance(intent, Mapping):
                continue
            examples = intent.get("examples", [])
            if isinstance(examples, list):
                approved_example_count += sum(
                    1
                    for example in examples
                    if isinstance(example, Mapping) and example.get("approved") is True
                )
    return CatalogVersionListItemResponse(
        intent_catalog_version=catalog_version.intent_catalog_version,
        service_id=catalog_version.service_id,
        intent_count=intent_count,
        approved_example_count=approved_example_count,
        created_by=catalog_version.created_by,
        created_at=catalog_version.created_at,
    )


def _test_run_summary_response(summary: CsvTestRunSummary) -> TestRunSummaryResponse:
    return TestRunSummaryResponse(
        test_run_id=summary.test_run_id,
        test_dataset_version=summary.test_dataset_version,
        threshold_preset=summary.threshold_preset,
        threshold_value=summary.threshold_value,
        pass_rate=summary.pass_rate,
        review_rate=summary.review_rate,
        risk_pass_rate=summary.risk_pass_rate,
        gate_passed=summary.gate_passed,
        block_reasons=summary.block_reasons,
        recommendations=summary.recommendations,
    )


def _test_run_list_item_response(
    test_run: TestRun,
    dataset: TestDataset,
    results: list[TestResult],
) -> TestRunListItemResponse:
    summary = summarize_test_run(test_run, results)
    return TestRunListItemResponse(
        test_run_id=test_run.test_run_id,
        service_id=test_run.service_id,
        test_dataset_version=test_run.test_dataset_version,
        source_filename=dataset.source_filename,
        policy_version=test_run.policy_version,
        intent_catalog_version=test_run.intent_catalog_version,
        threshold_preset=test_run.threshold_preset,
        threshold_value=float(test_run.threshold_value),
        pass_rate=float(test_run.pass_rate),
        review_rate=float(test_run.review_rate),
        risk_pass_rate=float(test_run.risk_pass_rate),
        gate_passed=test_run.gate_passed,
        block_reasons=summary.block_reasons,
        recommendations=summary.recommendations,
        created_by=test_run.created_by,
        created_at=test_run.created_at,
    )


def _test_result_response(result: TestResult) -> TestRunResultResponse:
    return TestRunResultResponse(
        case_id=result.case_id,
        query_masked=result.query_masked,
        case_type=result.case_type,
        expected_decision=result.expected_decision,
        expected_intent=result.expected_intent,
        actual_decision=result.actual_decision,
        actual_intent=result.actual_intent,
        actual_route_key=result.actual_route_key,
        confidence=float(result.confidence) if result.confidence is not None else None,
        result=result.result,
        reason=result.reason,
    )


def _release_response(release: Release) -> ReleaseResponse:
    return ReleaseResponse(
        release_version=release.release_version,
        service_id=release.service_id,
        environment=release.environment,
        policy_version=release.policy_version,
        intent_catalog_version=release.intent_catalog_version,
        model_version=release.model_version,
        vector_index_version=release.vector_index_version,
        test_dataset_version=release.test_dataset_version,
        test_run_id=release.test_run_id,
        pass_rate=float(release.pass_rate),
        risk_pass_rate=float(release.risk_pass_rate),
        active=release.active,
        released_by=release.released_by,
        released_at=release.released_at,
        rollback_target=release.rollback_target,
    )


def _release_diff_response(diff: release_service.ReleaseDiff) -> ReleaseDiffResponse:
    return ReleaseDiffResponse(
        service_id=diff.service_id,
        release_version=diff.release_version,
        compare_to=diff.compare_to,
        policy_version_diff=diff.policy_version_diff,
        catalog_version_diff=diff.catalog_version_diff,
        model_version_diff=diff.model_version_diff,
        test_run_diff=diff.test_run_diff,
        rollback_target=diff.rollback_target,
    )


def _publish_request_response(
    request: GovernedActionRequest,
) -> PublishRequestResponse:
    return PublishRequestResponse(
        request_id=request.request_id,
        service_id=request.service_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        status=request.status,
        requested_by=request.requested_by,
        requested_at=request.requested_at,
        decided_by=request.decided_by,
        decided_at=request.decided_at,
        reason=request.reason,
        decision_reason=request.decision_reason,
    )


def _publish_request_or_404(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    request_id: str,
) -> GovernedActionRequest:
    request = repository.get_governed_action_request(request_id)
    if (
        request is None
        or request.service_id != service_id
        or request.resource_type not in {"intent", "example", "release"}
    ):
        _raise_not_found("Publish request does not exist.")
    return request


def _runtime_log_response(runtime_log: Mapping[str, Any]) -> RuntimeLogResponse:
    values = {
        field: runtime_log[field]
        for field in MASKED_RUNTIME_LOG_FIELD_NAMES
    }
    for decimal_field in ("confidence", "margin", "threshold_value"):
        value = values[decimal_field]
        values[decimal_field] = float(value) if value is not None else None
    return RuntimeLogResponse.model_validate(values)


def _export_audit_state(
    response: ExportResponse,
    *,
    filter_keys: set[str],
    row_count: int | None = None,
    status_override: str | None = None,
) -> dict[str, Any]:
    state = response.model_dump(mode="json", exclude={"content"})
    if status_override is not None:
        state["status"] = status_override
    state["filter_keys"] = sorted(filter_keys)
    if row_count is not None:
        state["row_count"] = row_count
    return state


def _safe_export_filter_keys(
    resource_type: str,
    filters: Mapping[str, object],
) -> set[str]:
    if resource_type != "runtime_log":
        return set()
    return set(filters) & {"trace_id"}


def _runtime_log_export_trace_id(filters: Mapping[str, object]) -> str | None:
    unknown_filters = set(filters) - {"trace_id"}
    if unknown_filters:
        _raise_bad_request("Unsupported export filter.")
    trace_id = filters.get("trace_id")
    if trace_id is None:
        return None
    if not isinstance(trace_id, str) or not _safe_export_trace_id(trace_id):
        _raise_bad_request("Unsupported export filter.")
    return trace_id


def _safe_export_trace_id(trace_id: str) -> bool:
    allowed_punctuation = {"-", "_", ".", ":"}
    return (
        trace_id == trace_id.strip()
        and 0 < len(trace_id) <= 200
        and all(
            character.isascii()
            and (character.isalnum() or character in allowed_punctuation)
            for character in trace_id
        )
    )


def _serialize_export_rows(
    rows: list[Mapping[str, Any]],
    *,
    export_format: str,
) -> str:
    if export_format == "jsonl":
        return "\n".join(
            json.dumps(dict(row), ensure_ascii=False, default=str)
            for row in rows
        )

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(MASKED_RUNTIME_LOG_FIELD_NAMES))
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in MASKED_RUNTIME_LOG_FIELD_NAMES})
    return output.getvalue()


def _raw_text_keyring() -> RawTextKeyring:
    try:
        return load_raw_text_keyring()
    except MissingRawTextKekError:
        _raise_internal_error("Raw text encryption key is not configured.")
    except ValueError as exc:
        raise _raw_text_keyring_invalid_error() from exc


def _raw_text_keyring_invalid_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INTERNAL_ERROR,
                message="Raw text encryption key is invalid.",
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True),
    )


def _encrypted_raw_text(example: IntentExample) -> EncryptedText:
    return EncryptedText(
        ciphertext=example.text_raw_ciphertext,
        encrypted_dek=example.text_raw_encrypted_dek,
        key_id=example.text_raw_key_id,
        iv=example.text_raw_iv,
        auth_tag=example.text_raw_auth_tag,
        algorithm=example.text_raw_algorithm,
        encrypted_dek_iv=example.text_raw_encrypted_dek_iv,
        encrypted_dek_auth_tag=example.text_raw_encrypted_dek_auth_tag,
    )


def _example_text_for_embedding(example: IntentExample) -> str:
    embed_from = environ.get("EMBED_EXAMPLES_FROM", "masked").strip().lower()
    if embed_from == "masked":
        return example.text_masked
    if embed_from == "raw":
        return _raw_text_keyring().decrypt_text(_encrypted_raw_text(example))
    raise ValueError("EMBED_EXAMPLES_FROM must be one of: masked, raw.")


def _ensure_service_exists(
    repository: IntentRoutingRepository,
    service_id: str,
) -> None:
    if repository.get_service(service_id) is None:
        _raise_not_found("Service does not exist.")


async def _test_run_create_request_from_http(
    http_request: Request,
) -> TestRunCreateRequest:
    content_type = http_request.headers.get("content-type", "").split(";")[0].lower()
    if content_type == "multipart/form-data":
        return await _test_run_create_request_from_multipart(http_request)
    if content_type in {"", "application/json"} or content_type.endswith("+json"):
        try:
            payload = await http_request.json()
            return TestRunCreateRequest.model_validate(payload)
        except ValidationError:
            _raise_validation_failed()
        except Exception:
            _raise_bad_request("Request body must be valid JSON.")
    _raise_bad_request("Unsupported content type.")


async def _test_run_create_request_from_multipart(
    http_request: Request,
) -> TestRunCreateRequest:
    try:
        form = await http_request.form()
    except Exception:
        _raise_bad_request("Multipart form data is invalid.")

    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        _raise_validation_failed()

    try:
        csv_text = (await upload.read()).decode("utf-8")
    except UnicodeDecodeError:
        _raise_bad_request("Uploaded CSV must be UTF-8 text.")

    source_filename = _form_string(form.get("source_filename"))
    if source_filename is None:
        source_filename = upload.filename or "uploaded.csv"

    try:
        return TestRunCreateRequest.model_validate(
            {
                "policy_version": form.get("policy_version"),
                "intent_catalog_version": form.get("intent_catalog_version"),
                "threshold_preset": form.get("threshold_preset"),
                "source_filename": source_filename,
                "csv_text": csv_text,
            }
        )
    except ValidationError:
        _raise_validation_failed()


def _form_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _example_after_state(example: IntentExample) -> dict[str, object]:
    state = _example_response(example).model_dump(mode="json", exclude_none=True)
    if example.embedding is not None:
        state["embedding"] = {
            "dimension": len(example.embedding),
            "stored": True,
        }
    return state


def _policy_version_id(service_id: str, now: datetime) -> str:
    return f"pol-{service_id}-{now:%Y%m%d}-{uuid4().hex[:8]}"


def _catalog_version_id(service_id: str, now: datetime) -> str:
    return f"cat-{service_id}-{now:%Y%m%d}-{uuid4().hex[:8]}"


def _catalog_snapshot(
    repository: IntentRoutingRepository,
    service_id: str,
) -> dict[str, Any]:
    intents: list[dict[str, object]] = []
    for intent in repository.list_active_intents(service_id):
        examples = [
            {
                "example_id": str(example.example_id),
                "example_type": example.example_type,
                "text_masked": example.text_masked,
                "approved": example.approved,
            }
            for example in repository.list_approved_examples(
                service_id,
                intent.intent_id,
            )
        ]
        intents.append(
            {
                "intent_id": intent.intent_id,
                "domain": intent.domain,
                "display_name": intent.display_name,
                "description": intent.description,
                "route_key": intent.route_key,
                "status": intent.status,
                "include_keywords": list(intent.include_keywords or []),
                "exclude_keywords": list(intent.exclude_keywords or []),
                "examples": examples,
            }
        )
    return {"service_id": service_id, "intents": intents}


@router.get("/me/services", response_model=list[AccessibleServiceResponse])
def list_accessible_services(
    session_context: Annotated[
        AdminSessionContextRecord,
        Depends(require_admin_session_context),
    ],
    session: Annotated[Session, Depends(get_admin_session)],
) -> list[AccessibleServiceResponse]:
    context = admin_context_from_session_record(session_context)
    repository = IntentRoutingRepository(session)
    if context.has_role("system_admin"):
        return [
            _accessible_service_response(service, roles=frozenset({"system_admin"}))
            for service in repository.list_services()
        ]

    return [
        _accessible_service_response(
            service,
            roles=frozenset(context.service_roles.get(service.service_id, frozenset())),
        )
        for service in repository.list_services_for_user(context.actor_id)
    ]


@router.get("/users", response_model=list[AdminUserLookupResponse])
def list_admin_users(
    session_context: Annotated[
        AdminSessionContextRecord,
        Depends(require_admin_session_context),
    ],
    session: Annotated[Session, Depends(get_admin_session)],
    query: str | None = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 25,
) -> list[AdminUserLookupResponse]:
    context = admin_context_from_session_record(session_context)
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    return [
        _admin_user_lookup_response(user)
        for user in repository.list_admin_users(query=query, limit=limit)
    ]


@router.get(
    "/services/{service_id}/members",
    response_model=list[ServiceMemberResponse],
)
def list_service_members(
    service_id: str,
    session_context: Annotated[
        AdminSessionContextRecord,
        Depends(require_admin_session_context),
    ],
    session: Annotated[Session, Depends(get_admin_session)],
) -> list[ServiceMemberResponse]:
    context = admin_context_from_session_record(session_context)
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    if repository.get_service(service_id) is None:
        _raise_not_found("Service does not exist.")
    return _service_member_responses(repository.list_service_member_roles(service_id))


@router.post(
    "/services/{service_id}/members/{user_id}/roles",
    response_model=ServiceRoleGrantResponse,
)
def grant_service_member_role(
    service_id: str,
    user_id: str,
    request: ServiceRoleGrantRequest,
    http_request: Request,
    session_context: Annotated[
        AdminSessionContextRecord,
        Depends(require_admin_session_context),
    ],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ServiceRoleGrantResponse:
    context = admin_context_from_session_record(session_context)
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    if repository.get_service(service_id) is None:
        _raise_not_found("Service does not exist.")
    user = repository.get_admin_user(user_id)
    if user is None:
        _raise_not_found("Admin user does not exist.")
    if user.status != "active":
        _raise_bad_request("Admin user is not active.")
    now = datetime.now(UTC)
    role_record, role_created = repository.ensure_user_service_role_with_created(
        user_id=user_id,
        service_id=service_id,
        role=request.role,
        assigned_by=context.actor_id,
        assigned_at=now,
    )
    grant_response = _service_role_grant_response(role_record)
    if role_created:
        repository.insert_audit_log(
            event_type="service_membership.role_granted",
            actor_id=context.actor_id,
            service_id=service_id,
            trace_id=None,
            target_type="user_service_role",
            target_id=f"{service_id}:{user_id}:{request.role}",
            view_reason=None,
            source_ip=source_ip_from_request(http_request),
            before_state=None,
            after_state=grant_response.model_dump(mode="json"),
            created_at=now,
        )
    session.commit()
    return grant_response


@router.delete(
    "/services/{service_id}/members/{user_id}/roles/{role}",
    response_model=ServiceRoleRevokeResponse,
)
def revoke_service_member_role(
    service_id: str,
    user_id: str,
    role: Annotated[ServiceAdminRole, Path()],
    http_request: Request,
    session_context: Annotated[
        AdminSessionContextRecord,
        Depends(require_admin_session_context),
    ],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ServiceRoleRevokeResponse:
    context = admin_context_from_session_record(session_context)
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    if repository.get_service(service_id) is None:
        _raise_not_found("Service does not exist.")
    role_record = repository.delete_user_service_role_by_key(user_id, service_id, role)
    if role_record is None:
        _raise_not_found("Service role does not exist.")
    now = datetime.now(UTC)
    before_state = _service_role_grant_response(role_record).model_dump(mode="json")
    response = _service_role_revoke_response(
        role_record,
        revoked_by=context.actor_id,
        revoked_at=now,
    )
    repository.insert_audit_log(
        event_type="service_membership.role_revoked",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="user_service_role",
        target_id=f"{service_id}:{user_id}:{role}",
        view_reason=None,
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state=response.model_dump(mode="json"),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service(
    request: ServiceCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ServiceResponse:
    _require_system_admin(context)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    try:
        service = repository.create_service(
            service_id=request.service_id,
            display_name=request.display_name,
            environment=request.environment,
            default_threshold_preset=request.default_threshold_preset.value,
            max_input_tokens=request.max_input_tokens,
            status="active",
            created_by=context.actor_id,
            created_at=now,
            updated_at=now,
        )
    except IntegrityError:
        session.rollback()
        _raise_conflict("Service already exists.")
    repository.insert_audit_log(
        event_type="service.created",
        actor_id=context.actor_id,
        service_id=service.service_id,
        trace_id=None,
        target_type="service",
        target_id=service.service_id,
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=_service_response(service).model_dump(mode="json"),
        created_at=now,
    )
    session.commit()
    return _service_response(service)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    service_id: str | None = None,
    environment: str | None = None,
    status: ApiKeyStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ApiKeyResponse]:
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    return [
        _api_key_response(api_key)
        for api_key in repository.list_api_keys(
            service_id=service_id,
            environment=environment,
            status=status.value if status is not None else None,
            limit=limit,
        )
    ]


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    request: ApiKeyCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ApiKeyCreateResponse:
    _require_system_admin(context)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(request.service_id)
    if service is None:
        _raise_not_found("Service does not exist.")

    api_key, api_key_secret = _create_api_key_for_service(
        repository,
        service_id=request.service_id,
        environment=request.environment,
        app_id=request.app_id,
        allowed_intents=request.allowed_intents,
        allowed_route_keys=request.allowed_route_keys,
        expires_in_days=request.expires_in_days,
        actor_id=context.actor_id,
        now=now,
    )
    session.commit()
    return ApiKeyCreateResponse(
        api_key=api_key_secret,
        api_key_displayed_once=True,
        **_api_key_response(api_key).model_dump(),
    )


@router.post("/api-keys/{key_id}:revoke", response_model=ApiKeyResponse)
def revoke_api_key(
    key_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ApiKeyResponse:
    _require_system_admin(context)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    api_key = repository.get_api_key_by_id(key_id)
    if api_key is None:
        _raise_not_found("API key does not exist.")

    _revoke_api_key_record(
        repository,
        api_key=api_key,
        actor_id=context.actor_id,
        now=now,
    )
    session.commit()
    return _api_key_response(api_key)


@router.get("/services/{service_id}/api-keys", response_model=list[ApiKeyResponse])
def list_service_api_keys(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    environment: str | None = None,
    status: ApiKeyStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ApiKeyResponse]:
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    if environment is not None:
        _runtime_setup_environment(service, environment)
    return [
        _api_key_response(api_key)
        for api_key in repository.list_api_keys(
            service_id=service_id,
            environment=environment,
            status=status.value if status is not None else None,
            limit=limit,
        )
    ]


@router.post(
    "/services/{service_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_api_key(
    service_id: str,
    request: ServiceApiKeyCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ApiKeyCreateResponse:
    _require_system_admin(context)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")

    _validate_runtime_api_key_scope(repository, service, request)
    api_key, api_key_secret = _create_api_key_for_service(
        repository,
        service_id=service_id,
        environment=request.environment,
        app_id=request.app_id,
        allowed_intents=request.allowed_intents,
        allowed_route_keys=request.allowed_route_keys,
        expires_in_days=request.expires_in_days,
        actor_id=context.actor_id,
        now=now,
    )
    session.commit()
    return ApiKeyCreateResponse(
        api_key=api_key_secret,
        api_key_displayed_once=True,
        **_api_key_response(api_key).model_dump(),
    )


@router.post(
    "/services/{service_id}/api-keys/{key_id}:revoke",
    response_model=ApiKeyResponse,
)
def revoke_service_api_key(
    service_id: str,
    key_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ApiKeyResponse:
    _require_system_admin(context)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    api_key = repository.get_api_key_by_id(key_id)
    if api_key is None:
        _raise_not_found("API key does not exist.")
    if api_key.service_id != service_id:
        raise_admin_forbidden("API key does not belong to the selected Service.")

    _revoke_api_key_record(
        repository,
        api_key=api_key,
        actor_id=context.actor_id,
        now=now,
    )
    session.commit()
    return _api_key_response(api_key)


@router.get(
    "/services/{service_id}/runtime-setup",
    response_model=RuntimeSetupResponse,
)
def get_runtime_setup(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    environment: str | None = None,
    app_id: str | None = None,
    key_id: str | None = None,
) -> RuntimeSetupResponse:
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")

    target_environment = _runtime_setup_environment(service, environment)
    release, _ = _active_release_intent_route_candidates(
        repository,
        service,
        target_environment,
    )
    selected_key: ApiKey | None = None
    if key_id is not None:
        selected_key = repository.get_api_key_by_id(key_id)
        if selected_key is None:
            _raise_not_found("API key does not exist.")
        if selected_key.service_id != service_id:
            raise_admin_forbidden("API key does not belong to the selected Service.")
        if selected_key.environment != target_environment:
            _raise_validation_failed(
                "API key environment must match the selected environment."
            )
        if app_id is not None and selected_key.app_id != app_id:
            _raise_validation_failed("app_id must match the selected API key.")

    template_key_id = (
        selected_key.key_id
        if selected_key is not None
        else "{{intent_routing_key_id}}"
    )
    template_app_id = (
        selected_key.app_id
        if selected_key is not None
        else app_id or "{{intent_routing_app_id}}"
    )
    warnings: list[str] = []
    if release is None:
        warnings.append("No active release exists for the selected Service environment.")

    return RuntimeSetupResponse(
        service_id=service_id,
        environment=target_environment,
        runtime_endpoint="/v1/intent-route",
        recommended_timeout_seconds=8,
        active_release=_runtime_setup_active_release_response(release),
        selected_key=_runtime_setup_selected_key_response(selected_key),
        headers_template={
            "Authorization": "Bearer {{intent_routing_api_key}}",
            "X-Key-Id": template_key_id,
            "X-App-Id": template_app_id,
            "X-Service-Id": service_id,
            "X-Request-Id": "{{workflow_run_id}}",
            "Content-Type": "application/json",
        },
        body_template={
            "query": "{{user_query}}",
            "channel": "chat",
            "user_context": {"workflow_run_id": "{{workflow_run_id}}"},
        },
        dify_variable_mapping=[
            RuntimeSetupVariableMappingResponse(
                field="Authorization",
                source="Secret variable intent_routing_api_key",
            ),
            RuntimeSetupVariableMappingResponse(
                field="X-Key-Id",
                source="Secret or environment variable intent_routing_key_id",
            ),
            RuntimeSetupVariableMappingResponse(
                field="X-App-Id",
                source="Literal approved app_id",
            ),
            RuntimeSetupVariableMappingResponse(
                field="X-Service-Id",
                source="Workflow variable service_id",
            ),
            RuntimeSetupVariableMappingResponse(
                field="X-Request-Id",
                source="workflow_run_id",
            ),
        ],
        checklist=[
            "Dify secret variable masks intent_routing_api_key.",
            "Timeout is 8 seconds.",
            "408, 5xx, and timeout branches use fallback or human handoff "
            "without automatic retry loops.",
            "Downstream nodes preserve trace_id, request_id, route_key, and release_version.",
        ],
        docs=[
            "docs/integrations/dify-http-request-node.md",
            "docs/integrations/dify-handoff-checklist.md",
            "docs/integrations/dify-branching-playbook.md",
            "docs/api/openapi-runtime-examples.md",
        ],
        warnings=warnings,
    )


@router.get(
    "/services/{service_id}/runtime-logs",
    response_model=list[RuntimeLogResponse],
)
def list_runtime_logs(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[RuntimeLogResponse]:
    _require_runtime_log_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        _runtime_log_response(runtime_log)
        for runtime_log in repository.list_masked_runtime_logs(service_id, limit=limit)
    ]


@router.get(
    "/services/{service_id}/runtime-metrics",
    response_model=RuntimeMetricsResponse,
)
def get_runtime_metrics(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    window_hours: Annotated[int, Query(ge=1, le=24 * 31)] = 24,
) -> RuntimeMetricsResponse:
    _require_runtime_metrics_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return RuntimeMetricsResponse.model_validate(
        repository.runtime_metrics(service_id, window_hours=window_hours)
    )


@router.get(
    "/services/{service_id}/audit-logs",
    response_model=list[AuditLogResponse],
)
def list_audit_logs(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    event_type: Annotated[str | None, Query(min_length=1)] = None,
    trace_id: Annotated[str | None, Query(min_length=1)] = None,
) -> list[AuditLogResponse]:
    _require_security_lifecycle_read_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        AuditLogResponse.model_validate(safe_audit_log_item(audit_log))
        for audit_log in repository.list_audit_logs(
            service_id,
            limit=limit,
            event_type=event_type,
            trace_id=trace_id,
        )
    ]


@router.get(
    "/services/{service_id}/security/raw-text-key-summary",
    response_model=RawTextKeySummaryResponse,
)
def get_raw_text_key_summary(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RawTextKeySummaryResponse:
    _require_security_lifecycle_read_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    active_key_id = (environ.get("RAW_TEXT_KEK_ID", DEFAULT_RAW_TEXT_KEK_ID)).strip() or None
    return RawTextKeySummaryResponse.model_validate(
        raw_text_key_summary_from_counts(
            service_id=service_id,
            active_key_id=active_key_id,
            counts=repository.count_raw_text_key_inventory(service_id),
        )
    )


@router.post(
    "/services/{service_id}/exports",
    response_model=ExportResponse,
)
def create_export(
    service_id: str,
    request: ExportCreateRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ExportResponse:
    _require_export_access(context, service_id)
    requested_at = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    export_id = f"exp_{uuid4().hex}"
    filter_keys = _safe_export_filter_keys(request.resource_type, request.filters)
    requested_response = ExportResponse(
        export_id=export_id,
        service_id=service_id,
        resource_type=request.resource_type,
        status="rejected",
        format=request.format,
        content=None,
        rejection_reason=None,
        requested_by=context.actor_id,
        requested_at=requested_at,
    )
    repository.insert_audit_log(
        event_type="export.requested",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="export",
        target_id=export_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=None,
        after_state=_export_audit_state(
            requested_response,
            filter_keys=filter_keys,
            status_override="requested",
        ),
        created_at=requested_at,
    )

    try:
        if request.resource_type != "runtime_log":
            _raise_bad_request("Unsupported export resource type.")
        trace_id = _runtime_log_export_trace_id(request.filters)
    except HTTPException:
        rejected_at = datetime.now(UTC)
        rejected_response = ExportResponse(
            export_id=export_id,
            service_id=service_id,
            resource_type=request.resource_type,
            status="rejected",
            format=request.format,
            content=None,
            rejection_reason="Unsupported export request.",
            requested_by=context.actor_id,
            requested_at=requested_at,
        )
        repository.insert_audit_log(
            event_type="export.rejected",
            actor_id=context.actor_id,
            service_id=service_id,
            trace_id=None,
            target_type="export",
            target_id=export_id,
            view_reason=_safe_phase2_audit_reason(request.reason),
            source_ip=source_ip_from_request(http_request),
            before_state=_export_audit_state(
                requested_response,
                filter_keys=filter_keys,
                status_override="requested",
            ),
            after_state=_export_audit_state(
                rejected_response,
                filter_keys=filter_keys,
            ),
            created_at=rejected_at,
        )
        session.commit()
        _raise_bad_request("Unsupported export request.")

    rows = repository.list_masked_runtime_logs_for_export(
        service_id,
        trace_id=trace_id,
    )
    response = ExportResponse(
        export_id=export_id,
        service_id=service_id,
        resource_type=request.resource_type,
        status="completed",
        format=request.format,
        content=_serialize_export_rows(rows, export_format=request.format),
        rejection_reason=None,
        requested_by=context.actor_id,
        requested_at=requested_at,
    )
    repository.insert_audit_log(
        event_type="export.completed",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="export",
        target_id=export_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=_export_audit_state(
            requested_response,
            filter_keys=filter_keys,
            status_override="requested",
        ),
        after_state=_export_audit_state(
            response,
            filter_keys=filter_keys,
            row_count=len(rows),
        ),
        created_at=datetime.now(UTC),
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/runtime-logs/{trace_id}/raw-query-view-requests",
    response_model=RawQueryViewRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_raw_query_view_request(
    service_id: str,
    trace_id: str,
    request: RawQueryViewRequestCreateRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RawQueryViewRequestResponse:
    _require_raw_query_request_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    runtime_log = repository.get_masked_runtime_log(service_id, trace_id)
    if runtime_log is None:
        _raise_not_found("Runtime log does not exist.")

    view_request = repository.create_governed_action_request(
        request_id=f"gar_{uuid4().hex}",
        service_id=service_id,
        resource_type="raw_query",
        resource_id=trace_id,
        action="decrypt",
        requested_by=context.actor_id,
        requested_at=now,
        reason=request.reason,
    )
    response = _raw_query_view_request_response(view_request)
    repository.insert_audit_log(
        event_type="raw_query.requested",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=trace_id,
        target_type="raw_query_view_request",
        target_id=view_request.request_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=None,
        after_state=_safe_phase2_audit_state(response),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/raw-query-view-requests/{request_id}:approve",
    response_model=RawQueryViewRequestResponse,
)
def approve_raw_query_view_request(
    service_id: str,
    request_id: str,
    request: RawQueryViewRequestDecisionRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RawQueryViewRequestResponse:
    _require_raw_query_decision_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    view_request = _raw_query_view_request_or_404(
        repository,
        service_id=service_id,
        request_id=request_id,
    )
    before_state = _safe_phase2_audit_state(
        _raw_query_view_request_response(view_request)
    )
    try:
        repository.approve_governed_action_request(
            view_request,
            decided_by=context.actor_id,
            decided_at=now,
            reason=request.reason,
        )
    except ValueError as exc:
        if "request author" in str(exc):
            raise_admin_forbidden(str(exc))
        _raise_conflict(str(exc))
    response = _raw_query_view_request_response(view_request)
    repository.insert_audit_log(
        event_type="raw_query.approved",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=view_request.resource_id,
        target_type="raw_query_view_request",
        target_id=view_request.request_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state=_safe_phase2_audit_state(response),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/raw-query-view-requests/{request_id}:reject",
    response_model=RawQueryViewRequestResponse,
)
def reject_raw_query_view_request(
    service_id: str,
    request_id: str,
    request: RawQueryViewRequestDecisionRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RawQueryViewRequestResponse:
    if request.reason is None:
        _raise_validation_failed()
    _require_raw_query_decision_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    view_request = _raw_query_view_request_or_404(
        repository,
        service_id=service_id,
        request_id=request_id,
    )
    before_state = _safe_phase2_audit_state(
        _raw_query_view_request_response(view_request)
    )
    try:
        repository.reject_governed_action_request(
            view_request,
            decided_by=context.actor_id,
            decided_at=now,
            reason=request.reason,
        )
    except ValueError as exc:
        if "request author" in str(exc):
            raise_admin_forbidden(str(exc))
        _raise_conflict(str(exc))
    response = _raw_query_view_request_response(view_request)
    repository.insert_audit_log(
        event_type="raw_query.rejected",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=view_request.resource_id,
        target_type="raw_query_view_request",
        target_id=view_request.request_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state=_safe_phase2_audit_state(response),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/raw-query-view-requests/{request_id}:issue-token",
    response_model=RawQueryTokenResponse,
)
def issue_raw_query_view_token(
    service_id: str,
    request_id: str,
    request: RawQueryViewTokenIssueRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RawQueryTokenResponse:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    view_request = _raw_query_view_request_or_404(
        repository,
        service_id=service_id,
        request_id=request_id,
    )
    _require_raw_query_token_requester(context, view_request)
    raw_token = _create_raw_query_view_token()
    expires_at = now + timedelta(seconds=request.ttl_seconds)
    before_state = _safe_phase2_audit_state(
        _raw_query_view_request_response(view_request)
    )
    try:
        token = repository.issue_raw_query_view_token(
            view_request,
            token_id=f"rqt_{uuid4().hex}",
            token_hash=_hash_raw_query_view_token(raw_token),
            expires_at=expires_at,
            issued_by=context.actor_id,
            issued_at=now,
        )
    except ValueError as exc:
        _raise_conflict(str(exc))
    response = RawQueryTokenResponse(
        request_id=view_request.request_id,
        token=raw_token,
        expires_at=expires_at,
    )
    repository.insert_audit_log(
        event_type="raw_query.token_issued",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=view_request.resource_id,
        target_type="raw_query_view_request",
        target_id=view_request.request_id,
        view_reason=None,
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state={
            **_raw_query_token_audit_state(token),
            "token_returned_once": True,
        },
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/runtime-logs/{trace_id}:decrypt-raw-query",
    response_model=RawQueryDecryptResponse,
)
def decrypt_raw_runtime_query(
    service_id: str,
    trace_id: str,
    request: RawQueryDecryptRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RawQueryDecryptResponse:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    if request.raw_query_view_token is None:
        raise_admin_forbidden("Approved raw query view token is required.")
    raw_query_view_token_hash = _hash_raw_query_view_token(request.raw_query_view_token)
    raw_query_view_token = repository.consume_raw_query_view_token(
        token_hash=raw_query_view_token_hash,
        service_id=service_id,
        trace_id=trace_id,
        consumed_at=now,
    )
    if raw_query_view_token is None:
        expired_token = repository.expire_raw_query_view_token(
            token_hash=raw_query_view_token_hash,
            service_id=service_id,
            trace_id=trace_id,
            expired_at=now,
        )
        if expired_token is not None:
            repository.insert_audit_log(
                event_type="raw_query.token_expired",
                actor_id=context.actor_id,
                service_id=service_id,
                trace_id=trace_id,
                target_type="raw_query_view_request",
                target_id=expired_token.request_id,
                view_reason=None,
                source_ip=source_ip_from_request(http_request),
                before_state=_raw_query_token_audit_state(
                    expired_token,
                    include_terminal_timestamps=False,
                    status_override="token_issued",
                ),
                after_state=_raw_query_token_audit_state(expired_token),
                created_at=now,
            )
            session.commit()
        raise_admin_forbidden("Approved raw query view token is required.")
    _require_raw_query_token_requester(context, raw_query_view_token.request)

    runtime_log = repository.get_runtime_log_for_decrypt(service_id, trace_id)
    if runtime_log is None:
        _raise_not_found("Runtime log does not exist.")

    if (
        runtime_log.raw_query_deleted_at is not None
        or runtime_log_encrypted_raw_query(runtime_log) is None
    ):
        _raise_raw_query_unavailable()

    try:
        query_raw = decrypt_runtime_raw_query(runtime_log, _raw_text_keyring())
    except (InvalidTag, ValueError):
        _raise_raw_query_unavailable()
    if query_raw is None:
        _raise_raw_query_unavailable()

    repository.insert_audit_log(
        event_type="raw_query.viewed",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=trace_id,
        target_type="runtime_log",
        target_id=trace_id,
        view_reason=_safe_phase2_audit_reason(request.view_reason),
        source_ip=source_ip_from_request(http_request),
        before_state=None,
        after_state=raw_query_view_after_state(runtime_log),
        created_at=now,
    )
    session.commit()
    return RawQueryDecryptResponse(
        trace_id=trace_id,
        service_id=service_id,
        query_raw=query_raw,
        viewed_by=context.actor_id,
        viewed_at=now,
    )


@router.get(
    "/services/{service_id}/runtime-logs/{trace_id}",
    response_model=RuntimeLogResponse,
)
def get_runtime_log(
    service_id: str,
    trace_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> RuntimeLogResponse:
    _require_runtime_log_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    runtime_log = repository.get_masked_runtime_log(service_id, trace_id)
    if runtime_log is None:
        _raise_not_found("Runtime log does not exist.")
    return _runtime_log_response(runtime_log)


@router.post(
    "/services/{service_id}/intents",
    response_model=IntentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_intent(
    service_id: str,
    request: IntentCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> IntentResponse:
    _require_service_catalog_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    try:
        intent = repository.create_intent(
            service_id=service_id,
            intent_id=request.intent_id,
            domain=request.domain,
            display_name=request.display_name,
            description=request.description,
            route_key=request.route_key,
            status=IntentStatus.draft.value,
            include_keywords=request.include_keywords,
            exclude_keywords=request.exclude_keywords,
            created_by=context.actor_id,
            updated_by=context.actor_id,
            created_at=now,
            updated_at=now,
        )
    except IntegrityError:
        session.rollback()
        _raise_conflict("Intent id or route_key already exists for this service.")
    session.commit()
    return _intent_response(intent)


@router.get("/services/{service_id}/intents", response_model=list[IntentResponse])
def list_intents(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> list[IntentResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [_intent_response(intent) for intent in repository.list_intents(service_id)]


@router.get(
    "/services/{service_id}/intent-route-candidates",
    response_model=list[IntentRouteCandidateResponse],
)
def list_intent_route_candidates(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    source: str = "current_catalog",
    environment: str | None = None,
) -> list[IntentRouteCandidateResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    if source == "current_catalog":
        return [
            IntentRouteCandidateResponse(
                intent_id=intent.intent_id,
                display_name=intent.display_name,
                route_key=intent.route_key,
                status=intent.status,
                source=source,
            )
            for intent in repository.list_active_intents(service_id)
        ]
    if source == "active_release":
        release = repository.get_active_release(service_id, environment or service.environment)
        if release is None:
            return []
        catalog_version = repository.get_catalog_version(
            service_id,
            release.intent_catalog_version,
        )
        if catalog_version is None:
            return []
        intents = catalog_version.snapshot.get("intents", [])
        if not isinstance(intents, list):
            return []
        candidates: list[IntentRouteCandidateResponse] = []
        for intent in intents:
            if not isinstance(intent, Mapping):
                continue
            if intent.get("status") != IntentStatus.active.value:
                continue
            candidates.append(
                IntentRouteCandidateResponse(
                    intent_id=str(intent.get("intent_id", "")),
                    display_name=str(intent.get("display_name", "")),
                    route_key=str(intent.get("route_key", "")),
                    status=str(intent.get("status", "")),
                    source=source,
                )
            )
        return candidates
    _raise_bad_request("source must be current_catalog or active_release")


@router.patch(
    "/services/{service_id}/intents/{intent_id}",
    response_model=IntentResponse,
)
def patch_intent(
    service_id: str,
    intent_id: str,
    request: IntentPatchRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> IntentResponse:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    intent = repository.get_intent(service_id, intent_id)
    if intent is None:
        _raise_not_found("Intent does not exist.")

    updates: dict[str, object] = {}
    for field_name in request.model_fields_set:
        value = getattr(request, field_name)
        if isinstance(value, IntentStatus):
            value = value.value
        updates[field_name] = value
    updates["updated_by"] = context.actor_id
    updates["updated_at"] = datetime.now(UTC)
    try:
        intent = repository.update_intent(intent, **updates)
    except IntegrityError:
        session.rollback()
        _raise_conflict("Intent route_key already exists for this service.")
    session.commit()
    return _intent_response(intent)


@router.post(
    "/services/{service_id}/intents/{intent_id}/examples",
    response_model=ExampleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_example(
    service_id: str,
    intent_id: str,
    request: ExampleCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ExampleResponse:
    _require_service_catalog_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    if repository.get_intent(service_id, intent_id) is None:
        _raise_not_found("Intent does not exist.")

    encrypted_raw_text = _raw_text_keyring().encrypt_text(request.text_raw)
    example = repository.create_example(
        service_id=service_id,
        intent_id=intent_id,
        example_type=request.example_type.value,
        text_raw_ciphertext=encrypted_raw_text.ciphertext,
        text_raw_encrypted_dek=encrypted_raw_text.encrypted_dek,
        text_raw_encrypted_dek_iv=encrypted_raw_text.encrypted_dek_iv,
        text_raw_encrypted_dek_auth_tag=encrypted_raw_text.encrypted_dek_auth_tag,
        text_raw_key_id=encrypted_raw_text.key_id,
        text_raw_iv=encrypted_raw_text.iv,
        text_raw_auth_tag=encrypted_raw_text.auth_tag,
        text_raw_algorithm=encrypted_raw_text.algorithm,
        text_masked=mask_pii(request.text_raw),
        embedding=None,
        source=request.source,
        test_case_id=request.test_case_id,
        approved=False,
        created_by=context.actor_id,
        created_at=now,
    )
    repository.insert_audit_log(
        event_type="example.created",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="intent_example",
        target_id=str(example.example_id),
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=_example_after_state(example),
        created_at=now,
    )
    session.commit()
    return _example_response(example)


@router.post(
    "/services/{service_id}/policy-versions",
    response_model=PolicyVersionResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_version(
    service_id: str,
    request: PolicyVersionCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> PolicyVersionResponse:
    _require_service_catalog_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)

    try:
        policy_version = repository.create_policy_version(
            policy_version=_policy_version_id(service_id, now),
            service_id=service_id,
            threshold_preset=request.threshold_preset.value,
            threshold_value=Decimal(str(request.threshold_preset.threshold)),
            clarify_margin=Decimal(str(request.clarify_margin)),
            min_candidate_score=Decimal(str(request.min_candidate_score)),
            fallback_score=Decimal(str(request.fallback_score)),
            risk_policy=request.risk_policy.model_dump(mode="json", exclude_none=True),
            off_topic_policy=request.off_topic_policy.model_dump(
                mode="json",
                exclude_none=True,
            ),
            created_by=context.actor_id,
            created_at=now,
        )
    except IntegrityError:
        session.rollback()
        _raise_conflict("Policy version already exists.")
    repository.insert_audit_log(
        event_type="policy_version.created",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="policy_version",
        target_id=policy_version.policy_version,
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=_policy_version_response(policy_version).model_dump(mode="json"),
        created_at=now,
    )
    session.commit()
    return _policy_version_response(policy_version)


@router.get(
    "/services/{service_id}/policy-versions",
    response_model=list[PolicyVersionResponse],
    response_model_exclude_none=True,
)
def list_policy_versions(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PolicyVersionResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        _policy_version_response(policy_version)
        for policy_version in repository.list_policy_versions(service_id, limit=limit)
    ]


@router.get(
    "/services/{service_id}/policy-versions/{policy_version}",
    response_model=PolicyVersionResponse,
    response_model_exclude_none=True,
)
def get_policy_version(
    service_id: str,
    policy_version: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> PolicyVersionResponse:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    persisted_policy_version = repository.get_policy_version(service_id, policy_version)
    if persisted_policy_version is None:
        _raise_not_found("Policy version does not exist.")
    return _policy_version_response(persisted_policy_version)


@router.post(
    "/services/{service_id}/catalog-versions",
    response_model=CatalogVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_catalog_version(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> CatalogVersionResponse:
    _require_service_catalog_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    try:
        catalog_version = repository.create_catalog_version(
            intent_catalog_version=_catalog_version_id(service_id, now),
            service_id=service_id,
            snapshot=_catalog_snapshot(repository, service_id),
            created_by=context.actor_id,
            created_at=now,
        )
    except IntegrityError:
        session.rollback()
        _raise_conflict("Catalog version already exists.")

    response = _catalog_version_response(catalog_version)
    repository.insert_audit_log(
        event_type="catalog_version.created",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="intent_catalog_version",
        target_id=catalog_version.intent_catalog_version,
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=response.model_dump(mode="json"),
        created_at=now,
    )
    session.commit()
    return response


@router.get(
    "/services/{service_id}/catalog-versions",
    response_model=list[CatalogVersionListItemResponse],
)
def list_catalog_versions(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CatalogVersionListItemResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        _catalog_version_list_item_response(catalog_version)
        for catalog_version in repository.list_catalog_versions(service_id, limit=limit)
    ]


@router.get(
    "/services/{service_id}/intents/{intent_id}/examples",
    response_model=list[ExampleResponse],
)
def list_examples(
    service_id: str,
    intent_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> list[ExampleResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    if repository.get_intent(service_id, intent_id) is None:
        _raise_not_found("Intent does not exist.")
    return [
        _example_response(example)
        for example in repository.list_examples(service_id, intent_id)
    ]


@router.patch(
    "/services/{service_id}/examples/{example_id}:approve",
    response_model=ExampleResponse,
)
def approve_example(
    service_id: str,
    example_id: UUID,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ExampleResponse:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    example = repository.get_example(service_id, example_id)
    if example is None:
        _raise_not_found("Example does not exist.")
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    before_state = _example_after_state(example)
    try:
        provider = get_embedding_provider()
        embedding_text = _example_text_for_embedding(example)
        embeddings = provider.embed_texts(
            [embedding_text],
            max_tokens=service.max_input_tokens,
        )
        if len(embeddings) != 1:
            raise ValueError("embedding provider returned the wrong result count")
        embedding = embeddings[0]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorEnvelope(
                trace_id=_trace_id(),
                error=ErrorInfo(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Embedding generation failed.",
                    retryable=False,
                ),
            ).model_dump(mode="json", exclude_none=True),
        ) from exc
    if len(embedding) != 1024:
        _raise_internal_error("Embedding generation failed.")
    example = repository.approve_example(example, embedding=embedding)
    repository.insert_audit_log(
        event_type="example.approved",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="intent_example",
        target_id=str(example.example_id),
        view_reason=None,
        source_ip=None,
        before_state=before_state,
        after_state=_example_after_state(example),
        created_at=datetime.now(UTC),
    )
    session.commit()
    return _example_response(example)


@router.post(
    "/services/{service_id}/test-runs",
    response_model=TestRunSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_run(
    service_id: str,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> TestRunSummaryResponse:
    _require_service_catalog_access(context, service_id)
    request = await _test_run_create_request_from_http(http_request)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    policy_version = repository.get_policy_version(service_id, request.policy_version)
    if policy_version is None:
        _raise_not_found("Policy version does not exist.")
    catalog_version = repository.get_catalog_version(
        service_id,
        request.intent_catalog_version,
    )
    if catalog_version is None:
        _raise_not_found("Catalog version does not exist.")

    try:
        summary = run_csv_tests(
            repository,
            service=service,
            policy_version=policy_version,
            catalog_version=catalog_version,
            threshold_preset=request.threshold_preset,
            source_filename=request.source_filename,
            csv_text=request.csv_text,
            created_by=context.actor_id,
        )
    except CsvValidationError as exc:
        session.rollback()
        _raise_bad_request(str(exc))
    except IntegrityError:
        session.rollback()
        _raise_conflict("Test run already exists.")

    session.commit()
    return _test_run_summary_response(summary)


@router.get(
    "/services/{service_id}/test-runs",
    response_model=list[TestRunListItemResponse],
)
def list_test_runs(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    gate_passed: bool | None = None,
    risk_passed: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[TestRunListItemResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    rows = repository.list_test_runs(
        service_id,
        gate_passed=gate_passed,
        risk_passed=risk_passed,
        limit=limit,
    )
    return [
        _test_run_list_item_response(
            test_run,
            dataset,
            repository.list_test_results(test_run.test_run_id),
        )
        for test_run, dataset in rows
    ]


@router.get(
    "/services/{service_id}/test-runs/{test_run_id}",
    response_model=TestRunSummaryResponse,
)
def get_test_run_summary(
    service_id: str,
    test_run_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> TestRunSummaryResponse:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    test_run = repository.get_test_run(test_run_id)
    if test_run is None or test_run.service_id != service_id:
        _raise_not_found("Test run does not exist.")
    results = repository.list_test_results(test_run_id)
    return _test_run_summary_response(summarize_test_run(test_run, results))


@router.get(
    "/services/{service_id}/test-runs/{test_run_id}/results",
    response_model=list[TestRunResultResponse],
)
def get_test_run_results(
    service_id: str,
    test_run_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> list[TestRunResultResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    test_run = repository.get_test_run(test_run_id)
    if test_run is None or test_run.service_id != service_id:
        _raise_not_found("Test run does not exist.")
    return [
        _test_result_response(result)
        for result in repository.list_test_results(test_run_id)
    ]


@router.post(
    "/services/{service_id}/publish-requests",
    response_model=PublishRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_publish_request(
    service_id: str,
    request: PublishRequestCreateRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> PublishRequestResponse:
    _require_publish_request_access(context, service_id)
    if request.resource_type != "release" or request.action != "activate":
        _raise_bad_request("Only release activation publish requests are supported.")
    if request.target_version is not None and request.target_version != request.resource_id:
        _raise_bad_request("target_version must match release resource_id.")

    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    if repository.get_release(service_id, request.resource_id) is None:
        _raise_not_found("Release does not exist.")

    publish_request = repository.create_governed_action_request(
        request_id=f"gar_{uuid4().hex}",
        service_id=service_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        requested_by=context.actor_id,
        requested_at=now,
        reason=request.reason,
    )
    response = _publish_request_response(publish_request)
    repository.insert_audit_log(
        event_type="publish.requested",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="publish_request",
        target_id=publish_request.request_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=None,
        after_state=_safe_phase2_audit_state(response),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/publish-requests/{request_id}:approve",
    response_model=PublishRequestResponse,
)
def approve_publish_request(
    service_id: str,
    request_id: str,
    request: PublishRequestDecisionRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> PublishRequestResponse:
    _require_publish_decision_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    publish_request = _publish_request_or_404(
        repository,
        service_id=service_id,
        request_id=request_id,
    )
    before_state = _safe_phase2_audit_state(_publish_request_response(publish_request))
    try:
        repository.approve_governed_action_request(
            publish_request,
            decided_by=context.actor_id,
            decided_at=now,
            reason=request.reason,
        )
    except ValueError as exc:
        if "request author" in str(exc):
            raise_admin_forbidden(str(exc))
        _raise_conflict(str(exc))
    response = _publish_request_response(publish_request)
    repository.insert_audit_log(
        event_type="publish.approved",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="publish_request",
        target_id=publish_request.request_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state=_safe_phase2_audit_state(response),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/publish-requests/{request_id}:reject",
    response_model=PublishRequestResponse,
)
def reject_publish_request(
    service_id: str,
    request_id: str,
    request: PublishRequestDecisionRequest,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> PublishRequestResponse:
    if request.reason is None:
        _raise_validation_failed()
    _require_publish_decision_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    publish_request = _publish_request_or_404(
        repository,
        service_id=service_id,
        request_id=request_id,
    )
    before_state = _safe_phase2_audit_state(_publish_request_response(publish_request))
    try:
        repository.reject_governed_action_request(
            publish_request,
            decided_by=context.actor_id,
            decided_at=now,
            reason=request.reason,
        )
    except ValueError as exc:
        if "request author" in str(exc):
            raise_admin_forbidden(str(exc))
        _raise_conflict(str(exc))
    response = _publish_request_response(publish_request)
    repository.insert_audit_log(
        event_type="publish.rejected",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="publish_request",
        target_id=publish_request.request_id,
        view_reason=_safe_phase2_audit_reason(request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state=_safe_phase2_audit_state(response),
        created_at=now,
    )
    session.commit()
    return response


@router.post(
    "/services/{service_id}/publish-requests/{request_id}:activate",
    response_model=ReleaseResponse,
)
def activate_publish_request(
    service_id: str,
    request_id: str,
    http_request: Request,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ReleaseResponse:
    _require_publish_activation_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    publish_request = _publish_request_or_404(
        repository,
        service_id=service_id,
        request_id=request_id,
    )
    if publish_request.resource_type != "release" or publish_request.action != "activate":
        _raise_bad_request("Publish request is not a release activation request.")
    if publish_request.status != "approved":
        _raise_conflict("Publish request must be approved before activation.")

    try:
        before_state, release = release_service.activate_release(
            repository,
            service_id=service_id,
            release_version=publish_request.resource_id,
        )
    except release_service.ReleaseDependencyNotFoundError as exc:
        session.rollback()
        _raise_not_found(str(exc))

    publish_request.status = "activated"
    session.flush()
    repository.insert_audit_log(
        event_type="release.activated",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="release",
        target_id=release.release_version,
        view_reason=_safe_phase2_audit_reason(publish_request.reason),
        source_ip=source_ip_from_request(http_request),
        before_state=before_state,
        after_state=release_service.release_after_state(release),
        created_at=now,
    )
    session.commit()
    return _release_response(release)


@router.post(
    "/services/{service_id}/releases",
    response_model=ReleaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_release(
    service_id: str,
    request: ReleaseCreateRequest,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ReleaseResponse:
    _require_system_admin(context)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    if request.environment != service.environment:
        _raise_bad_request("Release environment must match service environment.")
    try:
        model_version = get_embedding_provider().model_version
        release = release_service.create_release(
            repository,
            service_id=service_id,
            environment=request.environment,
            policy_version=request.policy_version,
            intent_catalog_version=request.intent_catalog_version,
            model_version=model_version,
            test_run_id=request.test_run_id,
            rollback_target=request.rollback_target,
            released_by=context.actor_id,
            now=now,
        )
    except release_service.ReleaseDependencyNotFoundError as exc:
        session.rollback()
        _raise_not_found(str(exc))
    except release_service.ReleaseValidationError as exc:
        session.rollback()
        _raise_bad_request(str(exc))
    except IntegrityError:
        session.rollback()
        _raise_conflict("Release version already exists.")
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorEnvelope(
                trace_id=_trace_id(),
                error=ErrorInfo(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Release creation failed.",
                    retryable=False,
                ),
            ).model_dump(mode="json", exclude_none=True),
        ) from exc

    repository.insert_audit_log(
        event_type="release.created",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="release",
        target_id=release.release_version,
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=release_service.release_after_state(release),
        created_at=now,
    )
    session.commit()
    return _release_response(release)


@router.get(
    "/services/{service_id}/release-candidates",
    response_model=list[ReleaseCandidateResponse],
)
def list_release_candidates(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    environment: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ReleaseCandidateResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    target_environment = environment or service.environment
    environment_matches_service = target_environment == service.environment
    existing_releases = {
        release.test_run_id: release
        for release in repository.list_releases(service_id, target_environment)
    }
    rows = repository.list_test_runs(service_id, limit=limit)
    candidates: list[ReleaseCandidateResponse] = []
    for test_run, dataset in rows:
        results = repository.list_test_results(test_run.test_run_id)
        summary = summarize_test_run(test_run, results)
        existing_release = existing_releases.get(test_run.test_run_id)
        risk_passed = Decimal(str(test_run.risk_pass_rate)) == Decimal("1.0")
        block_reasons = list(summary.block_reasons)
        if not environment_matches_service:
            block_reasons.append("release environment must match service environment")
        if not risk_passed:
            block_reasons.append("risk pass rate must be 100%")
        if existing_release is not None:
            block_reasons.append("test run already has a release")
        eligible = (
            environment_matches_service
            and test_run.gate_passed
            and risk_passed
            and existing_release is None
        )
        candidates.append(
            ReleaseCandidateResponse(
                test_run_id=test_run.test_run_id,
                service_id=test_run.service_id,
                environment=target_environment,
                policy_version=test_run.policy_version,
                intent_catalog_version=test_run.intent_catalog_version,
                test_dataset_version=test_run.test_dataset_version,
                source_filename=dataset.source_filename,
                threshold_preset=test_run.threshold_preset,
                pass_rate=float(test_run.pass_rate),
                risk_pass_rate=float(test_run.risk_pass_rate),
                gate_passed=test_run.gate_passed,
                eligible=eligible,
                block_reasons=block_reasons,
                already_released=existing_release is not None,
                existing_release_version=(
                    existing_release.release_version
                    if existing_release is not None
                    else None
                ),
                created_at=test_run.created_at,
            )
        )
    return candidates


@router.get(
    "/services/{service_id}/releases/{release_version}/diff",
    response_model=ReleaseDiffResponse,
)
def get_release_diff(
    service_id: str,
    release_version: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    compare_to: str | None = None,
) -> ReleaseDiffResponse:
    _require_release_review_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    try:
        diff = release_service.build_release_diff(
            repository,
            service_id=service_id,
            release_version=release_version,
            compare_to=compare_to,
        )
    except release_service.ReleaseDependencyNotFoundError as exc:
        _raise_not_found(str(exc))
    return _release_diff_response(diff)


@router.get(
    "/services/{service_id}/releases",
    response_model=list[ReleaseResponse],
)
def list_releases(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    environment: str | None = None,
) -> list[ReleaseResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        _release_response(release)
        for release in repository.list_releases(service_id, environment)
    ]


@router.get(
    "/services/{service_id}/releases/active",
    response_model=ReleaseResponse,
)
def get_active_release(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    environment: str = "prod",
) -> ReleaseResponse:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    release = repository.get_active_release(service_id, environment)
    if release is None:
        _raise_not_found("Active release does not exist.")
    return _release_response(release)


@router.post(
    "/services/{service_id}/releases/{release_version}:activate",
    response_model=ReleaseResponse,
)
def activate_release(
    service_id: str,
    release_version: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ReleaseResponse:
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    try:
        before_state, release = release_service.activate_release(
            repository,
            service_id=service_id,
            release_version=release_version,
        )
    except release_service.ReleaseDependencyNotFoundError as exc:
        session.rollback()
        _raise_not_found(str(exc))

    repository.insert_audit_log(
        event_type="release.activated",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="release",
        target_id=release.release_version,
        view_reason=None,
        source_ip=None,
        before_state=before_state,
        after_state=release_service.release_after_state(release),
        created_at=datetime.now(UTC),
    )
    session.commit()
    return _release_response(release)


@router.post(
    "/services/{service_id}/releases/{release_version}:rollback",
    response_model=ReleaseResponse,
)
def rollback_release(
    service_id: str,
    release_version: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ReleaseResponse:
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    try:
        release, before_state, rollback_target = release_service.rollback_release(
            repository,
            service_id=service_id,
            release_version=release_version,
        )
    except release_service.ReleaseDependencyNotFoundError as exc:
        session.rollback()
        _raise_not_found(str(exc))
    except release_service.ReleaseValidationError as exc:
        session.rollback()
        _raise_bad_request(str(exc))

    after_state = release_service.release_after_state(rollback_target)
    after_state["rollback_from"] = release.release_version
    repository.insert_audit_log(
        event_type="release.rollback",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="release",
        target_id=release.release_version,
        view_reason=None,
        source_ip=None,
        before_state=before_state,
        after_state=after_state,
        created_at=datetime.now(UTC),
    )
    session.commit()
    return _release_response(rollback_target)
