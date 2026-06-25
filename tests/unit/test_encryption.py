import base64
from dataclasses import replace

import pytest
from cryptography.exceptions import InvalidTag

from intent_routing.security.encryption import EncryptedText, EnvelopeEncryptor


def _kek(byte: bytes = b"0") -> str:
    return base64.b64encode(byte * 32).decode("ascii")


def test_encrypts_and_decrypts_raw_text_without_plaintext_in_ciphertext() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())

    encrypted = encryptor.encrypt_text("보험금 청구 010-1234-5678")

    assert encrypted.algorithm == "AES-256-GCM"
    assert encrypted.key_id == "local-kek-001"
    assert b"010-1234-5678" not in encrypted.ciphertext
    assert encryptor.decrypt_text(encrypted) == "보험금 청구 010-1234-5678"


def test_same_plaintext_encrypts_with_distinct_iv_ciphertext_and_encrypted_dek() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())

    first = encryptor.encrypt_text("보험금 청구")
    second = encryptor.encrypt_text("보험금 청구")

    assert first.iv != second.iv
    assert first.ciphertext != second.ciphertext
    assert first.encrypted_dek != second.encrypted_dek
    assert first.encrypted_dek_iv != second.encrypted_dek_iv


def test_wrong_kek_fails_to_decrypt() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())
    wrong_encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek(b"1"))
    encrypted = encryptor.encrypt_text("보험금 청구")

    with pytest.raises(InvalidTag):
        wrong_encryptor.decrypt_text(encrypted)


@pytest.mark.parametrize(
    "field_name",
    [
        "ciphertext",
        "auth_tag",
        "encrypted_dek",
        "encrypted_dek_auth_tag",
        "iv",
        "encrypted_dek_iv",
    ],
)
def test_tampering_with_encrypted_payload_fails(field_name: str) -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())
    encrypted = encryptor.encrypt_text("보험금 청구")
    tampered = _tamper_encrypted_field(encrypted, field_name)

    with pytest.raises(InvalidTag):
        encryptor.decrypt_text(tampered)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("iv", b"0" * 11),
        ("auth_tag", b"0" * 15),
        ("encrypted_dek", b"0" * 31),
        ("encrypted_dek_iv", b"0" * 11),
        ("encrypted_dek_auth_tag", b"0" * 15),
    ],
)
def test_invalid_envelope_metadata_lengths_raise_value_error(
    field_name: str,
    value: bytes,
) -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())
    encrypted = encryptor.encrypt_text("보험금 청구")

    with pytest.raises(ValueError):
        encryptor.decrypt_text(_replace_encrypted_field(encrypted, field_name, value))


def test_moving_ciphertext_bytes_into_auth_tag_is_rejected() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())
    encrypted = encryptor.encrypt_text("보험금 청구")
    non_canonical = replace(
        encrypted,
        ciphertext=encrypted.ciphertext + encrypted.auth_tag[:1],
        auth_tag=encrypted.auth_tag[1:],
    )

    with pytest.raises(ValueError):
        encryptor.decrypt_text(non_canonical)


def test_invalid_base64_kek_raises_value_error() -> None:
    with pytest.raises(ValueError):
        EnvelopeEncryptor(kek_id="local-kek-001", kek_base64="not base64!!!")


def test_non_32_byte_kek_raises_value_error() -> None:
    short_kek = base64.b64encode(b"short").decode("ascii")

    with pytest.raises(ValueError):
        EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=short_kek)


def test_iv_and_auth_tag_lengths_are_aes_gcm_sizes() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())

    encrypted = encryptor.encrypt_text("보험금 청구")

    assert len(encrypted.iv) == 12
    assert len(encrypted.auth_tag) == 16
    assert len(encrypted.encrypted_dek_iv) == 12
    assert len(encrypted.encrypted_dek_auth_tag) == 16


def test_key_id_mismatch_raises_value_error() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())
    encrypted = encryptor.encrypt_text("보험금 청구")
    mismatched_key = replace(encrypted, key_id="local-kek-002")

    with pytest.raises(ValueError):
        encryptor.decrypt_text(mismatched_key)


def test_algorithm_mismatch_raises_value_error() -> None:
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_kek())
    encrypted = encryptor.encrypt_text("보험금 청구")
    mismatched_algorithm = replace(encrypted, algorithm="AES-128-GCM")

    with pytest.raises(ValueError):
        encryptor.decrypt_text(mismatched_algorithm)


def _tamper_encrypted_field(encrypted: EncryptedText, field_name: str) -> EncryptedText:
    if field_name == "ciphertext":
        return replace(encrypted, ciphertext=_flip_first_byte(encrypted.ciphertext))
    if field_name == "auth_tag":
        return replace(encrypted, auth_tag=_flip_first_byte(encrypted.auth_tag))
    if field_name == "encrypted_dek_auth_tag":
        return replace(
            encrypted,
            encrypted_dek_auth_tag=_flip_first_byte(encrypted.encrypted_dek_auth_tag),
        )
    if field_name == "encrypted_dek":
        return replace(encrypted, encrypted_dek=_flip_first_byte(encrypted.encrypted_dek))
    if field_name == "iv":
        return replace(encrypted, iv=_flip_first_byte(encrypted.iv))
    if field_name == "encrypted_dek_iv":
        return replace(
            encrypted,
            encrypted_dek_iv=_flip_first_byte(encrypted.encrypted_dek_iv),
        )
    raise AssertionError(f"unsupported encrypted field: {field_name}")


def _replace_encrypted_field(
    encrypted: EncryptedText,
    field_name: str,
    value: bytes,
) -> EncryptedText:
    if field_name == "iv":
        return replace(encrypted, iv=value)
    if field_name == "auth_tag":
        return replace(encrypted, auth_tag=value)
    if field_name == "encrypted_dek":
        return replace(encrypted, encrypted_dek=value)
    if field_name == "encrypted_dek_iv":
        return replace(encrypted, encrypted_dek_iv=value)
    if field_name == "encrypted_dek_auth_tag":
        return replace(encrypted, encrypted_dek_auth_tag=value)
    raise AssertionError(f"unsupported encrypted field: {field_name}")


def _flip_first_byte(value: bytes) -> bytes:
    return bytes([value[0] ^ 1]) + value[1:]
