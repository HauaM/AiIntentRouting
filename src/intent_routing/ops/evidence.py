from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEY_NAMES = {
    "admin_token",
    "api_key",
    "authorization",
    "kek_base64",
    "legacy_kek_base64",
    "legacy_keks_json",
    "password",
    "query_raw",
    "query_raw_auth_tag",
    "query_raw_ciphertext",
    "query_raw_encrypted_dek",
    "query_raw_encrypted_dek_auth_tag",
    "query_raw_encrypted_dek_iv",
    "query_raw_iv",
    "raw_text_kek_base64",
    "raw_text_legacy_keks_json",
    "secret",
    "state_path",
    "text_raw",
    "text_raw_auth_tag",
    "text_raw_ciphertext",
    "text_raw_encrypted_dek",
    "text_raw_encrypted_dek_auth_tag",
    "text_raw_encrypted_dek_iv",
    "text_raw_iv",
    "x_admin_token",
}
SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "admin_token",
    "api_key",
    "password",
    "secret",
    "kek_base64",
    "kekbase64",
    "keks_json",
    "legacy_kek",
    "legacy_keks",
    "legacykek",
    "legacykeks",
    "query_raw",
    "text_raw",
    "ciphertext",
    "encrypted_dek",
    "auth_tag",
)
KNOWN_SECRET_VALUES = (
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=",
)
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"irt_secret[A-Za-z0-9._:-]*", re.IGNORECASE),
    re.compile(r"RAW_TEXT_LEGACY_KEKS_JSON\s*[:=]\s*\{[^}]*\}", re.IGNORECASE),
    re.compile(
        r"\b(?:query_raw|text_raw)(?:_[A-Za-z0-9]+)*\s*[:=]\s*[^;\s|,]+",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:query_raw|text_raw)(?:_[A-Za-z0-9]+)+\b", re.IGNORECASE),
    re.compile(
        r"\b(?:ciphertext|encrypted[_-]?dek)\s*[:=]\s*[^;\s|,]+",
        re.IGNORECASE,
    ),
    re.compile(r"\bapi[_-]?key\s*[:=]\s*[^;\s|,]+", re.IGNORECASE),
    re.compile(r"\bX-API-Key\s*:\s*[^;\s|,]+", re.IGNORECASE),
    re.compile(r"\birt_[A-Za-z0-9_-]{20,}\b", re.IGNORECASE),
    re.compile(r"\S*\.state\.secret\.json\b", re.IGNORECASE),
    re.compile(r"\bvar/pilot/\S*secret\.json\b", re.IGNORECASE),
    re.compile(r"RAW_TEXT_KEK_BASE64", re.IGNORECASE),
    re.compile(r"RAW_TEXT_LEGACY_KEKS_JSON", re.IGNORECASE),
    re.compile(r"Authorization", re.IGNORECASE),
    re.compile(r"\bquery_raw\b", re.IGNORECASE),
    re.compile(r"\btext_raw\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_]*kek_base64\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])"),
    *[re.compile(re.escape(value)) for value in KNOWN_SECRET_VALUES],
)
URLSAFE_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{43,96})(?![A-Za-z0-9_-])"
)
REDACTED = "REDACTED"


