from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from os import environ
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from intent_routing.db.repositories import (
    AdminSessionContextRecord,
    IntentRoutingRepository,
)
from intent_routing.db.session import SessionLocal
from intent_routing.security.admin_auth import (
    AdminContext,
    _raise_authentication_failed,
    require_trusted_header_admin_context,
)
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_NAME,
    hash_admin_session_token,
)


def get_admin_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def require_admin_session_context(
    session: Annotated[Session, Depends(get_admin_session)],
    admin_session_token: Annotated[
        str | None,
        Cookie(alias=ADMIN_SESSION_COOKIE_NAME),
    ] = None,
) -> AdminSessionContextRecord:
    if admin_session_token is None or not admin_session_token.strip():
        _raise_authentication_failed()
    repository = IntentRoutingRepository(session)
    session_context = repository.get_active_admin_session_context(
        hash_admin_session_token(admin_session_token),
        now=datetime.now(UTC),
    )
    if session_context is None:
        _raise_authentication_failed()
    session.commit()
    return session_context


def admin_context_from_session_record(
    session_context: AdminSessionContextRecord,
) -> AdminContext:
    service_roles: dict[str, frozenset[str]] = {}
    for role in session_context.service_roles:
        service_roles[role.service_id] = frozenset(
            {*service_roles.get(role.service_id, frozenset()), role.role}
        )
    return AdminContext(
        actor_id=session_context.user.user_id,
        roles=session_context.global_roles,
        service_scope=frozenset(service_roles),
        all_service_scopes="system_admin" in session_context.global_roles,
        service_roles=service_roles,
    )


def require_admin_context(
    session: Annotated[Session, Depends(get_admin_session)],
    admin_session_token: Annotated[
        str | None,
        Cookie(alias=ADMIN_SESSION_COOKIE_NAME),
    ] = None,
    admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    actor_roles: Annotated[str | None, Header(alias="X-Actor-Roles")] = None,
    service_scope: Annotated[str | None, Header(alias="X-Service-Scope")] = None,
) -> AdminContext:
    if admin_session_token is not None and admin_session_token.strip():
        repository = IntentRoutingRepository(session)
        session_context = repository.get_active_admin_session_context(
            hash_admin_session_token(admin_session_token),
            now=datetime.now(UTC),
        )
        if session_context is None:
            _raise_authentication_failed()
        session.commit()
        return admin_context_from_session_record(session_context)

    if environ.get("ADMIN_AUTH_MODE", "").strip() == "trusted_headers":
        return require_trusted_header_admin_context(
            admin_token=admin_token,
            actor_id=actor_id,
            actor_roles=actor_roles,
            service_scope=service_scope,
        )

    _raise_authentication_failed()
