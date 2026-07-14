from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar, cast
from uuid import UUID

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import bindparam, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intent_routing.db import models

ModelT = TypeVar("ModelT")
RawTextKeyIdCounts = dict[str, dict[str, int] | int]

MASKED_RUNTIME_LOG_FIELD_NAMES = (
    "trace_id",
    "request_id",
    "app_id",
    "service_id",
    "release_version",
    "policy_version",
    "intent_catalog_version",
    "decision",
    "intent_id",
    "confidence",
    "margin",
    "threshold_preset",
    "threshold_value",
    "route_key",
    "error_code",
    "error_category",
    "error_layer",
    "http_status",
    "retryable",
    "latency_ms",
    "query_masked",
    "created_at",
)

ADMIN_USER_STATUSES = frozenset({"active", "disabled"})
GLOBAL_ADMIN_ROLES = frozenset({"system_admin"})
SERVICE_ADMIN_ROLES = frozenset(
    {"service_owner", "service_developer", "service_operator", "auditor"}
)
GOVERNED_RESOURCE_TYPES = frozenset(
    {"intent", "example", "release", "runtime_log", "raw_query", "export"}
)
GOVERNED_ACTIONS = frozenset(
    {"request", "approve", "reject", "activate", "rollback", "decrypt", "export"}
)
GOVERNED_REQUEST_STATUSES = frozenset(
    {
        "pending",
        "approved",
        "rejected",
        "activated",
        "rolled_back",
        "token_issued",
        "viewed",
        "expired",
        "completed",
    }
)


@dataclass(frozen=True, slots=True)
class ExampleSearchResult:
    example_id: UUID
    intent_id: str
    example_type: str
    similarity: float


@dataclass(frozen=True, slots=True)
class AdminSessionContextRecord:
    user: models.AdminUser
    admin_session: models.AdminSession
    global_roles: frozenset[str]
    service_roles: tuple[models.UserServiceRole, ...]


@dataclass(frozen=True, slots=True)
class PermissionServiceRoleSummaryRecord:
    service_id: str
    service_display_name: str
    role: str
    assigned_by: str
    assigned_at: datetime


@dataclass(frozen=True, slots=True)
class PermissionAdminUserSummaryRecord:
    user: models.AdminUser
    global_roles: tuple[str, ...]
    is_last_active_system_admin: bool
    organization_user: models.OrganizationUser | None
    service_roles: tuple[PermissionServiceRoleSummaryRecord, ...]
    risk_flags: tuple[str, ...]


def normalize_admin_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise ValueError("admin user email must not be blank")
    return normalized


