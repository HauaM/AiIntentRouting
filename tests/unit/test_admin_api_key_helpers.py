from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from intent_routing.api import admin
from intent_routing.db import models


class FakeApiKeyRepository:
    def __init__(self) -> None:
        self.revoked_at: datetime | None = None
        self.audit_events: list[dict[str, Any]] = []

    def revoke_api_key(
        self,
        api_key: models.ApiKey,
        *,
        revoked_at: datetime,
    ) -> models.ApiKey:
        self.revoked_at = revoked_at
        api_key.status = "revoked"
        api_key.revoked_at = revoked_at
        return api_key

    def insert_audit_log(self, **values: Any) -> None:
        self.audit_events.append(values)


def _api_key(*, status: str = "active", revoked_at: datetime | None = None) -> models.ApiKey:
    now = datetime.now(UTC)
    return models.ApiKey(
        key_id="key_live_test",
        key_hash="hash",
        key_fingerprint="sha256:abcd:test",
        environment="prod",
        app_id="dify-helpdesk",
        service_id="svc-a",
        allowed_intents=["billing_refund"],
        allowed_route_keys=["billing.refund.request"],
        status=status,
        expires_at=now + timedelta(days=1),
        revoked_at=revoked_at,
        created_by="admin-user",
        created_at=now,
    )


def test_api_key_create_response_includes_revoked_at_null() -> None:
    key = _api_key()

    response = admin.ApiKeyCreateResponse(
        api_key="irt_once",
        api_key_displayed_once=True,
        **admin._api_key_response(key).model_dump(),
    )

    assert response.revoked_at is None
    assert "revoked_at" in response.model_dump()


def test_revoke_api_key_record_is_idempotent_for_already_revoked_key() -> None:
    first_revoked_at = datetime(2026, 7, 9, 0, 0, tzinfo=UTC)
    retry_time = datetime(2026, 7, 9, 1, 0, tzinfo=UTC)
    key = _api_key(status="revoked", revoked_at=first_revoked_at)
    repository = FakeApiKeyRepository()

    result = admin._revoke_api_key_record(
        repository,  # type: ignore[arg-type]
        api_key=key,
        actor_id="admin-user",
        now=retry_time,
    )

    assert result is key
    assert key.revoked_at == first_revoked_at
    assert repository.revoked_at is None
    assert repository.audit_events == []


def test_revoke_api_key_record_writes_single_audit_event_for_active_key() -> None:
    revoked_at = datetime(2026, 7, 9, 1, 0, tzinfo=UTC)
    key = _api_key()
    repository = FakeApiKeyRepository()

    admin._revoke_api_key_record(
        repository,  # type: ignore[arg-type]
        api_key=key,
        actor_id="admin-user",
        now=revoked_at,
    )

    assert key.status == "revoked"
    assert key.revoked_at == revoked_at
    assert repository.revoked_at == revoked_at
    assert len(repository.audit_events) == 1
    assert repository.audit_events[0]["event_type"] == "api_key.revoked"
