from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from intent_routing.health import _alembic_head_revision
from intent_routing.main import create_app


def test_healthz_returns_ok_without_opening_readiness_session() -> None:
    app = create_app()
    app.state.readiness_session_factory = _failing_session_factory
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_ready_when_database_migration_and_pgvector_are_ready() -> None:
    app = create_app()
    app.state.readiness_session_factory = _ready_session_factory
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "alembic": "ok",
            "pgvector": "ok",
        },
    }


def test_readyz_returns_503_without_leaking_dependency_details() -> None:
    app = create_app()
    app.state.readiness_session_factory = _failing_session_factory
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body == {
        "status": "not_ready",
        "checks": {
            "database": "failed",
            "alembic": "skipped",
            "pgvector": "skipped",
        },
    }
    serialized = json.dumps(body, sort_keys=True)
    assert "postgresql+psycopg://intent:secret@db/intent_routing" not in serialized
    assert "boom" not in serialized
    assert "RAW_TEXT_KEK_BASE64" not in serialized


@contextmanager
def _ready_session_factory() -> Iterator[_ReadySession]:
    yield _ReadySession()


@contextmanager
def _failing_session_factory() -> Iterator[None]:
    raise RuntimeError(
        "boom postgresql+psycopg://intent:secret@db/intent_routing RAW_TEXT_KEK_BASE64"
    )
    yield None


class _ReadySession:
    def execute(self, statement: Any) -> _ScalarResult:
        sql = str(statement)
        if "SELECT 1" in sql:
            return _ScalarResult(1)
        if "alembic_version" in sql:
            return _ScalarResult(_alembic_head_revision())
        if "pg_extension" in sql:
            return _ScalarResult(1)
        raise AssertionError(f"unexpected readiness SQL: {sql}")


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one(self) -> object:
        return self._value

    def scalar_one_or_none(self) -> object:
        return self._value
