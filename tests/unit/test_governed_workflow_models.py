from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


def test_governed_workflow_models_expose_expected_tables_and_indexes() -> None:
    assert {
        "governed_action_requests",
        "raw_query_view_tokens",
    }.issubset(models.Base.metadata.tables)

    governed_requests = models.GovernedActionRequest.__table__
    raw_query_tokens = models.RawQueryViewToken.__table__

    assert set(cast(Any, governed_requests.primary_key).columns.keys()) == {"request_id"}
    assert _has_fk(governed_requests, ["service_id"], "services")
    assert {
        "request_id",
        "service_id",
        "resource_type",
        "resource_id",
        "action",
        "status",
        "requested_by",
        "requested_at",
        "decided_by",
        "decided_at",
        "reason",
    }.issubset(governed_requests.c.keys())
    assert _has_index(governed_requests, "service_id")
    assert _has_index(governed_requests, "status")
    assert _has_index(governed_requests, "resource_type")

    assert set(cast(Any, raw_query_tokens.primary_key).columns.keys()) == {"token_id"}
    assert _has_fk(raw_query_tokens, ["request_id"], "governed_action_requests")
    assert _has_fk(raw_query_tokens, ["service_id"], "services")
    assert "token_hash" in raw_query_tokens.c
    assert "token" not in raw_query_tokens.c
    assert "expires_at" in raw_query_tokens.c
    assert _has_index(raw_query_tokens, "service_id")
    assert _has_index(raw_query_tokens, "expires_at")


def test_governed_workflow_migration_creates_required_tables_and_indexes() -> None:
    migration = Path("alembic/versions/0006_governed_workflow_requests.py").read_text()

    assert "governed_action_requests" in migration
    assert "raw_query_view_tokens" in migration
    for index_name in (
        "ix_governed_action_requests_service_id",
        "ix_governed_action_requests_status",
        "ix_governed_action_requests_resource_type",
        "ix_raw_query_view_tokens_service_id",
        "ix_raw_query_view_tokens_expires_at",
    ):
        assert index_name in migration


def test_repository_exposes_governed_workflow_helpers() -> None:
    assert {
        "create_governed_action_request",
        "get_governed_action_request",
        "list_governed_action_requests",
        "approve_governed_action_request",
        "reject_governed_action_request",
        "issue_raw_query_view_token",
        "get_valid_raw_query_view_token",
        "mark_raw_query_view_token_viewed",
        "expire_raw_query_view_tokens",
    }.issubset(dir(IntentRoutingRepository))


def test_repository_creates_governed_request_and_raw_query_token_hash_only() -> None:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=5)
    session = _FakeSession()
    repository = IntentRoutingRepository(cast(Session, session))

    request = repository.create_governed_action_request(
        request_id="gar_123",
        service_id="svc-support",
        resource_type="raw_query",
        resource_id="trace-123",
        action="decrypt",
        requested_by="operator-1",
        requested_at=now,
        reason="Investigating support ticket INC-123",
    )

    assert request.status == "pending"
    assert request.requested_at == now
    assert request.decided_by is None
    assert request.decided_at is None
    assert session.added[-1] is request

    repository.approve_governed_action_request(
        request,
        decided_by="auditor-1",
        decided_at=now,
        reason="Ticket reason is valid",
    )
    token = repository.issue_raw_query_view_token(
        request,
        token_id="rqt_123",
        token_hash="sha256:raw-query-token-hash",
        expires_at=expires_at,
        issued_by="operator-1",
        issued_at=now,
    )

    assert request.status == "token_issued"
    assert token.request_id == "gar_123"
    assert token.service_id == "svc-support"
    assert token.trace_id == "trace-123"
    assert token.token_hash == "sha256:raw-query-token-hash"
    assert not hasattr(token, "token")
    assert token.expires_at == expires_at


def test_repository_rejects_invalid_governed_status_transitions() -> None:
    now = datetime.now(UTC)
    request = models.GovernedActionRequest(
        request_id="gar_pending",
        service_id="svc-support",
        resource_type="raw_query",
        resource_id="trace-123",
        action="decrypt",
        status="pending",
        requested_by="operator-1",
        requested_at=now,
        reason="Investigating support ticket INC-123",
    )
    session = _FakeSession()
    repository = IntentRoutingRepository(cast(Session, session))

    with pytest.raises(ValueError, match="must be approved"):
        repository.issue_raw_query_view_token(
            request,
            token_id="rqt_pending",
            token_hash="sha256:raw-query-token-hash",
            expires_at=now + timedelta(minutes=5),
            issued_by="operator-1",
            issued_at=now,
        )

    assert session.added == []
    assert request.status == "pending"

    with pytest.raises(ValueError, match="request author"):
        repository.approve_governed_action_request(
            request,
            decided_by="operator-1",
            decided_at=now,
        )


def _has_fk(table: Any, column_names: list[str], target_table: str) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and list(constraint.columns.keys()) == column_names
        and all(element.column.table.name == target_table for element in constraint.elements)
        for constraint in table.constraints
    )


def _has_index(table: Any, column_name: str) -> bool:
    return any(
        [column.name for column in index.columns] == [column_name] for index in table.indexes
    )


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        pass
