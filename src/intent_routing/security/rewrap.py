from __future__ import annotations

from collections.abc import Mapping, Sequence

from intent_routing.db.models import IntentExample, RuntimeLog
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring

RAW_TEXT_REWRAP_TABLES = ("intent_examples", "runtime_logs")
RAW_TEXT_REWRAP_INCLUDE_ALIASES = {
    "intent-examples": ("intent_examples",),
    "runtime-logs": ("runtime_logs",),
    "both": RAW_TEXT_REWRAP_TABLES,
}


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


def normalize_raw_text_rewrap_includes(includes: Sequence[str]) -> list[str]:
    included_tables: list[str] = []
    for include in includes:
        aliases = RAW_TEXT_REWRAP_INCLUDE_ALIASES.get(include)
        if aliases is None:
            raise ValueError(f"unsupported raw text rewrap include: {include}")
        for table_name in aliases:
            if table_name not in included_tables:
                included_tables.append(table_name)
    return included_tables


def source_key_ids_from_counts(
    key_counts: Mapping[str, object],
    *,
    included_tables: Sequence[str],
    active_key_id: str,
) -> list[str]:
    source_key_ids: set[str] = set()
    for table_name in included_tables:
        table_counts = key_counts.get(table_name, {})
        if not isinstance(table_counts, Mapping):
            continue
        for key_id in table_counts:
            if isinstance(key_id, str) and key_id != active_key_id:
                source_key_ids.add(key_id)
    return sorted(source_key_ids)


def build_raw_text_rewrap_report(
    *,
    rewrap_run_id: str,
    service_id: str,
    dry_run: bool,
    target_key_id: str,
    source_key_ids: Sequence[str],
    included_tables: Sequence[str],
    scanned_count: int,
    rewrapped_count: int,
    skipped_count: int,
    failed_count: int,
) -> dict[str, object]:
    return {
        "rewrap_run_id": rewrap_run_id,
        "service_id": service_id,
        "dry_run": dry_run,
        "target_key_id": target_key_id,
        "source_key_ids": list(source_key_ids),
        "included_tables": list(included_tables),
        "scanned_count": scanned_count,
        "rewrapped_count": rewrapped_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "plaintext_exported": False,
    }


def render_raw_text_rewrap_markdown(report: Mapping[str, object]) -> str:
    rows = [
        ("Rewrap run ID", report["rewrap_run_id"]),
        ("Service ID", report["service_id"]),
        ("Dry run", report["dry_run"]),
        ("Target key ID", report["target_key_id"]),
        ("Source key IDs", _markdown_list_value(report["source_key_ids"])),
        ("Included tables", _markdown_list_value(report["included_tables"])),
        ("Scanned count", report["scanned_count"]),
        ("Rewrapped count", report["rewrapped_count"]),
        ("Skipped count", report["skipped_count"]),
        ("Failed count", report["failed_count"]),
        ("Plaintext exported", report["plaintext_exported"]),
    ]
    lines = [
        "# Raw Text Rewrap Report",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    lines.extend(f"| {field} | {value} |" for field, value in rows)
    return "\n".join(lines) + "\n"


def raw_text_rewrap_audit_after_state(
    report: Mapping[str, object],
    *,
    approval_id: str,
) -> dict[str, object]:
    return {
        "approval_id": approval_id,
        "rewrap_run_id": report["rewrap_run_id"],
        "rewrapped_count": report["rewrapped_count"],
        "scanned_count": report["scanned_count"],
        "skipped_count": report["skipped_count"],
        "failed_count": report["failed_count"],
        "target_key_id": report["target_key_id"],
    }


def _markdown_list_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "(none)"
    return str(value)
