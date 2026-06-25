from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from os import environ
from typing import Annotated, Any, NoReturn
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intent_routing.db.models import ApiKey, Intent, IntentExample, Service
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import SessionLocal
from intent_routing.domain.enums import (
    ApiKeyStatus,
    ErrorCode,
    ExampleType,
    IntentStatus,
    ThresholdPreset,
)
from intent_routing.domain.schemas import ErrorEnvelope, ErrorInfo, validate_route_key
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
from intent_routing.security.encryption import EnvelopeEncryptor
from intent_routing.security.pii import mask_pii

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


def _raw_text_encryptor() -> EnvelopeEncryptor:
    kek_base64 = environ.get("RAW_TEXT_KEK_BASE64")
    if kek_base64 is None or not kek_base64.strip():
        _raise_internal_error("Raw text encryption key is not configured.")
    try:
        return EnvelopeEncryptor(
            kek_id=environ.get("RAW_TEXT_KEK_ID", "local-kek-001"),
            kek_base64=kek_base64,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorEnvelope(
                trace_id=_trace_id(),
                error=ErrorInfo(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Raw text encryption key is invalid.",
                    retryable=False,
                ),
            ).model_dump(mode="json", exclude_none=True),
        ) from exc


def _ensure_service_exists(
    repository: IntentRoutingRepository,
    service_id: str,
) -> None:
    if repository.get_service(service_id) is None:
        _raise_not_found("Service does not exist.")


def _example_after_state(example: IntentExample) -> dict[str, object]:
    return _example_response(example).model_dump(mode="json", exclude_none=True)


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

    encrypted_raw_text = _raw_text_encryptor().encrypt_text(request.text_raw)
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
    example = repository.approve_example(example)
    session.commit()
    return _example_response(example)
