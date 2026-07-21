from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from intent_routing.api import admin
from intent_routing.db import models

ApiKeyCreateRequestFactory = Callable[
    ...,
    admin.ApiKeyCreateRequest | admin.ServiceApiKeyCreateRequest,
]


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


def _api_key(
    *,
    status: str = "active",
    revoked_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> models.ApiKey:
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
        expires_at=expires_at if expires_at is not None else now + timedelta(days=1),
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


def test_api_key_create_request_and_response_allow_unlimited_expiry() -> None:
    request = admin.ServiceApiKeyCreateRequest(
        environment="prod",
        app_id="checkout-web",
        expires_in_days=None,
    )
    now = datetime.now(UTC)
    key = models.ApiKey(
        key_id="key_live_unlimited",
        key_hash="hash",
        key_fingerprint="sha256:abcd:unlimited",
        environment="prod",
        app_id="checkout-web",
        service_id="svc-a",
        allowed_intents=[],
        allowed_route_keys=[],
        status="active",
        expires_at=None,
        revoked_at=None,
        created_by="admin-user",
        created_at=now,
    )

    response = admin.ApiKeyCreateResponse(
        api_key="irt_once",
        api_key_displayed_once=True,
        **admin._api_key_response(key).model_dump(),
    )

    assert request.expires_in_days is None
    assert response.expires_at is None
    assert response.model_dump()["expires_at"] is None


@pytest.mark.parametrize(
    "request_factory, values",
    [
        (
            admin.ApiKeyCreateRequest,
            {"service_id": "svc-a", "environment": "dev", "app_id": "  checkout-web  "},
        ),
        (
            admin.ServiceApiKeyCreateRequest,
            {"environment": "dev", "app_id": "  checkout-web  "},
        ),
    ],
)
def test_api_key_create_requests_normalize_app_id_and_reject_blank_values(
    request_factory: ApiKeyCreateRequestFactory,
    values: dict[str, object],
) -> None:
    assert request_factory(**values).app_id == "checkout-web"

    with pytest.raises(ValidationError):
        request_factory(**{**values, "app_id": " \t "})


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


def test_api_key_reveal_audit_state_omits_secret_derived_fields() -> None:
    key = _api_key()

    state = admin._api_key_reveal_audit_state(key)

    assert state == {
        "key_id": key.key_id,
        "service_id": key.service_id,
        "environment": key.environment,
        "app_id": key.app_id,
        "status": key.status,
    }
    assert "api_key" not in state
    assert "authorization_header" not in state
    assert "key_fingerprint" not in state
    assert "key_hash" not in state


@pytest.mark.parametrize(
    ("api_key", "status_code", "message"),
    [
        (
            _api_key(
                status="revoked",
                revoked_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
            ),
            400,
            "Revoked API key secrets cannot be revealed.",
        ),
        (
            _api_key(expires_at=datetime(2026, 7, 21, 0, 59, tzinfo=UTC)),
            400,
            "Expired API key secrets cannot be revealed.",
        ),
        (
            _api_key(status="expired", expires_at=None),
            400,
            "Expired API key secrets cannot be revealed.",
        ),
        (
            _api_key(),
            409,
            "API key secret is unavailable; rotate or reissue this legacy key.",
        ),
    ],
)
def test_raise_if_api_key_not_revealable_rejects_non_recoverable_keys(
    api_key: models.ApiKey,
    status_code: int,
    message: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        admin._raise_if_api_key_not_revealable(
            api_key,
            datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
        )

    assert exc_info.value.status_code == status_code
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    error = detail["error"]
    assert isinstance(error, dict)
    assert error["message"] == message
