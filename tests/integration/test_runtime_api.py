from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from intent_routing.api.dependencies import get_api_key_lookup, get_runtime_environment
from intent_routing.main import create_app
from intent_routing.security.api_keys import ApiKeyRecord, fingerprint_secret, hash_secret


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _record_for(
    secret: str,
    *,
    allowed_route_keys: list[str] | None = None,
    environment: str = "prod",
    expires_at: datetime | None = None,
    key_hash: str | None = None,
    revoked_at: datetime | None = None,
    status: str = "active",
) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id="key-live",
        key_hash=key_hash or hash_secret(secret),
        key_fingerprint=fingerprint_secret(secret),
        environment=environment,
        app_id="app-a",
        service_id="svc-a",
        allowed_intents=[],
        allowed_route_keys=allowed_route_keys or [],
        status=status,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=1),
        revoked_at=revoked_at,
    )


def _client_with_key_lookup(
    lookup: Callable[[str], ApiKeyRecord | None],
    *,
    environment: str = "prod",
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_api_key_lookup] = lambda: lookup
    app.dependency_overrides[get_runtime_environment] = lambda: environment
    return TestClient(app)


def _headers(secret: str, **overrides: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {secret}",
        "X-Key-Id": "key-live",
        "X-App-Id": "app-a",
        "X-Service-Id": "svc-a",
    }
    headers.update(overrides)
    return headers


def _runtime_payload(**user_context: str) -> dict[str, object]:
    return {
        "query": "reset my password",
        "user_context": user_context,
    }


def test_intent_route_missing_authorization_returns_error_envelope() -> None:
    client = _client_with_key_lookup(lambda _key_id: None)

    response = client.post(
        "/v1/intent-route",
        headers={
            "X-Key-Id": "key-live",
            "X-App-Id": "app-a",
            "X-Service-Id": "svc-a",
        },
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "trace_id" in body


def test_intent_route_malformed_bearer_returns_authentication_failed() -> None:
    client = _client_with_key_lookup(lambda _key_id: None)

    response = client.post(
        "/v1/intent-route",
        headers=_headers("valid-runtime-secret", Authorization="Basic nope"),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_missing_app_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    headers = _headers(secret)
    headers.pop("X-App-Id")
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_missing_service_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    headers = _headers(secret)
    headers.pop("X-Service-Id")
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_missing_key_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    headers = _headers(secret)
    headers.pop("X-Key-Id")
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_unknown_key_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(lambda _key_id: None)

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_wrong_secret_returns_authentication_failed() -> None:
    client = _client_with_key_lookup(
        lambda _key_id: _record_for("stored-runtime-secret")
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers("wrong-runtime-secret"),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_environment_mismatch_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(secret, environment="dev"),
        environment="prod",
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_malformed_stored_hash_returns_error_envelope() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(
            secret,
            key_hash="pbkdf2_sha256$0$abcd$abcd",
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "detail" not in body


def test_intent_route_valid_key_invalid_service_returns_scope_denied() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret, **{"X-Service-Id": "svc-b"}),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "error"
    assert body["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_intent_route_expired_key_returns_authentication_failed() -> None:
    secret = "expired-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(
            secret,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_revoked_key_returns_authentication_failed() -> None:
    secret = "revoked-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(
            secret,
            status="revoked",
            revoked_at=datetime.now(UTC),
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_valid_key_returns_temporary_fallback_response() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "fallback"
    assert body["fallback_policy"]["recommended_action"] == "route_engine_pending"


def test_intent_route_forbidden_candidate_route_returns_unauthorized_decision() -> None:
    secret = "candidate-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(secret, allowed_route_keys=["allowed.route"])
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret, **{"X-Request-Id": "req-1"}),
        json=_runtime_payload(candidate_route_key="forbidden.route"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "unauthorized"
    assert body["request_id"] == "req-1"


def test_intent_route_forbidden_candidate_intent_returns_unauthorized_decision() -> None:
    secret = "candidate-intent-secret"
    client = _client_with_key_lookup(
        lambda _key_id: ApiKeyRecord(
            key_id="key-live",
            key_hash=hash_secret(secret),
            key_fingerprint=fingerprint_secret(secret),
            environment="prod",
            app_id="app-a",
            service_id="svc-a",
            allowed_intents=["allowed-intent"],
            allowed_route_keys=[],
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=1),
            revoked_at=None,
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(candidate_intent_id="forbidden-intent"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "unauthorized"
    assert body["intent_id"] == "forbidden-intent"
