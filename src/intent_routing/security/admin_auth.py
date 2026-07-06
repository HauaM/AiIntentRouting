from __future__ import annotations

from collections.abc import Mapping
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
    service_roles: Mapping[str, frozenset[str]]

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def can_access_service(self, service_id: str) -> bool:
        return self.all_service_scopes or service_id in self.service_scope

    def has_service_role(self, service_id: str, role: str) -> bool:
        return self.has_role("system_admin") or role in self.service_roles.get(
            service_id,
            frozenset(),
        )

    def has_any_service_role(self, service_id: str, roles: frozenset[str] | set[str]) -> bool:
        return self.has_role("system_admin") or bool(
            self.service_roles.get(service_id, frozenset()).intersection(roles)
        )


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


def require_trusted_header_admin_context(
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

    parsed_roles = _parse_csv_header(actor_roles)
    if not parsed_roles:
        _raise_authentication_failed()
    service_scope_values = _parse_csv_header(service_scope or "")
    global_roles = frozenset(role for role in parsed_roles if role == "system_admin")
    scoped_roles = parsed_roles - global_roles
    service_roles = {
        scoped_service_id: scoped_roles
        for scoped_service_id in service_scope_values
        if scoped_roles
    }

    return AdminContext(
        actor_id=actor_id,
        roles=global_roles,
        service_scope=service_scope_values,
        all_service_scopes="system_admin" in global_roles,
        service_roles=service_roles,
    )
