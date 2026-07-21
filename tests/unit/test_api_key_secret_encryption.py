from __future__ import annotations

from datetime import UTC, datetime, timedelta

from intent_routing.db import models
from intent_routing.security.api_key_secrets import (
    apply_encrypted_api_key_secret,
    encrypted_api_key_secret,
    load_api_key_secret_keyring,
)


def _api_key() -> models.ApiKey:
    now = datetime.now(UTC)
    return models.ApiKey(
        key_id="key_live_test",
        key_hash="hash",
        key_fingerprint="sha256:test:once",
        environment="dev",
        app_id="checkout-web",
        service_id="svc-a",
        allowed_intents=[],
        allowed_route_keys=[],
        status="active",
        expires_at=now + timedelta(days=1),
        revoked_at=None,
        created_by="admin-user",
        created_at=now,
    )


def test_api_key_secret_round_trips_through_envelope_columns() -> None:
    keyring = load_api_key_secret_keyring(
        {
            "API_KEY_SECRET_KEK_ID": "local-api-key-secret-kek-001",
            "API_KEY_SECRET_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "API_KEY_SECRET_LEGACY_KEKS_JSON": "{}",
        }
    )
    api_key = _api_key()

    encrypted = keyring.encrypt_text("irt_secret_once")
    apply_encrypted_api_key_secret(api_key, encrypted)

    stored = encrypted_api_key_secret(api_key)
    assert stored is not None
    assert keyring.decrypt_text(stored) == "irt_secret_once"
    assert api_key.secret_ciphertext is not None
    assert b"irt_secret_once" not in api_key.secret_ciphertext
