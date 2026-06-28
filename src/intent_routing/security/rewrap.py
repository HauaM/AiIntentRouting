from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

from intent_routing.db.models import IntentExample, RuntimeLog
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring


class RawTextKeyCountDetail(TypedDict):
    legacy: dict[str, int]
    active: dict[str, int]
    total: int


RawTextKeyCountsByTable = dict[str, RawTextKeyCountDetail]
RawTextFailureCounts = dict[str, dict[str, dict[str, int]]]


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


def raw_text_key_counts_by_table(
    key_counts: Mapping[str, object],
    *,
    included_tables: Sequence[str],
    active_key_id: str,
) -> RawTextKeyCountsByTable:
    counts_by_table: RawTextKeyCountsByTable = {}
    for table_name in included_tables:
        legacy_counts: dict[str, int] = {}
        active_counts: dict[str, int] = {}
        total = 0
        raw_table_counts = key_counts.get(table_name, {})
        if isinstance(raw_table_counts, Mapping):
            for key_id, raw_count in raw_table_counts.items():
                if not isinstance(key_id, str) or not isinstance(raw_count, int):
                    continue
                total += raw_count
                if key_id == active_key_id:
                    active_counts[key_id] = raw_count
                else:
                    legacy_counts[key_id] = raw_count
        counts_by_table[table_name] = {
            "legacy": legacy_counts,
            "active": active_counts,
            "total": total,
        }
    return counts_by_table


def build_raw_text_rewrap_report(
    *,
    rewrap_run_id: str,
    service_id: str,
    dry_run: bool,
    status: str,
    target_key_id: str,
    source_key_ids: Sequence[str],
    included_tables: Sequence[str],
    key_counts: RawTextKeyCountsByTable,
    before_key_counts: RawTextKeyCountsByTable,
    after_key_counts: RawTextKeyCountsByTable,
    failure_counts: RawTextFailureCounts,
    scanned_by_table: Mapping[str, int],
    limit: int,
    batch_size: int,
    scanned_count: int,
    rewrapped_count: int,
    skipped_count: int,
    failed_count: int,
) -> dict[str, object]:
    return {
        "rewrap_run_id": rewrap_run_id,
        "service_id": service_id,
        "dry_run": dry_run,
        "status": status,
        "target_key_id": target_key_id,
        "source_key_ids": list(source_key_ids),
        "included_tables": list(included_tables),
        "key_counts": key_counts,
        "before_key_counts": before_key_counts,
        "after_key_counts": after_key_counts,
        "failure_counts": failure_counts,
        "scanned_by_table": dict(scanned_by_table),
        "limit": limit,
        "batch_size": batch_size,
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
        ("Status", report["status"]),
        ("Target key ID", report["target_key_id"]),
        ("Source key IDs", _markdown_list_value(report["source_key_ids"])),
        ("Included tables", _markdown_list_value(report["included_tables"])),
        ("Limit", report["limit"]),
        ("Batch size", report["batch_size"]),
        ("Scanned by table", _markdown_count_mapping(report["scanned_by_table"])),
        ("Scanned count", report["scanned_count"]),
        ("Rewrapped count", report["rewrapped_count"]),
        ("Skipped count", report["skipped_count"]),
        ("Failed count", report["failed_count"]),
        ("Plaintext exported", report["plaintext_exported"]),
    ]
    lines = [
        "# Raw Text Rewrap Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    lines.extend(f"| {field} | {value} |" for field, value in rows)
    lines.extend(_markdown_key_count_lines(report.get("key_counts", {})))
    lines.extend(
        _markdown_snapshot_key_count_lines(
            label="Before",
            raw_key_counts=report.get("before_key_counts", {}),
            report=report,
        )
    )
    lines.extend(
        _markdown_snapshot_key_count_lines(
            label="After",
            raw_key_counts=report.get("after_key_counts", {}),
            report=report,
        )
    )
    lines.extend(_markdown_failure_count_lines(report.get("failure_counts", {})))
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


def _markdown_count_mapping(value: object) -> str:
    if not isinstance(value, Mapping):
        return str(value)
    return ", ".join(
        f"{key}={count}"
        for key, count in value.items()
        if isinstance(key, str) and isinstance(count, int)
    ) or "(none)"


def _markdown_key_count_lines(raw_key_counts: object) -> list[str]:
    lines = [
        "",
        "## Key Counts",
        "",
        "| Table | Key role | Key ID | Count |",
        "| --- | --- | --- | --- |",
    ]
    if not isinstance(raw_key_counts, Mapping):
        return lines
    for table_name, raw_detail in raw_key_counts.items():
        if not isinstance(table_name, str) or not isinstance(raw_detail, Mapping):
            continue
        for key_role in ("legacy", "active"):
            raw_counts = raw_detail.get(key_role, {})
            if not isinstance(raw_counts, Mapping):
                continue
            for key_id, count in raw_counts.items():
                if not isinstance(key_id, str) or not isinstance(count, int):
                    continue
                lines.append(f"| {table_name} | {key_role} | {key_id} | {count} |")
    return lines


def _markdown_snapshot_key_count_lines(
    *,
    label: str,
    raw_key_counts: object,
    report: Mapping[str, object],
) -> list[str]:
    lines = [
        "",
        f"## {label} Key Counts",
        "",
        "| Snapshot | Table | Key role | Key ID | Count |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not isinstance(raw_key_counts, Mapping):
        return lines
    source_key_ids = _report_string_list(report.get("source_key_ids", []))
    target_key_id = report.get("target_key_id")
    active_key_ids = [target_key_id] if isinstance(target_key_id, str) else []
    for table_name, raw_detail in raw_key_counts.items():
        if not isinstance(table_name, str) or not isinstance(raw_detail, Mapping):
            continue
        for key_role, expected_key_ids in (
            ("legacy", source_key_ids),
            ("active", active_key_ids),
        ):
            raw_counts = raw_detail.get(key_role, {})
            if not isinstance(raw_counts, Mapping):
                continue
            key_ids = sorted(
                set(expected_key_ids).union(
                    key_id for key_id in raw_counts if isinstance(key_id, str)
                )
            )
            for key_id in key_ids:
                count = raw_counts.get(key_id, 0)
                if isinstance(count, int):
                    lines.append(
                        f"| {label} | {table_name} | {key_role} | {key_id} | {count} |"
                    )
    return lines


def _markdown_failure_count_lines(raw_failure_counts: object) -> list[str]:
    lines = [
        "",
        "## Failure Counts",
        "",
        "| Table | Key ID | Reason | Count |",
        "| --- | --- | --- | --- |",
    ]
    if not isinstance(raw_failure_counts, Mapping):
        return lines
    for table_name, raw_key_counts in raw_failure_counts.items():
        if not isinstance(table_name, str) or not isinstance(raw_key_counts, Mapping):
            continue
        for key_id, raw_reason_counts in raw_key_counts.items():
            if not isinstance(key_id, str) or not isinstance(raw_reason_counts, Mapping):
                continue
            for reason, count in raw_reason_counts.items():
                if isinstance(reason, str) and isinstance(count, int):
                    lines.append(f"| {table_name} | {key_id} | {reason} | {count} |")
    return lines


def _report_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
