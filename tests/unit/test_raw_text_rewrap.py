import base64

from intent_routing.db.models import IntentExample, RuntimeLog
from intent_routing.security.encryption import EncryptedText, EnvelopeEncryptor
from intent_routing.security.keyring import RawTextKeyring
from intent_routing.security.rewrap import (
    apply_intent_example_encrypted_text,
    apply_runtime_log_encrypted_query,
    intent_example_encrypted_text,
    reencrypt_envelope,
    runtime_log_encrypted_query,
)


def _kek(byte: bytes = b"0") -> str:
    return base64.b64encode(byte * 32).decode("ascii")


def test_reencrypt_envelope_uses_active_key_and_preserves_plaintext() -> None:
    old_encryptor = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1"))
    encrypted = old_encryptor.encrypt_text("raw query text")
    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={"old-kek": _kek(b"1")},
    )

    migrated = reencrypt_envelope(encrypted, keyring)

    assert migrated.key_id == "new-kek"
    assert migrated.ciphertext != encrypted.ciphertext
    assert keyring.decrypt_text(migrated) == "raw query text"


def test_reencrypt_envelope_returns_active_key_envelope_unchanged() -> None:
    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={},
    )
    encrypted = keyring.encrypt_text("already wrapped")

    migrated = reencrypt_envelope(encrypted, keyring)

    assert migrated is encrypted


def test_intent_example_adapter_reads_and_applies_complete_envelope() -> None:
    encrypted = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1")).encrypt_text(
        "example text"
    )
    example = _intent_example(encrypted)
    migrated = EnvelopeEncryptor(kek_id="new-kek", kek_base64=_kek(b"2")).encrypt_text(
        "example text"
    )

    assert intent_example_encrypted_text(example) == encrypted

    apply_intent_example_encrypted_text(example, migrated)

    assert intent_example_encrypted_text(example) == migrated
    assert example.text_raw_ciphertext == migrated.ciphertext
    assert example.text_raw_encrypted_dek == migrated.encrypted_dek
    assert example.text_raw_encrypted_dek_iv == migrated.encrypted_dek_iv
    assert example.text_raw_encrypted_dek_auth_tag == migrated.encrypted_dek_auth_tag
    assert example.text_raw_key_id == migrated.key_id
    assert example.text_raw_iv == migrated.iv
    assert example.text_raw_auth_tag == migrated.auth_tag
    assert example.text_raw_algorithm == migrated.algorithm


def test_runtime_log_adapter_returns_none_without_complete_envelope() -> None:
    encrypted = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1")).encrypt_text(
        "raw query text"
    )
    runtime_log = _runtime_log(encrypted)
    runtime_log.query_raw_auth_tag = None

    assert runtime_log_encrypted_query(runtime_log) is None


def test_runtime_log_adapter_reads_and_applies_complete_envelope() -> None:
    encrypted = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1")).encrypt_text(
        "raw query text"
    )
    runtime_log = _runtime_log(encrypted)
    migrated = EnvelopeEncryptor(kek_id="new-kek", kek_base64=_kek(b"2")).encrypt_text(
        "raw query text"
    )

    assert runtime_log_encrypted_query(runtime_log) == encrypted

    apply_runtime_log_encrypted_query(runtime_log, migrated)

    assert runtime_log_encrypted_query(runtime_log) == migrated
    assert runtime_log.query_raw_ciphertext == migrated.ciphertext
    assert runtime_log.query_raw_encrypted_dek == migrated.encrypted_dek
    assert runtime_log.query_raw_encrypted_dek_iv == migrated.encrypted_dek_iv
    assert runtime_log.query_raw_encrypted_dek_auth_tag == migrated.encrypted_dek_auth_tag
    assert runtime_log.query_raw_key_id == migrated.key_id
    assert runtime_log.query_raw_iv == migrated.iv
    assert runtime_log.query_raw_auth_tag == migrated.auth_tag
    assert runtime_log.query_raw_algorithm == migrated.algorithm


def _intent_example(encrypted: EncryptedText) -> IntentExample:
    return IntentExample(
        text_raw_ciphertext=encrypted.ciphertext,
        text_raw_encrypted_dek=encrypted.encrypted_dek,
        text_raw_encrypted_dek_iv=encrypted.encrypted_dek_iv,
        text_raw_encrypted_dek_auth_tag=encrypted.encrypted_dek_auth_tag,
        text_raw_key_id=encrypted.key_id,
        text_raw_iv=encrypted.iv,
        text_raw_auth_tag=encrypted.auth_tag,
        text_raw_algorithm=encrypted.algorithm,
    )


def _runtime_log(encrypted: EncryptedText) -> RuntimeLog:
    return RuntimeLog(
        query_raw_ciphertext=encrypted.ciphertext,
        query_raw_encrypted_dek=encrypted.encrypted_dek,
        query_raw_encrypted_dek_iv=encrypted.encrypted_dek_iv,
        query_raw_encrypted_dek_auth_tag=encrypted.encrypted_dek_auth_tag,
        query_raw_key_id=encrypted.key_id,
        query_raw_iv=encrypted.iv,
        query_raw_auth_tag=encrypted.auth_tag,
        query_raw_algorithm=encrypted.algorithm,
    )
