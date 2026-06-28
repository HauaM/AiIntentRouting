from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from os import environ
from typing import Annotated, Any, Literal, NoReturn
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from intent_routing.config import DEFAULT_RAW_TEXT_KEK_ID, MissingRawTextKekError
from intent_routing.db.models import (
    ApiKey,
    Intent,
    IntentCatalogVersion,
    IntentExample,
    PolicyVersion,
    Release,
    Service,
    TestResult,
)
from intent_routing.db.repositories import (
    MASKED_RUNTIME_LOG_FIELD_NAMES,
    IntentRoutingRepository,
)
from intent_routing.db.session import SessionLocal
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
    require_admin_context,
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


class ApiKeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1)
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

    @field_validator("view_reason")
    @classmethod
    def view_reason_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("view_reason must be at least 10 characters")
        return stripped


class RawQueryDecryptResponse(BaseModel):
    trace_id: str
    service_id: str
    query_raw: str
    viewed_by: str
    viewed_at: datetime


def get_admin_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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


def _raise_validation_failed() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=ErrorEnvelope(
            trace_id=_trace_id(),
            error=ErrorInfo(
                code=ErrorCode.INVALID_REQUEST,
                message="Request validation failed.",
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
    if context.has_role("service_developer") and context.can_access_service(service_id):
        return
    raise_admin_forbidden("Service catalog scope is required for this action.")


def _require_runtime_log_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    allowed_roles = {"service_operator", "auditor"}
    if context.roles.intersection(allowed_roles) and context.can_access_service(service_id):
        return
    raise_admin_forbidden("Runtime log scope is required for this action.")


def _require_runtime_metrics_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_role("service_operator") and context.can_access_service(service_id):
        return
    raise_admin_forbidden("Runtime metrics scope is required for this action.")


def _require_security_lifecycle_read_access(
    context: AdminContext,
    service_id: str,
) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_role("auditor") and context.can_access_service(service_id):
        return
    raise_admin_forbidden("Security lifecycle audit scope is required for this action.")


def _require_raw_query_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_role("auditor") and context.can_access_service(service_id):
        return
    raise_admin_forbidden("Raw query audit scope is required for this action.")


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


def _runtime_log_response(runtime_log: Mapping[str, Any]) -> RuntimeLogResponse:
    values = {
        field: runtime_log[field]
        for field in MASKED_RUNTIME_LOG_FIELD_NAMES
    }
    for decimal_field in ("confidence", "margin", "threshold_value"):
        value = values[decimal_field]
        values[decimal_field] = float(value) if value is not None else None
    return RuntimeLogResponse.model_validate(values)


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

    api_key_secret = f"irt_{generate_api_key_secret()}"
    api_key = repository.create_api_key(
        key_id=f"key_live_{uuid4().hex}",
        key_hash=hash_secret(api_key_secret),
        key_fingerprint=fingerprint_secret(api_key_secret),
        environment=request.environment,
        app_id=request.app_id,
        service_id=request.service_id,
        allowed_intents=request.allowed_intents,
        allowed_route_keys=request.allowed_route_keys,
        status=ApiKeyStatus.active.value,
        expires_at=now + timedelta(days=request.expires_in_days),
        revoked_at=None,
        created_by=context.actor_id,
        created_at=now,
    )
    repository.insert_audit_log(
        event_type="api_key.created",
        actor_id=context.actor_id,
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

    before_state = _api_key_after_state(api_key)
    repository.revoke_api_key(api_key, revoked_at=now)
    repository.insert_audit_log(
        event_type="api_key.revoked",
        actor_id=context.actor_id,
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
    session.commit()
    return _api_key_response(api_key)


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
    _require_raw_query_access(context, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
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
        view_reason=request.view_reason,
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
