from typing import Any, cast

import pytest

from intent_routing.api import admin


class FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_get_admin_session_rolls_back_and_closes_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr(admin, "SessionLocal", lambda: session)

    session_generator = cast(Any, admin.get_admin_session())
    assert next(session_generator) is session

    with pytest.raises(RuntimeError):
        session_generator.throw(RuntimeError("failed write"))

    assert session.rolled_back is True
    assert session.closed is True
