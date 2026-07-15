from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Service(Base):
    __tablename__ = "services"

    service_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(Text)
    default_threshold_preset: Mapped[str] = mapped_column(
        Text, server_default=text("'balanced'")
    )
    max_input_tokens: Mapped[int] = mapped_column(server_default=text("256"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApiKey(Base):
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(Text, primary_key=True)
    key_hash: Mapped[str] = mapped_column(Text)
    key_fingerprint: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(Text)
    app_id: Mapped[str] = mapped_column(Text)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    allowed_intents: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    allowed_route_keys: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    status: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    service: Mapped[Service] = relationship()


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dept_number: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    use_yn: Mapped[str] = mapped_column(Text, server_default=text("'Y'"))
    created_by: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("use_yn in ('Y', 'N')", name="ck_departments_use_yn"),
        UniqueConstraint("dept_number", name="uq_departments_dept_number"),
    )


class OrganizationUser(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_number: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id"))
    use_yn: Mapped[str] = mapped_column(Text, server_default=text("'Y'"))
    created_by: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    department: Mapped[Department] = relationship()

    __table_args__ = (
        CheckConstraint("use_yn in ('Y', 'N')", name="ck_users_use_yn"),
        UniqueConstraint("user_number", name="uq_users_user_number"),
        Index("ix_users_department_id", "department_id"),
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text)
    email_normalized: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    admin_access_reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    organization_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
    )

    organization_user: Mapped[OrganizationUser | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'disabled')",
            name="ck_admin_users_status",
        ),
        UniqueConstraint("email"),
        UniqueConstraint("email_normalized"),
        UniqueConstraint(
            "organization_user_id",
            name="uq_admin_users_organization_user_id",
        ),
    )


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    session_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("admin_users.user_id"))
    token_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[AdminUser] = relationship()

    __table_args__ = (UniqueConstraint("token_hash"),)


class AdminUserRole(Base):
    __tablename__ = "admin_user_roles"

    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("admin_users.user_id"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    assigned_by: Mapped[str] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[AdminUser] = relationship()

    __table_args__ = (
        CheckConstraint(
            "role in ('system_admin', 'application_admin')",
            name="ck_admin_user_roles_role",
        ),
        Index(
            "uq_admin_user_roles_single_system_admin",
            "role",
            unique=True,
            postgresql_where=text("role = 'system_admin'"),
        ),
    )


class AdminAccessRequest(Base):
    __tablename__ = "admin_access_requests"

    request_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_number: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id"))
    email: Mapped[str] = mapped_column(Text)
    email_normalized: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    access_reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_admin_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("admin_users.user_id")
    )

    department: Mapped[Department] = relationship()
    created_user: Mapped[OrganizationUser | None] = relationship()
    created_admin_user: Mapped[AdminUser | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'approved', 'rejected')",
            name="ck_admin_access_requests_status",
        ),
        UniqueConstraint(
            "email_normalized",
            "status",
            name="uq_admin_access_requests_pending_email",
        ),
        Index("ix_admin_access_requests_status_requested_at", "status", "requested_at"),
    )


class UserServiceRole(Base):
    __tablename__ = "user_service_roles"

    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("admin_users.user_id"),
        primary_key=True,
    )
    service_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("services.service_id"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    assigned_by: Mapped[str] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[AdminUser] = relationship()
    service: Mapped[Service] = relationship()

    __table_args__ = (
        CheckConstraint(
            "role in ('service_owner', 'service_developer', 'service_operator', 'auditor')",
            name="ck_user_service_roles_role",
        ),
        Index("ix_user_service_roles_user_id", "user_id"),
        Index("ix_user_service_roles_service_id", "service_id"),
    )


class GovernedActionRequest(Base):
    __tablename__ = "governed_action_requests"

    request_id: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    resource_type: Mapped[str] = mapped_column(Text)
    resource_id: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    requested_by: Mapped[str] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)

    service: Mapped[Service] = relationship()

    __table_args__ = (
        CheckConstraint(
            "resource_type in "
            "('intent', 'example', 'release', 'runtime_log', 'raw_query', 'export')",
            name="ck_governed_action_requests_resource_type",
        ),
        CheckConstraint(
            "action in "
            "('request', 'approve', 'reject', 'activate', 'rollback', 'decrypt', "
            "'export')",
            name="ck_governed_action_requests_action",
        ),
        CheckConstraint(
            "status in "
            "('pending', 'approved', 'rejected', 'activated', 'rolled_back', "
            "'token_issued', 'viewed', 'expired', 'completed')",
            name="ck_governed_action_requests_status",
        ),
        Index("ix_governed_action_requests_service_id", "service_id"),
        Index("ix_governed_action_requests_status", "status"),
        Index("ix_governed_action_requests_resource_type", "resource_type"),
    )


