from datetime import UTC, datetime, timedelta

from intent_routing.domain.enums import ErrorCode
from intent_routing.security.api_keys import (
    ApiKeyRecord,
    check_scope,
    fingerprint_secret,
    generate_api_key_secret,
    hash_secret,
    verify_secret,
)


def _active_record(service_id: str = "svc-a") -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id="key-test",
        key_hash=hash_secret("test-secret"),
        key_fingerprint=fingerprint_secret("test-secret"),
        environment="prod",
        app_id="app-a",
        service_id=service_id,
        allowed_intents=[],
        allowed_route_keys=[],
        status="active",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=None,
    )


def test_generate_api_key_secret_returns_at_least_256_bit_urlsafe_secret() -> None:
    secret = generate_api_key_secret()

    assert len(secret) >= 43


def test_hash_verify_and_fingerprint_do_not_expose_raw_secret() -> None:
    secret = generate_api_key_secret()

    hashed = hash_secret(secret)
    fingerprint = fingerprint_secret(secret)

    assert secret not in hashed
    assert secret not in fingerprint
    assert verify_secret(secret, hashed) is True
    assert fingerprint.endswith(secret[-4:])


def test_verify_secret_returns_false_for_malformed_hash() -> None:
    assert verify_secret("test-secret", "pbkdf2_sha256$0$abcd$abcd") is False


def test_check_scope_denies_mismatched_service_id() -> None:
    record = _active_record(service_id="svc-a")

    result = check_scope(
        record,
        app_id="app-a",
        service_id="svc-b",
        route_key=None,
        intent_id=None,
    )

    assert result.allowed is False
    assert result.error_code == ErrorCode.SERVICE_SCOPE_DENIED
