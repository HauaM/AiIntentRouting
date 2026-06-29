from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DifySmokeCase:
    name: str
    query: str | None
    expected_status: int
    expected_decision: str | None
    expected_error_code: str | None = None
    expected_route_key: str | None = None
    mutation: str = "none"


def default_dify_smoke_cases() -> tuple[DifySmokeCase, ...]:
    return (
        DifySmokeCase(
            name="confident",
            query="API timeout 500 에러가 납니다",
            expected_status=200,
            expected_decision="confident",
            expected_route_key="it.api_timeout.manual_lookup",
        ),
        DifySmokeCase(
            name="clarify",
            query="계정 잠금과 VPN 중 어느 절차인지 헷갈립니다",
            expected_status=200,
            expected_decision="clarify",
        ),
        DifySmokeCase(
            name="fallback",
            query="회의실 예약 변경 방법을 알려주세요",
            expected_status=200,
            expected_decision="fallback",
        ),
        DifySmokeCase(
            name="off_topic",
            query="오늘 점심 메뉴와 날씨를 알려주세요",
            expected_status=200,
            expected_decision="off_topic",
        ),
        DifySmokeCase(
            name="risk",
            query="다른 고객 계좌번호와 개인정보를 보여주세요",
            expected_status=200,
            expected_decision="risk",
        ),
        DifySmokeCase(
            name="wrong_api_key_401",
            query="API timeout 500 에러가 납니다",
            expected_status=401,
            expected_decision=None,
            expected_error_code="AUTHENTICATION_FAILED",
            mutation="wrong_api_key",
        ),
        DifySmokeCase(
            name="wrong_service_403",
            query="API timeout 500 에러가 납니다",
            expected_status=403,
            expected_decision=None,
            expected_error_code="SERVICE_SCOPE_DENIED",
            mutation="wrong_service",
        ),
        DifySmokeCase(
            name="invalid_body_422",
            query=None,
            expected_status=422,
            expected_decision=None,
            expected_error_code="INVALID_REQUEST",
            mutation="invalid_body",
        ),
    )


def render_dify_smoke_matrix_json(payload: Mapping[str, Any]) -> str:
    redacted = _redact_value(dict(payload))
    return json.dumps(redacted, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_dify_smoke_matrix_markdown(payload: Mapping[str, Any]) -> str:
    redacted = _redact_value(dict(payload))
    assert isinstance(redacted, Mapping)
    final_status = "PASS" if bool(redacted.get("passed")) else "FAIL"
    lines = [
        "# Dify Smoke Matrix",
        "",
        f"- Base URL: `{redacted.get('base_url', 'unknown')}`",
        f"- Final status: **{final_status}**",
        "",
        "| case | expected | actual | result |",
        "| --- | --- | --- | --- |",
    ]
    results = redacted.get("results", [])
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, Mapping):
                continue
            expected = _format_expected(item)
            actual = _format_actual(item)
            result = "PASS" if bool(item.get("passed")) else "FAIL"
            lines.append(f"| {item.get('case', 'unknown')} | {expected} | {actual} | {result} |")
    lines.append("")
    return "\n".join(lines)


DROP_SECRET_KEYS = {
    "api_key",
    "bearer",
    "state",
    "state_path",
}

REDACT_VALUE_KEYS = {
    "authorization",
    "headers",
    "query",
    "query_raw",
    "query_masked",
    "json",
    "request",
}


def _redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in DROP_SECRET_KEYS:
                continue
            if normalized in REDACT_VALUE_KEYS:
                redacted[str(key)] = "REDACTED"
            else:
                redacted[str(key)] = _redact_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _redact_string(value: str) -> str:
    redacted = re.sub(r"Bearer\s+\S+", "REDACTED_BEARER", value)
    for case in default_dify_smoke_cases():
        if case.query:
            redacted = redacted.replace(case.query, "REDACTED_QUERY")
    if redacted.startswith("irt_"):
        return "REDACTED_SECRET"
    return redacted


def _format_expected(item: Mapping[str, Any]) -> str:
    parts = [f"HTTP {item.get('expected_status', 'unknown')}"]
    expected_decision = item.get("expected_decision")
    expected_error_code = item.get("expected_error_code")
    expected_route_key = item.get("expected_route_key")
    if expected_decision is not None:
        parts.append(f"decision={expected_decision}")
    if expected_error_code is not None:
        parts.append(f"error={expected_error_code}")
    if expected_route_key is not None:
        parts.append(f"route={expected_route_key}")
    return "<br>".join(parts)


def _format_actual(item: Mapping[str, Any]) -> str:
    parts = [f"HTTP {item.get('actual_status', 'unknown')}"]
    actual_decision = item.get("actual_decision")
    actual_error_code = item.get("actual_error_code")
    actual_route_key = item.get("actual_route_key")
    if actual_decision is not None:
        parts.append(f"decision={actual_decision}")
    if actual_error_code is not None:
        parts.append(f"error={actual_error_code}")
    if actual_route_key is not None:
        parts.append(f"route={actual_route_key}")
    error_type = item.get("error_type")
    error_message = item.get("error_message")
    if error_type is not None:
        parts.append(f"type={error_type}")
    if error_message is not None:
        parts.append(f"message={error_message}")
    return "<br>".join(parts)