class RawQueryViewToken(Base):
    __tablename__ = "raw_query_view_tokens"

    token_id: Mapped[str] = mapped_column(Text, primary_key=True)
    request_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("governed_action_requests.request_id"),
    )
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    trace_id: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[str] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    request: Mapped[GovernedActionRequest] = relationship()
    service: Mapped[Service] = relationship()

    __table_args__ = (
        UniqueConstraint("token_hash"),
        Index("ix_raw_query_view_tokens_service_id", "service_id"),
        Index("ix_raw_query_view_tokens_expires_at", "expires_at"),
    )


class Intent(Base):
    __tablename__ = "intents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    intent_id: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    route_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    include_keywords: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    exclude_keywords: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    created_by: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    service: Mapped[Service] = relationship()

    __table_args__ = (
        UniqueConstraint("service_id", "intent_id"),
        UniqueConstraint("service_id", "route_key"),
    )


class IntentExample(Base):
    __tablename__ = "intent_examples"

    example_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    service_id: Mapped[str] = mapped_column(Text)
    intent_id: Mapped[str] = mapped_column(Text)
    example_type: Mapped[str] = mapped_column(Text)
    text_raw_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    text_raw_encrypted_dek: Mapped[bytes] = mapped_column(LargeBinary)
    text_raw_encrypted_dek_iv: Mapped[bytes] = mapped_column(LargeBinary)
    text_raw_encrypted_dek_auth_tag: Mapped[bytes] = mapped_column(LargeBinary)
    text_raw_key_id: Mapped[str] = mapped_column(Text)
    text_raw_iv: Mapped[bytes] = mapped_column(LargeBinary)
    text_raw_auth_tag: Mapped[bytes] = mapped_column(LargeBinary)
    text_raw_algorithm: Mapped[str] = mapped_column(Text)
    text_masked: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    source: Mapped[str] = mapped_column(Text)
    test_case_id: Mapped[str | None] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(server_default=text("false"))
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        ForeignKeyConstraint(
            ["service_id", "intent_id"],
            ["intents.service_id", "intents.intent_id"],
        ),
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    policy_version: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    threshold_preset: Mapped[str] = mapped_column(Text)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric)
    clarify_margin: Mapped[Decimal] = mapped_column(Numeric)
    min_candidate_score: Mapped[Decimal] = mapped_column(Numeric)
    fallback_score: Mapped[Decimal] = mapped_column(Numeric)
    risk_policy: Mapped[dict[str, Any]] = mapped_column(JSONB)
    off_topic_policy: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntentCatalogVersion(Base):
    __tablename__ = "intent_catalog_versions"

    intent_catalog_version: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VectorIndexVersion(Base):
    __tablename__ = "vector_index_versions"

    vector_index_version: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    intent_catalog_version: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TestDataset(Base):
    __tablename__ = "test_datasets"

    test_dataset_version: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    source_filename: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    test_dataset_version: Mapped[str] = mapped_column(
        Text, ForeignKey("test_datasets.test_dataset_version")
    )
    case_id: Mapped[str] = mapped_column(Text)
    query: Mapped[str] = mapped_column(Text)
    expected_intent: Mapped[str | None] = mapped_column(Text)
    case_type: Mapped[str] = mapped_column(Text)
    memo: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("test_dataset_version", "case_id"),)


class TestRun(Base):
    __tablename__ = "test_runs"

    test_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    test_dataset_version: Mapped[str] = mapped_column(
        Text, ForeignKey("test_datasets.test_dataset_version")
    )
    policy_version: Mapped[str] = mapped_column(
        Text, ForeignKey("policy_versions.policy_version")
    )
    intent_catalog_version: Mapped[str] = mapped_column(
        Text, ForeignKey("intent_catalog_versions.intent_catalog_version")
    )
    threshold_preset: Mapped[str] = mapped_column(Text)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric)
    pass_rate: Mapped[Decimal] = mapped_column(Numeric)
    review_rate: Mapped[Decimal] = mapped_column(Numeric)
    risk_pass_rate: Mapped[Decimal] = mapped_column(Numeric)
    gate_passed: Mapped[bool]
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["TestResult"]] = relationship(cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    test_run_id: Mapped[str] = mapped_column(Text, ForeignKey("test_runs.test_run_id"))
    case_id: Mapped[str] = mapped_column(Text)
    query_masked: Mapped[str] = mapped_column(Text)
    case_type: Mapped[str] = mapped_column(Text)
    expected_decision: Mapped[str] = mapped_column(Text)
    expected_intent: Mapped[str | None] = mapped_column(Text)
    actual_decision: Mapped[str] = mapped_column(Text)
    actual_intent: Mapped[str | None] = mapped_column(Text)
    actual_route_key: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    result: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)


