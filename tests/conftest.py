"""Shared pytest configuration for intent-routing tests."""

from collections.abc import Iterator
from os import environ

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def trusted_header_admin_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_AUTH_MODE", "trusted_headers")


@pytest.fixture
def db_session() -> Iterator[Session]:
    database_url = environ.get("TEST_DATABASE_URL") or environ.get("DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "DB integration tests require TEST_DATABASE_URL or explicit DATABASE_URL."
        )
    engine = create_engine(database_url)

    with Session(engine) as session:
        yield session

    engine.dispose()
