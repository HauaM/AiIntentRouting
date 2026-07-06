from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from intent_routing.db.repositories import (
    AdminSessionContextRecord,
    IntentRoutingRepository,
)
from intent_routing.db.session import SessionLocal
from intent_routing.security.admin_auth import _raise_authentication_failed
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