class Release(Base):
    __tablename__ = "releases"

    release_version: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str] = mapped_column(Text, ForeignKey("services.service_id"))
    environment: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(
        Text, ForeignKey("policy_versions.policy_version")
    )
    intent_catalog_version: Mapped[str] = mapped_column(
        Text, ForeignKey("intent_catalog_versions.intent_catalog_version")
    )
    model_version: Mapped[str] = mapped_column(Text)
    vector_index_version: Mapped[str] = mapped_column(Text)
    test_dataset_version: Mapped[str] = mapped_column(
        Text, ForeignKey("test_datasets.test_dataset_version")
    )
    test_run_id: Mapped[str] = mapped_column(Text, ForeignKey("test_runs.test_run_id"))
    pass_rate: Mapped[Decimal] = mapped_column(Numeric)
    risk_pass_rate: Mapped[Decimal] = mapped_column(Numeric)
    active: Mapped[bool] = mapped_column(server_default=text("false"))
    released_by: Mapped[str] = mapped_column(Text)
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rollback_target: Mapped[str | None] = mapped_column(Text)


class RuntimeLog(Base):
    __tablename__ = "runtime_logs"

    trace_id: Mapped[str] = mapped_column(Text, primary_key=True)
    request_id: Mapped[str | None] = mapped_column(Text)
    app_id: Mapped[str | None] = mapped_column(Text)
    service_id: Mapped[str | None] = mapped_column(Text)
    release_version: Mapped[str | None] = mapped_column(Text)
    policy_version: Mapped[str | None] = mapped_column(Text)
    intent_catalog_version: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(Text)
    vector_index_version: Mapped[str | None] = mapped_column(Text)
    test_run_id: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(Text)
    intent_id: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    margin: Mapped[Decimal | None] = mapped_column(Numeric)
    threshold_preset: Mapped[str | None] = mapped_column(Text)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric)
    route_key: Mapped[str | None] = mapped_column(Text)
    decision_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_category: Mapped[str | None] = mapped_column(Text)
    error_layer: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None]
    retryable: Mapped[bool | None]
    latency_ms: Mapped[int]
    query_raw_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    query_raw_encrypted_dek: Mapped[bytes | None] = mapped_column(LargeBinary)
    query_raw_encrypted_dek_iv: Mapped[bytes | None] = mapped_column(LargeBinary)
    query_raw_encrypted_dek_auth_tag: Mapped[bytes | None] = mapped_column(LargeBinary)
    query_raw_key_id: Mapped[str | None] = mapped_column(Text)
    query_raw_iv: Mapped[bytes | None] = mapped_column(LargeBinary)
    query_raw_auth_tag: Mapped[bytes | None] = mapped_column(LargeBinary)
    query_raw_algorithm: Mapped[str | None] = mapped_column(Text)
    query_masked: Mapped[str | None] = mapped_column(Text)
    raw_query_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    raw_query_deleted_by: Mapped[str | None] = mapped_column(Text)
    raw_query_delete_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RawTextRewrapRun(Base):
    __tablename__ = "raw_text_rewrap_runs"

    rewrap_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str | None] = mapped_column(Text)
    target_key_id: Mapped[str] = mapped_column(Text)
    source_key_ids: Mapped[list[str]] = mapped_column(JSONB)
    included_tables: Mapped[list[str]] = mapped_column(JSONB)
    dry_run: Mapped[bool]
    approval_id: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    scanned_count: Mapped[int]
    rewrapped_count: Mapped[int]
    skipped_count: Mapped[int]
    failed_count: Mapped[int]
    report: Mapped[dict[str, Any]] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    service_id: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(Text)
    target_type: Mapped[str] = mapped_column(Text)
    target_id: Mapped[str] = mapped_column(Text)
    view_reason: Mapped[str | None] = mapped_column(Text)
    source_ip: Mapped[str | None] = mapped_column(Text)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
