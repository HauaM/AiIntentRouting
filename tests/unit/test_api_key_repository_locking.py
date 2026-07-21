from __future__ import annotations

import inspect
from typing import Any, cast

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from intent_routing.api import admin
from intent_routing.db.repositories import IntentRoutingRepository


class CapturingSession:
    def __init__(self) -> None:
        self.statement: Any = None
        self.result = object()

    def scalar(self, statement: Any) -> object:
        self.statement = statement
        return self.result


def test_get_api_key_by_id_for_update_uses_row_lock() -> None:
    assert hasattr(IntentRoutingRepository, "get_api_key_by_id_for_update")
    session = CapturingSession()
    repository = IntentRoutingRepository(cast(Session, session))

    result = repository.get_api_key_by_id_for_update("key_live_test")

    assert result is session.result
    sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "WHERE api_keys.key_id = 'key_live_test'" in sql
    assert sql.rstrip().endswith("FOR UPDATE")


def test_api_key_reveal_and_revoke_handlers_use_locked_loader() -> None:
    for handler in (
        admin.revoke_api_key,
        admin.revoke_service_api_key,
        admin.reveal_service_api_key,
    ):
        source = inspect.getsource(handler)
        assert "repository.get_api_key_by_id_for_update(key_id)" in source
        assert "repository.get_api_key_by_id(key_id)" not in source