def _require_allowed_value(value: object, *, field_name: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return value


def _require_nonblank_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


class IntentRoutingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _add_and_flush(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def create_service(self, **values: Any) -> models.Service:
        return self._add_and_flush(models.Service(**values))

    def get_service(self, service_id: str) -> models.Service | None:
        return self.session.get(models.Service, service_id)

    def list_services(self) -> list[models.Service]:
        return list(
            self.session.scalars(
                select(models.Service).order_by(
                    models.Service.service_id,
                    models.Service.display_name,
                )
            )
        )

    def list_services_for_user(self, user_id: str) -> list[models.Service]:
        return list(
            self.session.scalars(
                select(models.Service)
                .join(models.UserServiceRole)
                .where(models.UserServiceRole.user_id == user_id)
                .distinct()
                .order_by(models.Service.service_id, models.Service.display_name)
            )
        )

    def create_api_key(self, **values: Any) -> models.ApiKey:
        return self._add_and_flush(models.ApiKey(**values))

    def get_api_key_by_id(self, key_id: str) -> models.ApiKey | None:
        return self.session.get(models.ApiKey, key_id)

    def create_department(self, **values: Any) -> models.Department:
        return self._add_and_flush(models.Department(**values))

    def list_departments(
        self,
        *,
        query: str | None = None,
        use_yn: str | None = None,
        limit: int = 100,
    ) -> list[models.Department]:
        limit = max(1, min(limit, 100))
        statement = select(models.Department)
        if query is not None and query.strip():
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(models.Department.dept_number).like(pattern),
                    func.lower(models.Department.name).like(pattern),
                )
            )
        if use_yn is not None:
            statement = statement.where(models.Department.use_yn == use_yn)
        return list(
            self.session.scalars(
                statement.order_by(models.Department.dept_number).limit(limit)
            )
        )

    def update_department(
        self,
        department: models.Department,
        **values: Any,
    ) -> models.Department:
        for field_name, value in values.items():
            setattr(department, field_name, value)
        self.session.flush()
        return department

    def deactivate_department(
        self,
        department: models.Department,
        *,
        updated_by: str,
        updated_at: datetime,
    ) -> models.Department:
        department.use_yn = "N"
        department.updated_by = updated_by
        department.updated_at = updated_at
        self.session.flush()
        return department

    def create_organization_user(self, **values: Any) -> models.OrganizationUser:
        return self._add_and_flush(models.OrganizationUser(**values))

    def list_organization_users(
        self,
        *,
        query: str | None = None,
        department_id: UUID | None = None,
        use_yn: str | None = None,
        limit: int = 100,
    ) -> list[models.OrganizationUser]:
        limit = max(1, min(limit, 100))
        statement = select(models.OrganizationUser).join(models.Department)
        if query is not None and query.strip():
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(models.OrganizationUser.user_number).like(pattern),
                    func.lower(models.OrganizationUser.name).like(pattern),
                    func.lower(models.Department.dept_number).like(pattern),
                    func.lower(models.Department.name).like(pattern),
                )
            )
        if department_id is not None:
            statement = statement.where(models.OrganizationUser.department_id == department_id)
        if use_yn is not None:
            statement = statement.where(models.OrganizationUser.use_yn == use_yn)
        return list(
            self.session.scalars(
                statement.order_by(
                    models.Department.dept_number,
                    models.OrganizationUser.user_number,
                ).limit(limit)
            )
        )

    def update_organization_user(
        self,
        organization_user: models.OrganizationUser,
        **values: Any,
    ) -> models.OrganizationUser:
        for field_name, value in values.items():
            setattr(organization_user, field_name, value)
        self.session.flush()
        return organization_user

    def deactivate_organization_user(
        self,
        organization_user: models.OrganizationUser,
        *,
        updated_by: str,
        updated_at: datetime,
    ) -> models.OrganizationUser:
        organization_user.use_yn = "N"
        organization_user.updated_by = updated_by
        organization_user.updated_at = updated_at
        self.session.flush()
        return organization_user

    def list_api_keys(
        self,
        *,
        service_id: str | None = None,
        environment: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[models.ApiKey]:
        statement = select(models.ApiKey)
        if service_id is not None:
            statement = statement.where(models.ApiKey.service_id == service_id)
        if environment is not None:
            statement = statement.where(models.ApiKey.environment == environment)
        if status is not None:
            statement = statement.where(models.ApiKey.status == status)
        return list(
            self.session.scalars(
                statement.order_by(
                    models.ApiKey.created_at.desc(),
                    models.ApiKey.key_id,
                ).limit(limit)
            )
        )

    def create_admin_user(self, **values: Any) -> models.AdminUser:
        values = dict(values)
        email = values.get("email")
        if not isinstance(email, str):
            raise ValueError("admin user email must be provided")
        values["email"] = email.strip()
        values["email_normalized"] = normalize_admin_email(email)
        values["status"] = _require_allowed_value(
            values.get("status", "active"),
            field_name="admin user status",
            allowed=ADMIN_USER_STATUSES,
        )
        return self._add_and_flush(models.AdminUser(**values))

    def get_admin_user(self, user_id: str) -> models.AdminUser | None:
        return self.session.get(models.AdminUser, user_id)

    def get_admin_user_by_email(self, email: str) -> models.AdminUser | None:
        email_normalized = normalize_admin_email(email)
        return self.session.scalar(
            select(models.AdminUser).where(
                models.AdminUser.email_normalized == email_normalized
            )
        )

    def get_login_eligible_admin_user_by_email(
        self,
        email: str,
    ) -> models.AdminUser | None:
        email_normalized = normalize_admin_email(email)
        return self.session.scalar(
            select(models.AdminUser)
            .outerjoin(models.OrganizationUser)
            .where(models.AdminUser.email_normalized == email_normalized)
            .where(models.AdminUser.status == "active")
            .where(
                or_(
                    models.AdminUser.organization_user_id.is_(None),
                    models.OrganizationUser.use_yn == "Y",
                )
            )
        )

    def list_admin_users(
        self,
        query: str | None = None,
        limit: int = 25,
    ) -> list[models.AdminUser]:
        limit = max(1, min(limit, 25))
        statement = select(models.AdminUser)
        if query is not None and query.strip():
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(models.AdminUser.email_normalized).like(pattern),
                    func.lower(models.AdminUser.email).like(pattern),
                    func.lower(models.AdminUser.display_name).like(pattern),
                    func.lower(models.AdminUser.user_id).like(pattern),
                )
            )
        return list(
            self.session.scalars(
                statement.order_by(
                    models.AdminUser.email_normalized,
                    models.AdminUser.user_id,
                ).limit(limit)
            )
        )

    def list_managed_admin_users(
        self,
        *,
        organization_user_id: UUID | None = None,
        query: str | None = None,
        limit: int = 25,
    ) -> list[models.AdminUser]:
        limit = max(1, min(limit, 25))
        statement = select(models.AdminUser)
        if organization_user_id is not None:
            statement = statement.where(
                models.AdminUser.organization_user_id == organization_user_id
            )
        if query is not None and query.strip():
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(models.AdminUser.email_normalized).like(pattern),
                    func.lower(models.AdminUser.email).like(pattern),
                    func.lower(models.AdminUser.display_name).like(pattern),
                    func.lower(models.AdminUser.user_id).like(pattern),
                )
            )
        return list(
            self.session.scalars(
                statement.order_by(
                    models.AdminUser.email_normalized,
                    models.AdminUser.user_id,
                ).limit(limit)
            )
        )

    def list_permission_admin_user_summaries(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        global_role: str | None = None,
        organization_link: str | None = None,
        organization_use_yn: str | None = None,
        limit: int = 100,
    ) -> list[PermissionAdminUserSummaryRecord]:
        limit = max(1, min(limit, 200))
        if status is not None:
            status = _require_allowed_value(
                status,
                field_name="admin user status",
                allowed=ADMIN_USER_STATUSES,
            )
        if global_role is not None:
            global_role = _require_allowed_value(
                global_role,
                field_name="admin user role",
                allowed=GLOBAL_ADMIN_ROLES,
            )
        if organization_link is not None:
            organization_link = _require_allowed_value(
                organization_link,
                field_name="organization link",
                allowed=frozenset({"linked", "unlinked"}),
            )
        if organization_use_yn is not None:
            organization_use_yn = _require_allowed_value(
                organization_use_yn,
                field_name="organization user use_yn",
                allowed=frozenset({"Y", "N"}),
            )

        statement = (
            select(models.AdminUser)
            .outerjoin(models.AdminUser.organization_user)
            .outerjoin(models.OrganizationUser.department)
        )
        if query is not None and query.strip():
            pattern = f"%{query.strip().lower()}%"
            service_match_user_ids = (
                select(models.UserServiceRole.user_id)
                .join(models.Service)
                .where(
                    or_(
                        func.lower(models.UserServiceRole.service_id).like(pattern),
                        func.lower(models.Service.display_name).like(pattern),
                    )
                )
            )
            statement = statement.where(
                or_(
                    func.lower(models.AdminUser.email_normalized).like(pattern),
                    func.lower(models.AdminUser.email).like(pattern),
                    func.lower(models.AdminUser.display_name).like(pattern),
                    func.lower(models.AdminUser.user_id).like(pattern),
                    func.lower(models.OrganizationUser.user_number).like(pattern),
                    func.lower(models.OrganizationUser.name).like(pattern),
                    func.lower(models.Department.dept_number).like(pattern),
                    func.lower(models.Department.name).like(pattern),
                    models.AdminUser.user_id.in_(service_match_user_ids),
                )
            )
        if status is not None:
            statement = statement.where(models.AdminUser.status == status)
        if global_role is not None:
            role_user_ids = select(models.AdminUserRole.user_id).where(
                models.AdminUserRole.role == global_role
            )
            statement = statement.where(models.AdminUser.user_id.in_(role_user_ids))
        if organization_link == "linked":
            statement = statement.where(
                models.AdminUser.organization_user_id.is_not(None)
            )
        elif organization_link == "unlinked":
            statement = statement.where(models.AdminUser.organization_user_id.is_(None))
        if organization_use_yn is not None:
            statement = statement.where(
                models.OrganizationUser.use_yn == organization_use_yn
            )

        users = list(
            self.session.scalars(
                statement.order_by(
                    models.AdminUser.email_normalized,
                    models.AdminUser.user_id,
                ).limit(limit)
            )
        )
        user_ids = [user.user_id for user in users]
        if not user_ids:
            return []

        global_roles_by_user_id: dict[str, list[str]] = {
            user_id: [] for user_id in user_ids
        }
        for role_record in self.session.scalars(
            select(models.AdminUserRole)
            .where(models.AdminUserRole.user_id.in_(user_ids))
            .order_by(models.AdminUserRole.user_id, models.AdminUserRole.role)
        ):
            global_roles_by_user_id.setdefault(role_record.user_id, []).append(
                role_record.role
            )

        service_roles_by_user_id: dict[
            str,
            list[PermissionServiceRoleSummaryRecord],
        ] = {user_id: [] for user_id in user_ids}
        for role_record in self.session.scalars(
            select(models.UserServiceRole)
            .join(models.Service)
            .where(models.UserServiceRole.user_id.in_(user_ids))
            .order_by(
                models.UserServiceRole.user_id,
                models.Service.display_name,
                models.UserServiceRole.service_id,
                models.UserServiceRole.role,
            )
        ):
            service_roles_by_user_id.setdefault(role_record.user_id, []).append(
                PermissionServiceRoleSummaryRecord(
                    service_id=role_record.service_id,
                    service_display_name=role_record.service.display_name,
                    role=role_record.role,
                    assigned_by=role_record.assigned_by,
                    assigned_at=role_record.assigned_at,
                )
            )

        active_system_admin_count = self.count_login_eligible_admin_users_with_role(
            "system_admin"
        )
        return [
            self._permission_admin_user_summary_record(
                user,
                global_roles=tuple(sorted(global_roles_by_user_id[user.user_id])),
                service_roles=tuple(service_roles_by_user_id[user.user_id]),
                active_system_admin_count=active_system_admin_count,
            )
            for user in users
        ]

    def _permission_admin_user_summary_record(
        self,
        user: models.AdminUser,
        *,
        global_roles: tuple[str, ...],
        service_roles: tuple[PermissionServiceRoleSummaryRecord, ...],
        active_system_admin_count: int,
    ) -> PermissionAdminUserSummaryRecord:
        organization_user = user.organization_user
        is_login_eligible_system_admin = (
            user.status == "active"
            and "system_admin" in global_roles
            and (
                user.organization_user_id is None
                or (organization_user is not None and organization_user.use_yn == "Y")
            )
        )
        is_last_active_system_admin = (
            is_login_eligible_system_admin and active_system_admin_count == 1
        )

        risk_flags: list[str] = []
        if organization_user is not None and organization_user.use_yn != "Y":
            risk_flags.append("linked_inactive_organization_user")
        if user.status == "disabled" and service_roles:
            risk_flags.append("disabled_admin_has_service_roles")
        if user.status == "active" and not global_roles and not service_roles:
            risk_flags.append("active_admin_without_roles")
        if user.organization_user_id is None:
            risk_flags.append("unlinked_admin_user")
        if is_last_active_system_admin:
            risk_flags.append("single_active_system_admin")

        return PermissionAdminUserSummaryRecord(
            user=user,
            global_roles=global_roles,
            is_last_active_system_admin=is_last_active_system_admin,
            organization_user=organization_user,
            service_roles=service_roles,
            risk_flags=tuple(risk_flags),
        )

    def get_admin_user_by_organization_user_id(
        self,
        organization_user_id: UUID,
    ) -> models.AdminUser | None:
        return self.session.scalar(
            select(models.AdminUser).where(
                models.AdminUser.organization_user_id == organization_user_id
            )
        )

    def update_admin_user(
        self,
        user: models.AdminUser,
        **values: Any,
    ) -> models.AdminUser:
        if "email" in values:
            email = values["email"]
            if not isinstance(email, str):
                raise ValueError("admin user email must be provided")
            user.email = email.strip()
            user.email_normalized = normalize_admin_email(email)
        if "display_name" in values:
            user.display_name = _require_nonblank_string(
                values["display_name"],
                field_name="admin user display_name",
            ).strip()
        if "status" in values:
            user.status = _require_allowed_value(
                values["status"],
                field_name="admin user status",
                allowed=ADMIN_USER_STATUSES,
            )
        if "updated_at" in values:
            user.updated_at = values["updated_at"]
        self.session.flush()
        return user

    def update_admin_user_login(
        self,
        user: models.AdminUser,
        *,
        last_login_at: datetime,
    ) -> models.AdminUser:
        user.last_login_at = last_login_at
        user.updated_at = last_login_at
        self.session.flush()
        return user

    def update_admin_user_password(
        self,
        user: models.AdminUser,
        *,
        password_hash: str,
        updated_at: datetime,
    ) -> models.AdminUser:
        if not password_hash.strip():
            raise ValueError("admin user password_hash must not be blank")
        user.password_hash = password_hash
        user.updated_at = updated_at
        self.session.flush()
        return user

    def assign_admin_user_role(self, **values: Any) -> models.AdminUserRole:
        values = dict(values)
        values["role"] = _require_allowed_value(
            values.get("role"),
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        return self._add_and_flush(models.AdminUserRole(**values))

    def ensure_admin_user_role(self, **values: Any) -> models.AdminUserRole:
        user_id = values.get("user_id")
        role = _require_allowed_value(
            values.get("role"),
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("admin user role user_id must be provided")
        existing = self.session.get(models.AdminUserRole, (user_id, role))
        if existing is not None:
            return existing
        return self.assign_admin_user_role(**values)

    def admin_user_role_exists(self, role: str) -> bool:
        role = _require_allowed_value(
            role,
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        return (
            self.session.scalar(
                select(models.AdminUserRole.user_id)
                .where(models.AdminUserRole.role == role)
                .limit(1)
            )
            is not None
        )

    def list_admin_user_roles(self, user_id: str) -> list[models.AdminUserRole]:
        return list(
            self.session.scalars(
                select(models.AdminUserRole)
                .where(models.AdminUserRole.user_id == user_id)
                .order_by(models.AdminUserRole.role)
            )
        )

    def delete_admin_user_role_by_key(
        self,
        user_id: str,
        role: str,
    ) -> models.AdminUserRole | None:
        role = _require_allowed_value(
            role,
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        role_record = self.session.get(models.AdminUserRole, (user_id, role))
        if role_record is None:
            return None
        self.session.delete(role_record)
        self.session.flush()
        return role_record

    def count_login_eligible_admin_users_with_role(self, role: str) -> int:
        role = _require_allowed_value(
            role,
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        count = self.session.scalar(
            select(func.count())
            .select_from(models.AdminUserRole)
            .join(models.AdminUser)
            .outerjoin(models.OrganizationUser)
            .where(models.AdminUserRole.role == role)
            .where(models.AdminUser.status == "active")
            .where(
                or_(
                    models.AdminUser.organization_user_id.is_(None),
                    models.OrganizationUser.use_yn == "Y",
                )
            )
        )
        return int(count or 0)

    def create_admin_session(self, **values: Any) -> models.AdminSession:
        return self._add_and_flush(models.AdminSession(**values))

    def get_admin_session_by_token_hash(
        self,
        token_hash: str,
    ) -> models.AdminSession | None:
        return self.session.scalar(
            select(models.AdminSession).where(
                models.AdminSession.token_hash == token_hash
            )
        )

    def get_active_admin_session_context(
        self,
        token_hash: str,
        *,
        now: datetime,
    ) -> AdminSessionContextRecord | None:
        if not token_hash.strip():
            return None
        admin_session = self.session.scalar(
            select(models.AdminSession)
            .join(models.AdminUser)
            .outerjoin(models.OrganizationUser)
            .where(models.AdminSession.token_hash == token_hash)
            .where(models.AdminSession.revoked_at.is_(None))
            .where(models.AdminSession.expires_at > now)
            .where(models.AdminUser.status == "active")
            .where(
                or_(
                    models.AdminUser.organization_user_id.is_(None),
                    models.OrganizationUser.use_yn == "Y",
                )
            )
        )
        if admin_session is None:
            return None

        admin_session.last_seen_at = now
        self.session.flush()
        return AdminSessionContextRecord(
            user=admin_session.user,
            admin_session=admin_session,
            global_roles=frozenset(
                role.role for role in self.list_admin_user_roles(admin_session.user_id)
            ),
            service_roles=tuple(
                self.list_service_roles_for_user(admin_session.user_id)
            ),
        )

    def revoke_admin_session(
        self,
        admin_session: models.AdminSession,
        *,
        revoked_at: datetime,
    ) -> models.AdminSession:
        admin_session.revoked_at = revoked_at
        self.session.flush()
        return admin_session

    def assign_user_service_role(self, **values: Any) -> models.UserServiceRole:
        values = dict(values)
        values["role"] = _require_allowed_value(
            values.get("role"),
            field_name="user service role",
            allowed=SERVICE_ADMIN_ROLES,
        )
        return self._add_and_flush(models.UserServiceRole(**values))

    def ensure_user_service_role(self, **values: Any) -> models.UserServiceRole:
        role_record, _created = self.ensure_user_service_role_with_created(**values)
        return role_record

    def ensure_user_service_role_with_created(
        self,
        **values: Any,
    ) -> tuple[models.UserServiceRole, bool]:
        user_id = _require_nonblank_string(
            values.get("user_id"),
            field_name="user service role user_id",
        )
        service_id = _require_nonblank_string(
            values.get("service_id"),
            field_name="user service role service_id",
        )
        role = _require_allowed_value(
            values.get("role"),
            field_name="user service role",
            allowed=SERVICE_ADMIN_ROLES,
        )
        existing = self.get_user_service_role(user_id, service_id, role)
        if existing is not None:
            return existing, False
        try:
            with self.session.begin_nested():
                return self.assign_user_service_role(**values), True
        except IntegrityError:
            existing = self.get_user_service_role(user_id, service_id, role)
            if existing is None:
                raise
            return existing, False

    def get_user_service_role(
        self,
        user_id: str,
        service_id: str,
        role: str,
    ) -> models.UserServiceRole | None:
        role = _require_allowed_value(
            role,
            field_name="user service role",
            allowed=SERVICE_ADMIN_ROLES,
        )
        return self.session.get(models.UserServiceRole, (user_id, service_id, role))

    def delete_user_service_role(self, role_record: models.UserServiceRole) -> None:
        self.session.delete(role_record)
        self.session.flush()

    def delete_user_service_role_by_key(
        self,
        user_id: str,
        service_id: str,
        role: str,
    ) -> models.UserServiceRole | None:
        role = _require_allowed_value(
            role,
            field_name="user service role",
            allowed=SERVICE_ADMIN_ROLES,
        )
        role_record = self.session.scalar(
            select(models.UserServiceRole)
            .where(models.UserServiceRole.user_id == user_id)
            .where(models.UserServiceRole.service_id == service_id)
            .where(models.UserServiceRole.role == role)
            .with_for_update()
        )
        if role_record is None:
            return None
        self.session.delete(role_record)
        self.session.flush()
        return role_record

    def list_user_service_roles(
        self,
        user_id: str,
        service_id: str,
    ) -> list[models.UserServiceRole]:
        return list(
            self.session.scalars(
                select(models.UserServiceRole)
                .where(models.UserServiceRole.user_id == user_id)
                .where(models.UserServiceRole.service_id == service_id)
                .order_by(models.UserServiceRole.role)
            )
        )

    def list_service_member_roles(self, service_id: str) -> list[models.UserServiceRole]:
        return list(
            self.session.scalars(
                select(models.UserServiceRole)
                .join(models.AdminUser)
                .where(models.UserServiceRole.service_id == service_id)
                .order_by(
                    models.AdminUser.email_normalized,
                    models.UserServiceRole.role,
                    models.UserServiceRole.user_id,
                )
            )
        )

    def list_service_roles_for_user(self, user_id: str) -> list[models.UserServiceRole]:
        return list(
            self.session.scalars(
                select(models.UserServiceRole)
                .where(models.UserServiceRole.user_id == user_id)
                .order_by(models.UserServiceRole.service_id, models.UserServiceRole.role)
            )
        )

    def create_governed_action_request(
        self,
        **values: Any,
    ) -> models.GovernedActionRequest:
        values = dict(values)
        values["resource_type"] = _require_allowed_value(
            values.get("resource_type"),
            field_name="governed resource type",
            allowed=GOVERNED_RESOURCE_TYPES,
        )
        values["action"] = _require_allowed_value(
            values.get("action"),
            field_name="governed action",
            allowed=GOVERNED_ACTIONS,
        )
        values["status"] = _require_allowed_value(
            values.get("status", "pending"),
            field_name="governed request status",
            allowed=GOVERNED_REQUEST_STATUSES,
        )
        values["resource_id"] = _require_nonblank_string(
            values.get("resource_id"),
            field_name="governed resource id",
        )
        values["requested_by"] = _require_nonblank_string(
            values.get("requested_by"),
            field_name="governed request requester",
        )
        values["reason"] = _require_nonblank_string(
            values.get("reason"),
            field_name="governed request reason",
        )
        values.setdefault("decided_by", None)
        values.setdefault("decided_at", None)
        values.setdefault("decision_reason", None)
        return self._add_and_flush(models.GovernedActionRequest(**values))

    def get_governed_action_request(
        self,
        request_id: str,
    ) -> models.GovernedActionRequest | None:
        return self.session.get(models.GovernedActionRequest, request_id)

    def list_governed_action_requests(
        self,
        *,
        service_id: str,
        status: str | None = None,
        resource_type: str | None = None,
        limit: int = 50,
    ) -> list[models.GovernedActionRequest]:
        statement = select(models.GovernedActionRequest).where(
            models.GovernedActionRequest.service_id == service_id
        )
        if status is not None:
            status = _require_allowed_value(
                status,
                field_name="governed request status",
                allowed=GOVERNED_REQUEST_STATUSES,
            )
            statement = statement.where(models.GovernedActionRequest.status == status)
        if resource_type is not None:
            resource_type = _require_allowed_value(
                resource_type,
                field_name="governed resource type",
                allowed=GOVERNED_RESOURCE_TYPES,
            )
            statement = statement.where(models.GovernedActionRequest.resource_type == resource_type)
        return list(
            self.session.scalars(
                statement.order_by(
                    models.GovernedActionRequest.requested_at.desc(),
                    models.GovernedActionRequest.request_id,
                ).limit(limit)
            )
        )

    def approve_governed_action_request(
        self,
        request: models.GovernedActionRequest,
        *,
        decided_by: str,
        decided_at: datetime,
        reason: str | None = None,
    ) -> models.GovernedActionRequest:
        self._require_pending_governed_request(request)
        decided_by = _require_nonblank_string(
            decided_by,
            field_name="governed request decision actor",
        )
        if request.requested_by == decided_by:
            raise ValueError("request author cannot approve own request")
        request.status = "approved"
        request.decided_by = decided_by
        request.decided_at = decided_at
        request.decision_reason = reason
        self.session.flush()
        return request

    def reject_governed_action_request(
        self,
        request: models.GovernedActionRequest,
        *,
        decided_by: str,
        decided_at: datetime,
        reason: str,
    ) -> models.GovernedActionRequest:
        self._require_pending_governed_request(request)
        decided_by = _require_nonblank_string(
            decided_by,
            field_name="governed request decision actor",
        )
        if request.requested_by == decided_by:
            raise ValueError("request author cannot reject own request")
        request.status = "rejected"
        request.decided_by = decided_by
        request.decided_at = decided_at
        request.decision_reason = _require_nonblank_string(
            reason,
            field_name="governed request rejection reason",
        )
        self.session.flush()
        return request

    def issue_raw_query_view_token(
        self,
        request: models.GovernedActionRequest,
        *,
        token_id: str,
        token_hash: str,
        expires_at: datetime,
        issued_by: str,
        issued_at: datetime,
    ) -> models.RawQueryViewToken:
        if request.resource_type != "raw_query" or request.action != "decrypt":
            raise ValueError("raw query view token requires a raw_query decrypt request")
        if request.status != "approved":
            raise ValueError("raw query view request must be approved before token issue")
        token_hash = _require_nonblank_string(
            token_hash,
            field_name="raw query view token hash",
        )
        if expires_at <= issued_at:
            raise ValueError("raw query view token expiry must be after issue time")
        request.status = "token_issued"
        token = models.RawQueryViewToken(
            token_id=token_id,
            request_id=request.request_id,
            service_id=request.service_id,
            trace_id=request.resource_id,
            token_hash=token_hash,
            expires_at=expires_at,
            issued_by=_require_nonblank_string(
                issued_by,
                field_name="raw query view token issuer",
            ),
            issued_at=issued_at,
            viewed_at=None,
            expired_at=None,
        )
        self.session.add(token)
        self.session.flush()
        return token

    def consume_raw_query_view_token(
        self,
        *,
        token_hash: str,
        service_id: str,
        trace_id: str,
        consumed_at: datetime,
    ) -> models.RawQueryViewToken | None:
        token = self.session.scalar(
            select(models.RawQueryViewToken)
            .join(models.GovernedActionRequest)
            .where(models.RawQueryViewToken.token_hash == token_hash)
            .where(models.RawQueryViewToken.service_id == service_id)
            .where(models.RawQueryViewToken.trace_id == trace_id)
            .where(models.RawQueryViewToken.expires_at > consumed_at)
            .where(models.RawQueryViewToken.viewed_at.is_(None))
            .where(models.RawQueryViewToken.expired_at.is_(None))
            .where(models.GovernedActionRequest.status == "token_issued")
            .with_for_update()
        )
        if token is None:
            return None
        token.viewed_at = consumed_at
        token.request.status = "viewed"
        self.session.flush()
        return token

    def expire_raw_query_view_token(
        self,
        *,
        token_hash: str,
        service_id: str,
        trace_id: str,
        expired_at: datetime,
    ) -> models.RawQueryViewToken | None:
        token = self.session.scalar(
            select(models.RawQueryViewToken)
            .join(models.GovernedActionRequest)
            .where(models.RawQueryViewToken.token_hash == token_hash)
            .where(models.RawQueryViewToken.service_id == service_id)
            .where(models.RawQueryViewToken.trace_id == trace_id)
            .where(models.RawQueryViewToken.expires_at <= expired_at)
            .where(models.RawQueryViewToken.viewed_at.is_(None))
            .where(models.RawQueryViewToken.expired_at.is_(None))
            .where(models.GovernedActionRequest.status == "token_issued")
            .with_for_update()
        )
        if token is None:
            return None
        token.expired_at = expired_at
        token.request.status = "expired"
        self.session.flush()
        return token

    def get_valid_raw_query_view_token(
        self,
        *,
        token_hash: str,
        service_id: str,
        trace_id: str,
        now: datetime,
    ) -> models.RawQueryViewToken | None:
        return self.session.scalar(
            select(models.RawQueryViewToken)
            .join(models.GovernedActionRequest)
            .where(models.RawQueryViewToken.token_hash == token_hash)
            .where(models.RawQueryViewToken.service_id == service_id)
            .where(models.RawQueryViewToken.trace_id == trace_id)
            .where(models.RawQueryViewToken.expires_at > now)
            .where(models.RawQueryViewToken.viewed_at.is_(None))
            .where(models.RawQueryViewToken.expired_at.is_(None))
            .where(models.GovernedActionRequest.status == "token_issued")
        )

    def mark_raw_query_view_token_viewed(
        self,
        token: models.RawQueryViewToken,
        *,
        viewed_at: datetime,
    ) -> models.RawQueryViewToken:
        token.viewed_at = viewed_at
        token.request.status = "viewed"
        self.session.flush()
        return token

    def expire_raw_query_view_tokens(
        self,
        *,
        now: datetime,
    ) -> list[models.RawQueryViewToken]:
        tokens = list(
            self.session.scalars(
                select(models.RawQueryViewToken)
                .join(models.GovernedActionRequest)
                .where(models.RawQueryViewToken.expires_at <= now)
                .where(models.RawQueryViewToken.expired_at.is_(None))
            )
        )
        for token in tokens:
            token.expired_at = now
            if token.request.status == "token_issued":
                token.request.status = "expired"
        self.session.flush()
        return tokens

    def _require_pending_governed_request(
        self,
        request: models.GovernedActionRequest,
    ) -> None:
        if request.status != "pending":
            raise ValueError("governed request must be pending")

    def revoke_api_key(
        self,
        api_key: models.ApiKey,
        *,
        revoked_at: datetime,
    ) -> models.ApiKey:
        api_key.status = "revoked"
        api_key.revoked_at = revoked_at
        self.session.flush()
        return api_key

    def create_intent(self, **values: Any) -> models.Intent:
        return self._add_and_flush(models.Intent(**values))

    def get_intent(self, service_id: str, intent_id: str) -> models.Intent | None:
        return self.session.scalar(
            select(models.Intent)
            .where(models.Intent.service_id == service_id)
            .where(models.Intent.intent_id == intent_id)
        )

    def list_intents(self, service_id: str) -> list[models.Intent]:
        return list(
            self.session.scalars(
                select(models.Intent)
                .where(models.Intent.service_id == service_id)
                .order_by(models.Intent.intent_id)
            )
        )

    def list_active_intents(self, service_id: str) -> list[models.Intent]:
        return list(
            self.session.scalars(
                select(models.Intent)
                .where(models.Intent.service_id == service_id)
                .where(models.Intent.status == "active")
                .order_by(models.Intent.intent_id)
            )
        )

    def update_intent(self, intent: models.Intent, **values: Any) -> models.Intent:
        for key, value in values.items():
            setattr(intent, key, value)
        self.session.flush()
        return intent

    def create_example(self, **values: Any) -> models.IntentExample:
        return self._add_and_flush(models.IntentExample(**values))

    def get_example(
        self,
        service_id: str,
        example_id: UUID,
    ) -> models.IntentExample | None:
        return self.session.scalar(
            select(models.IntentExample)
            .where(models.IntentExample.service_id == service_id)
            .where(models.IntentExample.example_id == example_id)
        )

    def list_examples(self, service_id: str, intent_id: str) -> list[models.IntentExample]:
        return list(
            self.session.scalars(
                select(models.IntentExample)
                .where(models.IntentExample.service_id == service_id)
                .where(models.IntentExample.intent_id == intent_id)
                .order_by(models.IntentExample.created_at, models.IntentExample.example_id)
            )
        )

    def list_approved_examples(
        self,
        service_id: str,
        intent_id: str,
    ) -> list[models.IntentExample]:
        return list(
            self.session.scalars(
                select(models.IntentExample)
                .where(models.IntentExample.service_id == service_id)
                .where(models.IntentExample.intent_id == intent_id)
                .where(models.IntentExample.approved.is_(True))
                .order_by(models.IntentExample.created_at, models.IntentExample.example_id)
            )
        )

    def approve_example(
        self,
        example: models.IntentExample,
        *,
        embedding: list[float] | None = None,
    ) -> models.IntentExample:
        example.approved = True
        if embedding is not None:
            example.embedding = embedding
        self.session.flush()
        return example

    def search_approved_examples_by_embedding(
        self,
        service_id: str,
        query_embedding: list[float],
        *,
        limit: int,
    ) -> list[ExampleSearchResult]:
        if len(query_embedding) != 1024:
            raise ValueError("query_embedding must have 1024 dimensions")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        statement = text(
            """
            SELECT example_id,
                   intent_id,
                   example_type,
                   1 - (embedding <=> :query_embedding) AS similarity
            FROM intent_examples
            WHERE service_id = :service_id
              AND approved = true
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :query_embedding
            LIMIT :limit
            """
        ).bindparams(bindparam("query_embedding", type_=Vector(1024)))
        rows = self.session.execute(
            statement,
            {
                "service_id": service_id,
                "query_embedding": query_embedding,
                "limit": limit,
            },
        ).mappings()
        return [
            ExampleSearchResult(
                example_id=row["example_id"],
                intent_id=row["intent_id"],
                example_type=row["example_type"],
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]

    def create_policy_version(self, **values: Any) -> models.PolicyVersion:
        return self._add_and_flush(models.PolicyVersion(**values))

    def get_policy_version(
        self,
        service_id: str,
        policy_version: str,
    ) -> models.PolicyVersion | None:
        return self.session.scalar(
            select(models.PolicyVersion)
            .where(models.PolicyVersion.service_id == service_id)
            .where(models.PolicyVersion.policy_version == policy_version)
        )

    def list_policy_versions(
        self,
        service_id: str,
        *,
        limit: int = 50,
    ) -> list[models.PolicyVersion]:
        return list(
            self.session.scalars(
                select(models.PolicyVersion)
                .where(models.PolicyVersion.service_id == service_id)
                .order_by(
                    models.PolicyVersion.created_at.desc(),
                    models.PolicyVersion.policy_version,
                )
                .limit(limit)
            )
        )

    def create_catalog_version(self, **values: Any) -> models.IntentCatalogVersion:
        return self._add_and_flush(models.IntentCatalogVersion(**values))

    def get_catalog_version(
        self,
        service_id: str,
        intent_catalog_version: str,
    ) -> models.IntentCatalogVersion | None:
        return self.session.scalar(
            select(models.IntentCatalogVersion)
            .where(models.IntentCatalogVersion.service_id == service_id)
            .where(
                models.IntentCatalogVersion.intent_catalog_version
                == intent_catalog_version
            )
        )

    def list_catalog_versions(
        self,
        service_id: str,
        *,
        limit: int = 50,
    ) -> list[models.IntentCatalogVersion]:
        return list(
            self.session.scalars(
                select(models.IntentCatalogVersion)
                .where(models.IntentCatalogVersion.service_id == service_id)
                .order_by(
                    models.IntentCatalogVersion.created_at.desc(),
                    models.IntentCatalogVersion.intent_catalog_version,
                )
                .limit(limit)
            )
        )

    def create_test_dataset(
        self,
        dataset_values: dict[str, Any],
        cases: Iterable[dict[str, Any]] = (),
    ) -> models.TestDataset:
        test_dataset_version = dataset_values["test_dataset_version"]
        dataset = models.TestDataset(**dataset_values)
        self.session.add(dataset)
        self.session.flush()
        for case_values in cases:
            normalized_case_values = dict(case_values)
            case_dataset_version = normalized_case_values.setdefault(
                "test_dataset_version",
                test_dataset_version,
            )
            if case_dataset_version != test_dataset_version:
                raise ValueError("case test_dataset_version must match dataset")
            self.session.add(models.TestCase(**normalized_case_values))
        self.session.flush()
        return dataset

    def create_test_run_with_results(
        self,
        test_run_values: dict[str, Any],
        results: Iterable[dict[str, Any]],
    ) -> models.TestRun:
        test_run = models.TestRun(**test_run_values)
        self.session.add(test_run)
        self.session.flush()
        for result_values in results:
            self.session.add(
                models.TestResult(test_run_id=test_run.test_run_id, **result_values)
            )
        self.session.flush()
        return test_run

    def get_test_run(self, test_run_id: str) -> models.TestRun | None:
        return self.session.get(models.TestRun, test_run_id)

    def list_test_runs(
        self,
        service_id: str,
        *,
        gate_passed: bool | None = None,
        risk_passed: bool | None = None,
        limit: int = 50,
    ) -> list[tuple[models.TestRun, models.TestDataset]]:
        statement = (
            select(models.TestRun, models.TestDataset)
            .join(
                models.TestDataset,
                models.TestDataset.test_dataset_version
                == models.TestRun.test_dataset_version,
            )
            .where(models.TestRun.service_id == service_id)
        )
        if gate_passed is not None:
            statement = statement.where(models.TestRun.gate_passed.is_(gate_passed))
        if risk_passed is True:
            statement = statement.where(models.TestRun.risk_pass_rate == 1)
        if risk_passed is False:
            statement = statement.where(models.TestRun.risk_pass_rate != 1)
        rows = self.session.execute(
            statement.order_by(
                models.TestRun.created_at.desc(),
                models.TestRun.test_run_id,
            ).limit(limit)
        ).all()
        return [(test_run, dataset) for test_run, dataset in rows]

    def list_test_results(self, test_run_id: str) -> list[models.TestResult]:
        return list(
            self.session.scalars(
                select(models.TestResult)
                .where(models.TestResult.test_run_id == test_run_id)
                .order_by(models.TestResult.case_id)
            )
        )

    def create_release(self, **values: Any) -> models.Release:
        return self._add_and_flush(models.Release(**values))

    def acquire_advisory_xact_lock(self, lock_key: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key)::bigint)"),
            {"lock_key": lock_key},
        )

    def create_vector_index_version(self, **values: Any) -> models.VectorIndexVersion:
        return self._add_and_flush(models.VectorIndexVersion(**values))

    def list_vector_index_versions_by_prefix(self, prefix: str) -> list[str]:
        return list(
            self.session.scalars(
                select(models.VectorIndexVersion.vector_index_version)
                .where(
                    models.VectorIndexVersion.vector_index_version.startswith(
                        prefix,
                        autoescape=True,
                    )
                )
                .order_by(models.VectorIndexVersion.vector_index_version)
            )
        )

    def get_release(
        self,
        service_id: str,
        release_version: str,
    ) -> models.Release | None:
        return self.session.scalar(
            select(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.release_version == release_version)
        )

    def list_releases(
        self,
        service_id: str,
        environment: str | None = None,
    ) -> list[models.Release]:
        statement = select(models.Release).where(models.Release.service_id == service_id)
        if environment is not None:
            statement = statement.where(models.Release.environment == environment)
        return list(
            self.session.scalars(
                statement.order_by(
                    models.Release.released_at.desc(),
                    models.Release.release_version,
                )
            )
        )

    def list_release_versions_by_prefix(
        self,
        service_id: str,
        prefix: str,
    ) -> list[str]:
        return list(
            self.session.scalars(
                select(models.Release.release_version)
                .where(models.Release.service_id == service_id)
                .where(
                    models.Release.release_version.startswith(
                        prefix,
                        autoescape=True,
                    )
                )
                .order_by(models.Release.release_version)
            )
        )

    def get_active_release(self, service_id: str, environment: str) -> models.Release | None:
        return self.session.scalar(
            select(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.environment == environment)
            .where(models.Release.active.is_(True))
            .order_by(models.Release.released_at.desc())
        )

    def set_active_release(self, service_id: str, environment: str, release_version: str) -> None:
        target_release = self.session.scalar(
            select(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.environment == environment)
            .where(models.Release.release_version == release_version)
        )
        if target_release is None:
            raise ValueError("release_version does not match service_id and environment")

        self.session.execute(
            update(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.environment == environment)
            .values(active=False)
        )
        target_release.active = True
        self.session.flush()

    def insert_runtime_log(self, **values: Any) -> models.RuntimeLog:
        return self._add_and_flush(models.RuntimeLog(**values))

    def create_raw_text_rewrap_run(self, **values: Any) -> models.RawTextRewrapRun:
        return self._add_and_flush(models.RawTextRewrapRun(**values))

    def complete_raw_text_rewrap_run(
        self,
        run: models.RawTextRewrapRun,
        **values: Any,
    ) -> models.RawTextRewrapRun:
        for key, value in values.items():
            setattr(run, key, value)
        self.session.flush()
        return run

    def list_intent_examples_for_rewrap(
        self,
        service_id: str,
        key_ids: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[models.IntentExample]:
        statement = select(models.IntentExample).where(
            models.IntentExample.service_id == service_id
        )
        if key_ids is not None:
            key_id_values = tuple(key_ids)
            if not key_id_values:
                return []
            statement = statement.where(models.IntentExample.text_raw_key_id.in_(key_id_values))
        statement = statement.order_by(
            models.IntentExample.created_at,
            models.IntentExample.example_id,
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))

    def list_runtime_logs_for_rewrap(
        self,
        service_id: str,
        key_ids: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[models.RuntimeLog]:
        statement = (
            select(models.RuntimeLog)
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.query_raw_ciphertext.is_not(None))
            .where(models.RuntimeLog.query_raw_encrypted_dek.is_not(None))
            .where(models.RuntimeLog.query_raw_encrypted_dek_iv.is_not(None))
            .where(models.RuntimeLog.query_raw_encrypted_dek_auth_tag.is_not(None))
            .where(models.RuntimeLog.query_raw_key_id.is_not(None))
            .where(models.RuntimeLog.query_raw_iv.is_not(None))
            .where(models.RuntimeLog.query_raw_auth_tag.is_not(None))
            .where(models.RuntimeLog.query_raw_algorithm.is_not(None))
        )
        if key_ids is not None:
            key_id_values = tuple(key_ids)
            if not key_id_values:
                return []
            statement = statement.where(models.RuntimeLog.query_raw_key_id.in_(key_id_values))
        statement = statement.order_by(
            models.RuntimeLog.created_at,
            models.RuntimeLog.trace_id,
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))

    def count_raw_text_key_ids(self, service_id: str) -> RawTextKeyIdCounts:
        example_rows = self.session.execute(
            select(
                models.IntentExample.text_raw_key_id,
                func.count(models.IntentExample.example_id),
            )
            .where(models.IntentExample.service_id == service_id)
            .group_by(models.IntentExample.text_raw_key_id)
        )
        runtime_log_rows = self.session.execute(
            select(
                models.RuntimeLog.query_raw_key_id,
                func.count(models.RuntimeLog.trace_id),
            )
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.raw_query_deleted_at.is_(None))
            .where(models.RuntimeLog.query_raw_ciphertext.is_not(None))
            .where(models.RuntimeLog.query_raw_encrypted_dek.is_not(None))
            .where(models.RuntimeLog.query_raw_encrypted_dek_iv.is_not(None))
            .where(models.RuntimeLog.query_raw_encrypted_dek_auth_tag.is_not(None))
            .where(models.RuntimeLog.query_raw_key_id.is_not(None))
            .where(models.RuntimeLog.query_raw_iv.is_not(None))
            .where(models.RuntimeLog.query_raw_auth_tag.is_not(None))
            .where(models.RuntimeLog.query_raw_algorithm.is_not(None))
            .group_by(models.RuntimeLog.query_raw_key_id)
        )
        redacted_count = self.session.scalar(
            select(func.count(models.RuntimeLog.trace_id))
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.raw_query_deleted_at.is_not(None))
        )
        return {
            "intent_examples": {
                key_id: int(count)
                for key_id, count in example_rows
            },
            "runtime_logs": {
                key_id: int(count)
                for key_id, count in runtime_log_rows
            },
            "runtime_logs_redacted": int(redacted_count or 0),
        }

    def count_raw_text_key_inventory(self, service_id: str) -> RawTextKeyIdCounts:
        example_rows = self.session.execute(
            select(
                models.IntentExample.text_raw_key_id,
                func.count(models.IntentExample.example_id),
            )
            .where(models.IntentExample.service_id == service_id)
            .group_by(models.IntentExample.text_raw_key_id)
        )
        runtime_log_rows = self.session.execute(
            select(
                models.RuntimeLog.query_raw_key_id,
                func.count(models.RuntimeLog.trace_id),
            )
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.query_raw_key_id.is_not(None))
            .group_by(models.RuntimeLog.query_raw_key_id)
        )
        redacted_count = self.session.scalar(
            select(func.count(models.RuntimeLog.trace_id))
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.raw_query_deleted_at.is_not(None))
        )
        incomplete_without_key_count = self.session.scalar(
            select(func.count(models.RuntimeLog.trace_id))
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.raw_query_deleted_at.is_(None))
            .where(models.RuntimeLog.query_raw_key_id.is_(None))
            .where(
                or_(
                    models.RuntimeLog.query_raw_ciphertext.is_not(None),
                    models.RuntimeLog.query_raw_encrypted_dek.is_not(None),
                    models.RuntimeLog.query_raw_encrypted_dek_iv.is_not(None),
                    models.RuntimeLog.query_raw_encrypted_dek_auth_tag.is_not(None),
                    models.RuntimeLog.query_raw_iv.is_not(None),
                    models.RuntimeLog.query_raw_auth_tag.is_not(None),
                    models.RuntimeLog.query_raw_algorithm.is_not(None),
                )
            )
        )

        return {
            "intent_examples": {
                key_id: int(count)
                for key_id, count in example_rows
            },
            "runtime_logs": {
                key_id: int(count)
                for key_id, count in runtime_log_rows
            },
            "runtime_logs_redacted": int(redacted_count or 0),
            "runtime_logs_incomplete": int(incomplete_without_key_count or 0),
        }

    def list_audit_logs(
        self,
        service_id: str,
        limit: int,
        event_type: str | None = None,
        trace_id: str | None = None,
    ) -> list[models.AuditLog]:
        statement = select(models.AuditLog).where(models.AuditLog.service_id == service_id)
        if event_type is not None:
            statement = statement.where(models.AuditLog.event_type == event_type)
        if trace_id is not None:
            statement = statement.where(models.AuditLog.trace_id == trace_id)
        statement = statement.order_by(
            models.AuditLog.created_at.desc(),
            models.AuditLog.audit_id,
        ).limit(limit)
        return list(self.session.scalars(statement))

    def runtime_metrics(
        self,
        service_id: str,
        *,
        window_hours: int,
    ) -> dict[str, Any]:
        from intent_routing.ops.metrics import runtime_metrics_for_service

        return runtime_metrics_for_service(
            self.session,
            service_id,
            window_hours=window_hours,
        )

    def redact_runtime_raw_queries(
        self,
        service_id: str,
        trace_ids: Iterable[str],
        actor_id: str,
        reason: str,
        deleted_at: datetime,
    ) -> int:
        return len(
            self.redact_runtime_raw_query_trace_ids(
                service_id,
                trace_ids=trace_ids,
                actor_id=actor_id,
                reason=reason,
                deleted_at=deleted_at,
            )
        )

    def redact_runtime_raw_query_trace_ids(
        self,
        service_id: str,
        trace_ids: Iterable[str],
        actor_id: str,
        reason: str,
        deleted_at: datetime,
    ) -> list[str]:
        trace_id_values = tuple(trace_ids)
        if not trace_id_values:
            return []

        redacted_trace_ids = self.session.scalars(
            update(models.RuntimeLog)
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.trace_id.in_(trace_id_values))
            .where(models.RuntimeLog.raw_query_deleted_at.is_(None))
            .where(
                or_(
                    models.RuntimeLog.query_raw_ciphertext.is_not(None),
                    models.RuntimeLog.query_raw_encrypted_dek.is_not(None),
                    models.RuntimeLog.query_raw_encrypted_dek_iv.is_not(None),
                    models.RuntimeLog.query_raw_encrypted_dek_auth_tag.is_not(None),
                    models.RuntimeLog.query_raw_key_id.is_not(None),
                    models.RuntimeLog.query_raw_iv.is_not(None),
                    models.RuntimeLog.query_raw_auth_tag.is_not(None),
                    models.RuntimeLog.query_raw_algorithm.is_not(None),
                )
            )
            .values(
                query_raw_ciphertext=None,
                query_raw_encrypted_dek=None,
                query_raw_encrypted_dek_iv=None,
                query_raw_encrypted_dek_auth_tag=None,
                query_raw_key_id=None,
                query_raw_iv=None,
                query_raw_auth_tag=None,
                query_raw_algorithm=None,
                raw_query_deleted_at=deleted_at,
                raw_query_deleted_by=actor_id,
                raw_query_delete_reason=reason,
            )
            .returning(models.RuntimeLog.trace_id)
        )
        self.session.flush()
        return list(redacted_trace_ids.all())

    def list_masked_runtime_logs(
        self,
        service_id: str,
        *,
        limit: int,
    ) -> list[Mapping[str, Any]]:
        columns = _masked_runtime_log_columns()
        rows = (
            self.session.execute(
                select(*columns)
                .where(models.RuntimeLog.service_id == service_id)
                .order_by(
                    models.RuntimeLog.created_at.desc(),
                    models.RuntimeLog.trace_id,
                )
                .limit(limit)
            )
            .mappings()
            .all()
        )
        return [cast("Mapping[str, Any]", row) for row in rows]

    def list_masked_runtime_logs_for_export(
        self,
        service_id: str,
        *,
        trace_id: str | None = None,
        limit: int = 500,
    ) -> list[Mapping[str, Any]]:
        statement = select(*_masked_runtime_log_columns()).where(
            models.RuntimeLog.service_id == service_id
        )
        if trace_id is not None:
            statement = statement.where(models.RuntimeLog.trace_id == trace_id)
        rows = self.session.execute(
            statement.order_by(
                models.RuntimeLog.created_at.desc(),
                models.RuntimeLog.trace_id,
            ).limit(limit)
        ).mappings()
        return [cast("Mapping[str, Any]", row) for row in rows]

    def get_masked_runtime_log(
        self,
        service_id: str,
        trace_id: str,
    ) -> Mapping[str, Any] | None:
        row = (
            self.session.execute(
                select(*_masked_runtime_log_columns())
                .where(models.RuntimeLog.service_id == service_id)
                .where(models.RuntimeLog.trace_id == trace_id)
            )
            .mappings()
            .one_or_none()
        )
        return cast("Mapping[str, Any] | None", row)

    def get_runtime_log_for_decrypt(
        self,
        service_id: str,
        trace_id: str,
    ) -> models.RuntimeLog | None:
        return self.session.scalar(
            select(models.RuntimeLog)
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.trace_id == trace_id)
        )

    def insert_audit_log(self, **values: Any) -> models.AuditLog:
        return self._add_and_flush(models.AuditLog(**values))


def _masked_runtime_log_columns() -> tuple[Any, ...]:
    return tuple(
        getattr(models.RuntimeLog, field_name).label(field_name)
        for field_name in MASKED_RUNTIME_LOG_FIELD_NAMES
    )
