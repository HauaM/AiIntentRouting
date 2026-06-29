from __future__ import annotations

from fastapi import Request

from intent_routing.db.models import RuntimeLog
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring
from intent_routing.security.rewrap import runtime_log_encrypted_query


def runtime_log_encrypted_raw_query(runtime_log: RuntimeLog) -> EncryptedText | None:
    return runtime_log_encrypted_query(runtime_log)


def decrypt_runtime_raw_query(
    runtime_log: RuntimeLog,
    keyring: RawTextKeyring,
) -> str | None:
    encrypted = runtime_log_encrypted_raw_query(runtime_log)
    if encrypted is None:
        return None
    return keyring.decrypt_text(encrypted)


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
