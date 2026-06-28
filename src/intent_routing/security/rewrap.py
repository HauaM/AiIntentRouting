from __future__ import annotations

from intent_routing.db.models import IntentExample, RuntimeLog
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring


def reencrypt_envelope(
    encrypted: EncryptedText,
    keyring: RawTextKeyring,
) -> EncryptedText:
    if encrypted.key_id == keyring.active_key_id:
        return encrypted
    plaintext = keyring.decrypt_text(encrypted)
    return keyring.encrypt_text(plaintext)


def intent_example_encrypted_text(example: IntentExample) -> EncryptedText:
    return EncryptedText(
        ciphertext=example.text_raw_ciphertext,
        encrypted_dek=example.text_raw_encrypted_dek,
        encrypted_dek_iv=example.text_raw_encrypted_dek_iv,
        encrypted_dek_auth_tag=example.text_raw_encrypted_dek_auth_tag,
        key_id=example.text_raw_key_id,
        iv=example.text_raw_iv,
        auth_tag=example.text_raw_auth_tag,
        algorithm=example.text_raw_algorithm,
    )


def apply_intent_example_encrypted_text(
    example: IntentExample,
    encrypted: EncryptedText,
) -> None:
    example.text_raw_ciphertext = encrypted.ciphertext
    example.text_raw_encrypted_dek = encrypted.encrypted_dek
    example.text_raw_encrypted_dek_iv = encrypted.encrypted_dek_iv
    example.text_raw_encrypted_dek_auth_tag = encrypted.encrypted_dek_auth_tag
    example.text_raw_key_id = encrypted.key_id
    example.text_raw_iv = encrypted.iv
    example.text_raw_auth_tag = encrypted.auth_tag
    example.text_raw_algorithm = encrypted.algorithm


def runtime_log_encrypted_query(runtime_log: RuntimeLog) -> EncryptedText | None:
    ciphertext = runtime_log.query_raw_ciphertext
    encrypted_dek = runtime_log.query_raw_encrypted_dek
    encrypted_dek_iv = runtime_log.query_raw_encrypted_dek_iv
    encrypted_dek_auth_tag = runtime_log.query_raw_encrypted_dek_auth_tag
    key_id = runtime_log.query_raw_key_id
    iv = runtime_log.query_raw_iv
    auth_tag = runtime_log.query_raw_auth_tag
    algorithm = runtime_log.query_raw_algorithm

    if (
        ciphertext is None
        or encrypted_dek is None
        or encrypted_dek_iv is None
        or encrypted_dek_auth_tag is None
        or key_id is None
        or iv is None
        or auth_tag is None
        or algorithm is None
    ):
        return None

    return EncryptedText(
        ciphertext=ciphertext,
        encrypted_dek=encrypted_dek,
        encrypted_dek_iv=encrypted_dek_iv,
        encrypted_dek_auth_tag=encrypted_dek_auth_tag,
        key_id=key_id,
        iv=iv,
        auth_tag=auth_tag,
        algorithm=algorithm,
    )


def apply_runtime_log_encrypted_query(
    runtime_log: RuntimeLog,
    encrypted: EncryptedText,
) -> None:
    runtime_log.query_raw_ciphertext = encrypted.ciphertext
    runtime_log.query_raw_encrypted_dek = encrypted.encrypted_dek
    runtime_log.query_raw_encrypted_dek_iv = encrypted.encrypted_dek_iv
    runtime_log.query_raw_encrypted_dek_auth_tag = encrypted.encrypted_dek_auth_tag
    runtime_log.query_raw_key_id = encrypted.key_id
    runtime_log.query_raw_iv = encrypted.iv
    runtime_log.query_raw_auth_tag = encrypted.auth_tag
    runtime_log.query_raw_algorithm = encrypted.algorithm
