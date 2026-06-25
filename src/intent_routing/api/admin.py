from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, NoReturn
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intent_routing.db.models import ApiKey, Service
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import SessionLocal
from intent_routing.domain.enums import ApiKeyStatus, ErrorCode, ThresholdPreset
from intent_routing.domain.schemas import ErrorEnvelope, ErrorInfo
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


def _require_system_admin(context: AdminContext) -> None:
    if not context.has_role("system_admin"):
        raise_admin_forbidden("system_admin role is required for this action.")


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
