from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar, cast
from uuid import UUID

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import bindparam, func, or_, select, text, update
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

    def assign_admin_user_role(self, **values: Any) -> models.AdminUserRole:
        values = dict(values)
        values["role"] = _require_allowed_value(
            values.get("role"),
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        return self._add_and_flush(models.AdminUserRole(**values))

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
            .where(models.AdminSession.token_hash == token_hash)
            .where(models.AdminSession.revoked_at.is_(None))
            .where(models.AdminSession.expires_at > now)
            .where(models.AdminUser.status == "active")
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

    def list_service_roles_for_user(self, user_id: str) -> list[models.UserServiceRole]:
        return list(
            self.session.scalars(
                select(models.UserServiceRole)
                .where(models.UserServiceRole.user_id == user_id)
                .order_by(models.UserServiceRole.service_id, models.UserServiceRole.role)
            )
        )

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
