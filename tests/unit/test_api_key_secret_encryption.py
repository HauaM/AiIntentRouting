from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.exceptions import InvalidTag

from intent_routing.db import models
from intent_routing.security.api_key_secrets import (
    api_key_secret_encryption_context,
    apply_encrypted_api_key_secret,
    encrypted_api_key_secret,
    load_api_key_secret_keyring,
)


def _context(api_key: models.ApiKey) -> dict[str, str]:
    return api_key_secret_encryption_context(
        service_id=api_key.service_id,
        key_id=api_key.key_id,
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

    assert "context" in inspect.signature(keyring.encrypt_text).parameters
    assert "context" in inspect.signature(keyring.decrypt_text).parameters
    context = _context(api_key)
    encrypted = keyring.encrypt_text("irt_secret_once", context=context)
    apply_encrypted_api_key_secret(api_key, encrypted)

    stored = encrypted_api_key_secret(api_key)
    assert stored is not None
    assert keyring.decrypt_text(stored, context=context) == "irt_secret_once"
    assert api_key.secret_ciphertext is not None
    assert b"irt_secret_once" not in api_key.secret_ciphertext


def test_swapped_api_key_secret_envelope_fails_row_context_authentication() -> None:
    keyring = load_api_key_secret_keyring(
        {
            "API_KEY_SECRET_KEK_ID": "local-api-key-secret-kek-001",
            "API_KEY_SECRET_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "API_KEY_SECRET_LEGACY_KEKS_JSON": "{}",
        }
    )
    assert "context" in inspect.signature(keyring.encrypt_text).parameters
    source = _api_key()
    target = _api_key()
    target.key_id = "key_live_other"
    target.service_id = "svc-b"
    encrypted = keyring.encrypt_text(
        "irt_secret_once",
        context=_context(source),
    )
    apply_encrypted_api_key_secret(target, encrypted)
    transplanted = encrypted_api_key_secret(target)
    assert transplanted is not None

    with pytest.raises(InvalidTag):
        keyring.decrypt_text(
            transplanted,
            context=_context(target),
        )
