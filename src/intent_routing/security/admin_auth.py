from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Annotated, NoReturn
from uuid import uuid4

from fastapi import Header, HTTPException, status

from intent_routing.domain.enums import ErrorCode
from intent_routing.domain.schemas import ErrorEnvelope, ErrorInfo


@dataclass(frozen=True)
class AdminContext:
    actor_id: str
    roles: frozenset[str]
    service_scope: frozenset[str]
    all_service_scopes: bool

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def can_access_service(self, service_id: str) -> bool:
        return self.all_service_scopes or service_id in self.service_scope


def _trace_id() -> str:
    return f"irt-{uuid4().hex}"


def _error_envelope(code: ErrorCode, message: str) -> dict[str, object]:
    return ErrorEnvelope(
        trace_id=_trace_id(),
        error=ErrorInfo(
            code=code,
            message=message,
            retryable=False,
        ),
    ).model_dump(mode="json", exclude_none=True)


def _raise_authentication_failed() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_error_envelope(
            code=ErrorCode.AUTHENTICATION_FAILED,
            message="Admin authentication failed.",
        ),
    )


def raise_admin_forbidden(message: str = "Admin role is not allowed for this action.") -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_error_envelope(
            code=ErrorCode.SERVICE_SCOPE_DENIED,
            message=message,
        ),
    )


def _parse_csv_header(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def require_admin_context(
    admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    actor_roles: Annotated[str | None, Header(alias="X-Actor-Roles")] = None,
    service_scope: Annotated[str | None, Header(alias="X-Service-Scope")] = None,
) -> AdminContext:
    expected_token = environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if expected_token is None or not expected_token.strip() or admin_token != expected_token:
        _raise_authentication_failed()
    if actor_id is None or actor_roles is None:
        _raise_authentication_failed()

    roles = _parse_csv_header(actor_roles)
    if not roles:
        _raise_authentication_failed()

    return AdminContext(
        actor_id=actor_id,
        roles=roles,
        service_scope=_parse_csv_header(service_scope or ""),
        all_service_scopes="system_admin" in roles,
    )
