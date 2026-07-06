from __future__ import annotations

from datetime import UTC, datetime
from os import environ
from typing import Annotated, NoReturn
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_session_context,
)
from intent_routing.db.models import AdminUser, UserServiceRole
from intent_routing.db.repositories import (
    AdminSessionContextRecord,
    IntentRoutingRepository,
)
from intent_routing.domain.enums import ErrorCode
from intent_routing.domain.schemas import ErrorEnvelope, ErrorInfo
from intent_routing.security.admin_auth import _raise_authentication_failed
from intent_routing.security.admin_passwords import (
    hash_admin_password,
    verify_admin_password,
)
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_MAX_AGE_SECONDS,
    ADMIN_SESSION_COOKIE_NAME,
    admin_session_cookie_secure,
    admin_session_expires_at,
    create_admin_session_token,
    hash_admin_session_token,
)

router = APIRouter(prefix="/admin/v1/auth", tags=["admin-auth"])


class AdminAuthBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str | None = Field(default=None, min_length=1)
    email: str = Field(min_length=3)
    display_name: str = Field(min_length=1)
    password: str = Field(min_length=8)


class AdminAuthLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class AdminCurrentUser(BaseModel):
    user_id: str
    email: str
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class AdminAuthServiceRole(BaseModel):
    service_id: str
    role: str


class AdminAuthCurrentUserResponse(BaseModel):
    user: AdminCurrentUser
    global_roles: list[str]
    service_roles: list[AdminAuthServiceRole]


class AdminAuthSuccessResponse(BaseModel):
    success: bool


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


def _raise_conflict(message: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=_error_envelope(ErrorCode.INVALID_REQUEST, message),
    )


def _require_bootstrap_token(admin_token: str | None) -> None:
    expected_token = environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if expected_token is None or not expected_token.strip() or admin_token != expected_token:
        _raise_authentication_failed()


def _set_admin_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        ADMIN_SESSION_COOKIE_NAME,
        token,
        max_age=ADMIN_SESSION_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=admin_session_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _clear_admin_session_cookie(response: Response) -> None:
    response.delete_cookie(
        ADMIN_SESSION_COOKIE_NAME,
        httponly=True,
        secure=admin_session_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _current_user_response(
    user: AdminUser,
    *,
    global_roles: frozenset[str],
    service_roles: tuple[UserServiceRole, ...],
) -> AdminAuthCurrentUserResponse:
    return AdminAuthCurrentUserResponse(
        user=AdminCurrentUser(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        ),
        global_roles=sorted(global_roles),
        service_roles=[
            AdminAuthServiceRole(service_id=role.service_id, role=role.role)
            for role in service_roles
        ],
    )


@router.post(
    "/bootstrap-admin",
    response_model=AdminAuthCurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_admin(
    request: AdminAuthBootstrapRequest,
    session: Annotated[Session, Depends(get_admin_session)],
    admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> AdminAuthCurrentUserResponse:
    _require_bootstrap_token(admin_token)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    repository.acquire_advisory_xact_lock("admin-bootstrap-system-admin")
    if repository.admin_user_role_exists("system_admin"):
        _raise_conflict("Initial system admin already exists.")
    if repository.get_admin_user_by_email(request.email) is not None:
        _raise_conflict("Admin user already exists.")
    try:
        user = repository.create_admin_user(
            user_id=request.user_id or f"admin_{uuid4().hex}",
            email=request.email,
            display_name=request.display_name,
            password_hash=hash_admin_password(request.password),
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="bootstrap",
            assigned_at=now,
        )
    except IntegrityError:
        session.rollback()
        _raise_conflict("Admin user already exists.")
    session.commit()
    return _current_user_response(
        user,
        global_roles=frozenset({"system_admin"}),
        service_roles=(),
    )


@router.post("/login", response_model=AdminAuthCurrentUserResponse)
def login(
    request: AdminAuthLoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_admin_session)],
) -> AdminAuthCurrentUserResponse:
    repository = IntentRoutingRepository(session)
    user = repository.get_admin_user_by_email(request.email)
    if (
        user is None
        or user.status != "active"
        or not verify_admin_password(request.password, user.password_hash)
    ):
        _raise_authentication_failed()

    now = datetime.now(UTC)
    raw_token = create_admin_session_token()
    repository.create_admin_session(
        session_id=f"ads_{uuid4().hex}",
        user_id=user.user_id,
        token_hash=hash_admin_session_token(raw_token),
        created_at=now,
        expires_at=admin_session_expires_at(days=1),
        revoked_at=None,
        last_seen_at=None,
    )
    repository.update_admin_user_login(user, last_login_at=now)
    session.commit()
    _set_admin_session_cookie(response, raw_token)
    return _current_user_response(
        user,
        global_roles=frozenset(
            role.role for role in repository.list_admin_user_roles(user.user_id)
        ),
        service_roles=tuple(repository.list_service_roles_for_user(user.user_id)),
    )


@router.post("/logout", response_model=AdminAuthSuccessResponse)
def logout(
    response: Response,
    session: Annotated[Session, Depends(get_admin_session)],
    admin_session_token: Annotated[
        str | None,
        Cookie(alias=ADMIN_SESSION_COOKIE_NAME),
    ] = None,
) -> AdminAuthSuccessResponse:
    if admin_session_token is not None and admin_session_token.strip():
        repository = IntentRoutingRepository(session)
        admin_session = repository.get_admin_session_by_token_hash(
            hash_admin_session_token(admin_session_token)
        )
        if admin_session is not None and admin_session.revoked_at is None:
            repository.revoke_admin_session(admin_session, revoked_at=datetime.now(UTC))
            session.commit()
    _clear_admin_session_cookie(response)
    return AdminAuthSuccessResponse(success=True)


@router.get("/me", response_model=AdminAuthCurrentUserResponse)
def me(
    session_context: Annotated[
        AdminSessionContextRecord,
        Depends(require_admin_session_context),
    ],
) -> AdminAuthCurrentUserResponse:
    return _current_user_response(
        session_context.user,
        global_roles=session_context.global_roles,
        service_roles=session_context.service_roles,
    )
