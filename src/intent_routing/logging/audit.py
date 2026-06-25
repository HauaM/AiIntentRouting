from __future__ import annotations

from fastapi import Request

from intent_routing.db.models import RuntimeLog
from intent_routing.security.encryption import EncryptedText, EnvelopeEncryptor


def runtime_log_encrypted_raw_query(runtime_log: RuntimeLog) -> EncryptedText | None:
    if (
        runtime_log.query_raw_ciphertext is None
        or runtime_log.query_raw_encrypted_dek is None
        or runtime_log.query_raw_encrypted_dek_iv is None
        or runtime_log.query_raw_encrypted_dek_auth_tag is None
        or runtime_log.query_raw_key_id is None
        or runtime_log.query_raw_iv is None
        or runtime_log.query_raw_auth_tag is None
        or runtime_log.query_raw_algorithm is None
    ):
        return None
    return EncryptedText(
        ciphertext=runtime_log.query_raw_ciphertext,
        encrypted_dek=runtime_log.query_raw_encrypted_dek,
        encrypted_dek_iv=runtime_log.query_raw_encrypted_dek_iv,
        encrypted_dek_auth_tag=runtime_log.query_raw_encrypted_dek_auth_tag,
        key_id=runtime_log.query_raw_key_id,
        iv=runtime_log.query_raw_iv,
        auth_tag=runtime_log.query_raw_auth_tag,
        algorithm=runtime_log.query_raw_algorithm,
    )


def decrypt_runtime_raw_query(
    runtime_log: RuntimeLog,
    encryptor: EnvelopeEncryptor,
) -> str | None:
    encrypted = runtime_log_encrypted_raw_query(runtime_log)
    if encrypted is None:
        return None
    return encryptor.decrypt_text(encrypted)


def raw_query_view_after_state(runtime_log: RuntimeLog) -> dict[str, object]:
    return {
        "trace_id": runtime_log.trace_id,
        "service_id": runtime_log.service_id,
        "query_raw_viewed": True,
    }


def source_ip_from_request(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host
