from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from os import environ
from typing import Annotated, NoReturn
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, status

from intent_routing.db.models import ApiKey
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import session_scope
from intent_routing.domain.enums import ErrorCode
from intent_routing.domain.schemas import ErrorEnvelope, ErrorInfo
from intent_routing.security.api_keys import ApiKeyRecord, check_scope, verify_secret

ApiKeyLookup = Callable[[str], ApiKeyRecord | None]


@dataclass(frozen=True)
class AuthContext:
    key_id: str
    app_id: str
    service_id: str
    request_id: str | None
    allowed_intents: list[str]
    allowed_route_keys: list[str]


def _trace_id() -> str:
    return f"irt-{uuid4().hex}"


def _error_envelope(
    code: ErrorCode,
    message: str,
    retryable: bool,
    request_id: str | None,
) -> dict[str, object]:
    return ErrorEnvelope(
        trace_id=_trace_id(),
        request_id=request_id,
        error=ErrorInfo(
            code=code,
            message=message,
            retryable=retryable,
        ),
    ).model_dump(mode="json", exclude_none=True)


def _raise_authentication_failed(request_id: str | None) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_error_envelope(
            code=ErrorCode.AUTHENTICATION_FAILED,
            message="API key authentication failed.",
            retryable=False,
            request_id=request_id,
        ),
    )


def _raise_scope_denied(request_id: str | None) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_error_envelope(
            code=ErrorCode.SERVICE_SCOPE_DENIED,
            message="API key is not allowed to access this service or route.",
            retryable=False,
            request_id=request_id,
        ),
    )


def _record_from_model(model: ApiKey) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=model.key_id,
        key_hash=model.key_hash,
        key_fingerprint=model.key_fingerprint,
        environment=model.environment,
        app_id=model.app_id,
        service_id=model.service_id,
        allowed_intents=list(model.allowed_intents or []),
        allowed_route_keys=list(model.allowed_route_keys or []),
        status=model.status,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
    )


def get_runtime_environment() -> str:
    return environ.get("INTENT_ROUTING_ENVIRONMENT", "prod")


def get_api_key_lookup() -> ApiKeyLookup:
    def lookup(key_id: str) -> ApiKeyRecord | None:
        with session_scope() as session:
            repository = IntentRoutingRepository(session)
            model = repository.get_api_key_by_id(key_id)
            if model is None:
                return None
            return _record_from_model(model)

    return lookup


def _bearer_secret(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, credentials = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not credentials:
        return None
    return credentials


def _is_expired(record: ApiKeyRecord, now: datetime) -> bool:
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now


def require_api_key(
    lookup: Annotated[ApiKeyLookup, Depends(get_api_key_lookup)],
    environment: Annotated[str, Depends(get_runtime_environment)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    app_id: Annotated[str | None, Header(alias="X-App-Id")] = None,
    service_id: Annotated[str | None, Header(alias="X-Service-Id")] = None,
    key_id: Annotated[str | None, Header(alias="X-Key-Id")] = None,
    request_id: Annotated[str | None, Header(alias="X-Request-Id")] = None,
) -> AuthContext:
    secret = _bearer_secret(authorization)
    if secret is None or app_id is None or service_id is None or key_id is None:
        _raise_authentication_failed(request_id)

    record = lookup(key_id)
    if record is None:
        _raise_authentication_failed(request_id)

    if not verify_secret(secret, record.key_hash):
        _raise_authentication_failed(request_id)

    if (
        record.status != "active"
        or record.revoked_at is not None
        or _is_expired(record, datetime.now(UTC))
        or record.environment != environment
    ):
        _raise_authentication_failed(request_id)

    scope_result = check_scope(
        record,
        app_id=app_id,
        service_id=service_id,
        route_key=None,
        intent_id=None,
    )
    if not scope_result.allowed:
        _raise_scope_denied(request_id)

    return AuthContext(
        key_id=record.key_id,
        app_id=record.app_id,
        service_id=record.service_id,
        request_id=request_id,
        allowed_intents=record.allowed_intents,
        allowed_route_keys=record.allowed_route_keys,
    )