def render_ops_evidence_json(payload: Mapping[str, Any]) -> str:
    redacted = redact_ops_evidence(payload)
    return json.dumps(redacted, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_ops_evidence_markdown(payload: Mapping[str, Any]) -> str:
    redacted = redact_ops_evidence(payload)
    active_release = _mapping(redacted.get("active_release"))
    readyz = _mapping(redacted.get("readyz"))
    runtime_metrics = _mapping(redacted.get("runtime_metrics"))
    key_summary = _mapping(redacted.get("raw_text_key_summary"))
    rewrap_status = _mapping(redacted.get("latest_rewrap_runs_status"))
    retention = _mapping(
        redacted.get("runtime_raw_query_retention")
        or runtime_metrics.get("raw_query_retention")
    )
    audit_evidence = _mapping(redacted.get("audit_evidence"))

    lines = [
        "# Intent Routing Operations Evidence",
        "",
        "## Service",
        "",
        f"- Service ID: `{redacted.get('service_id', 'unknown')}`",
        f"- Environment: `{redacted.get('environment', 'unknown')}`",
        f"- Collected at: `{redacted.get('collected_at', 'unknown')}`",
        f"- Active release: `{active_release.get('release_version', 'unknown')}`",
        f"- Active release environment: `{active_release.get('environment', 'unknown')}`",
        "",
        "## Readiness",
        "",
        f"- Readyz: `{readyz.get('status', 'unknown')}` (`{readyz.get('status_code', 'unknown')}`)",
        "",
        "## Runtime Metrics",
        "",
        f"- Window hours: `{runtime_metrics.get('window_hours', 'unknown')}`",
        f"- Request count: `{runtime_metrics.get('request_count', 0)}`",
        f"- Latency p50 ms: `{_latency_value(runtime_metrics, 'p50')}`",
        f"- Latency p95 ms: `{_latency_value(runtime_metrics, 'p95')}`",
        f"- Latency max ms: `{_latency_value(runtime_metrics, 'max')}`",
        "",
        "### Decision Counts",
        "",
        "| decision | count |",
        "| --- | ---: |",
    ]
    lines.extend(_count_rows(runtime_metrics.get("decision_counts")))
    lines.extend(
        [
            "",
            "### Error Counts",
            "",
            "| error | count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(_count_rows(runtime_metrics.get("error_counts")))
    lines.extend(
        [
            "",
            "### Top Route Keys",
            "",
            "| route key | count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(_route_key_rows(runtime_metrics.get("top_route_keys")))

    lines.extend(
        [
            "",
            "## Raw Text Key Summary",
            "",
            f"- Active raw text key: `{key_summary.get('active_key_id', 'unknown')}`",
            "",
            "### Intent Examples",
            "",
            "| key id | count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(_key_summary_rows(key_summary.get("intent_examples")))
    lines.extend(
        [
            "",
            "### Runtime Logs",
            "",
            "| key id | state | count |",
            "| --- | --- | ---: |",
        ]
    )
    lines.extend(_runtime_key_summary_rows(key_summary.get("runtime_logs")))

    lines.extend(
        [
            "",
            "## KEK Rewrap Runs",
            "",
        ]
    )
    if rewrap_status:
        collected = str(bool(rewrap_status.get("collected"))).lower()
        lines.append(f"- Rewrap runs collected: `{collected}`")
        reason = rewrap_status.get("reason")
        if reason:
            lines.append(f"- Rewrap runs collection reason: `{reason}`")
        lines.append("")
    lines.extend(
        [
            "| run id | status | dry run | scanned | rewrapped | skipped | failed |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(_rewrap_rows(redacted.get("latest_rewrap_runs")))

    lines.extend(
        [
            "",
            "## Runtime Raw-Query Retention",
            "",
            f"- Raw query encrypted count: `{retention.get('encrypted_count', 0)}`",
            f"- Raw query redacted count: `{retention.get('redacted_count', 0)}`",
            "",
            "## Audit Evidence",
            "",
            f"- Audit event count: `{audit_evidence.get('count', 0)}`",
            "",
            "| event type | actor | target | created at |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(_audit_rows(audit_evidence.get("events")))
    lines.extend(
        [
            "",
            "## Secret Redaction Statement",
            "",
            "Sensitive fields and secret-looking substrings were redacted recursively.",
            f"Redaction marker: `{REDACTED}`.",
            (
                "No raw plaintext, bearer tokens, API keys, KEK material, ciphertext, "
                "encrypted DEKs, or secret state paths are intentionally exported."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def redact_ops_evidence(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        redacted_count = 0
        for raw_key, item in value.items():
            key = str(raw_key)
            if _is_sensitive_key(key):
                redacted_count += 1
                redacted[_redacted_key(redacted, redacted_count)] = REDACTED
                continue
            safe_key = _redact_text(key)
            if not safe_key or _is_sensitive_key(safe_key):
                redacted_count += 1
                redacted[_redacted_key(redacted, redacted_count)] = redact_ops_evidence(item)
                continue
            redacted[safe_key] = redact_ops_evidence(item)
        return redacted
    if isinstance(value, list):
        return [redact_ops_evidence(item) for item in value]
    if isinstance(value, tuple):
        return [redact_ops_evidence(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    return (
        normalized in SENSITIVE_KEY_NAMES
        or any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)
    )


def _normalize_key(key: str) -> str:
    underscored = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    return re.sub(r"[^a-z0-9]+", "_", underscored.lower()).strip("_")


def _redact_text(value: str) -> str:
    redacted = value
    for pattern in SENSITIVE_TEXT_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    redacted = URLSAFE_TOKEN_PATTERN.sub(_redact_urlsafe_token_match, redacted)
    return re.sub(r"(?:REDACTED[\s,;:=]*){2,}", f"{REDACTED} ", redacted).strip()


def _redact_urlsafe_token_match(match: re.Match[str]) -> str:
    token = match.group(1)
    if _looks_like_generated_urlsafe_token(token):
        return REDACTED
    return token


def _looks_like_generated_urlsafe_token(token: str) -> bool:
    if "." in token or len(token) < 43:
        return False
    has_upper = any(character.isupper() for character in token)
    has_lower = any(character.islower() for character in token)
    has_digit = any(character.isdigit() for character in token)
    has_urlsafe_symbol = any(character in {"-", "_"} for character in token)
    if not (has_upper and has_lower and (has_digit or has_urlsafe_symbol)):
        return False
    unique_ratio = len(set(token)) / len(token)
    return unique_ratio >= 0.45


def _redacted_key(existing: Mapping[str, Any], number: int) -> str:
    candidate = f"redacted_field_{number}"
    while candidate in existing:
        number += 1
        candidate = f"redacted_field_{number}"
    return candidate


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _latency_value(metrics: Mapping[str, Any], key: str) -> Any:
    latency = _mapping(metrics.get("latency_ms"))
    value = latency.get(key)
    return value if value is not None else "none"


def _count_rows(value: Any) -> list[str]:
    if not isinstance(value, Mapping) or not value:
        return ["| none | 0 |"]
    return [
        f"| {_markdown_cell(name)} | {_markdown_cell(count)} |"
        for name, count in value.items()
    ]


def _route_key_rows(value: Any) -> list[str]:
    rows = _sequence_of_mappings(value)
    if not rows:
        return ["| none | 0 |"]
    return [
        "| {route_key} | {count} |".format(
            route_key=_markdown_cell(row.get("route_key", "unknown")),
            count=_markdown_cell(row.get("count", 0)),
        )
        for row in rows
    ]


def _key_summary_rows(value: Any) -> list[str]:
    rows = _sequence_of_mappings(value)
    if not rows:
        return ["| none | 0 |"]
    return [
        f"| {_markdown_cell(row.get('key_id', 'none'))} | {_markdown_cell(row.get('count', 0))} |"
        for row in rows
    ]


def _runtime_key_summary_rows(value: Any) -> list[str]:
    rows = _sequence_of_mappings(value)
    if not rows:
        return ["| none | none | 0 |"]
    return [
        "| {key_id} | {state} | {count} |".format(
            key_id=_markdown_cell(row.get("key_id", "none")),
            state=_markdown_cell(row.get("state", "encrypted")),
            count=_markdown_cell(row.get("count", 0)),
        )
        for row in rows
    ]


def _rewrap_rows(value: Any) -> list[str]:
    rows = _sequence_of_mappings(value)
    if not rows:
        return ["| none | none | false | 0 | 0 | 0 | 0 |"]
    return [
        (
            "| {run_id} | {status} | {dry_run} | {scanned} | "
            "{rewrapped} | {skipped} | {failed} |"
        ).format(
            run_id=_markdown_cell(row.get("rewrap_run_id", "unknown")),
            status=_markdown_cell(row.get("status", "unknown")),
            dry_run=_markdown_cell(row.get("dry_run", "unknown")),
            scanned=_markdown_cell(row.get("scanned_count", 0)),
            rewrapped=_markdown_cell(row.get("rewrapped_count", 0)),
            skipped=_markdown_cell(row.get("skipped_count", 0)),
            failed=_markdown_cell(row.get("failed_count", 0)),
        )
        for row in rows
    ]


def _audit_rows(value: Any) -> list[str]:
    rows = _sequence_of_mappings(value)
    if not rows:
        return ["| none | none | none | none |"]
    return [
        "| {event_type} | {actor} | {target} | {created_at} |".format(
            event_type=_markdown_cell(row.get("event_type", "unknown")),
            actor=_markdown_cell(row.get("actor_id", "unknown")),
            target=_markdown_cell(row.get("target_id", "unknown")),
            created_at=_markdown_cell(row.get("created_at", "unknown")),
        )
        for row in rows
    ]


def _markdown_cell(value: Any) -> str:
    text = str(value)
    text = re.sub(r"[\r\n]+", " ", text)
    return text.replace("|", r"\|")


def _sequence_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, Mapping)]
