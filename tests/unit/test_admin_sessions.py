from datetime import UTC, datetime

from intent_routing.security.admin_sessions import (
    admin_session_expires_at,
    create_admin_session_token,
    hash_admin_session_token,
    verify_admin_session_token,
)


def test_create_admin_session_token_returns_unique_high_entropy_urlsafe_tokens() -> None:
    token = create_admin_session_token()
    another_token = create_admin_session_token()

    assert token != another_token
    assert len(token) >= 43
    assert all(character.isalnum() or character in "-_" for character in token)


def test_admin_session_token_hash_is_deterministic_and_does_not_store_raw_token() -> None:
    token = create_admin_session_token()

    token_hash = hash_admin_session_token(token)

    assert token not in token_hash
    assert token_hash == hash_admin_session_token(token)
    assert verify_admin_session_token(token, token_hash) is True


def test_admin_session_token_verify_rejects_wrong_token() -> None:
    token_hash = hash_admin_session_token("session-token")

    assert verify_admin_session_token("wrong-token", token_hash) is False


def test_admin_session_token_helpers_reject_blank_or_malformed_values() -> None:
    valid_hash = hash_admin_session_token("session-token")

    assert verify_admin_session_token("", valid_hash) is False
    assert verify_admin_session_token(" ", valid_hash) is False
    assert verify_admin_session_token("session-token", "not-a-session-hash") is False


def test_admin_session_expiry_is_future_utc_datetime() -> None:
    before = datetime.now(UTC)

    expiry = admin_session_expires_at(hours=2)

    assert expiry.tzinfo is UTC
    assert expiry > before


def test_admin_session_expiry_requires_positive_duration() -> None:
    try:
        admin_session_expires_at()
    except ValueError as exc:
        assert str(exc) == "admin session expiry duration must be positive"
    else:
        raise AssertionError("admin_session_expires_at should reject zero duration")
