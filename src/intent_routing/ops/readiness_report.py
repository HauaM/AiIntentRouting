from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

SECRET_KEYS = {
    "api_key",
    "authorization",
    "raw_text_kek_base64",
    "query_raw",
    "state_path",
}


def redact_secret_values(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in SECRET_KEYS:
                redacted[str(key)] = "REDACTED"
            else:
                redacted[str(key)] = redact_secret_values(item)
        return redacted
    if isinstance(value, list):
        return [redact_secret_values(item) for item in value]
    return value


def render_readiness_json(payload: Mapping[str, Any]) -> str:
    redacted = _with_final_status(redact_secret_values(dict(payload)))
    return json.dumps(redacted, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_readiness_markdown(payload: Mapping[str, Any]) -> str:
    redacted = _with_final_status(redact_secret_values(dict(payload)))
    lines = [
        f"# Pilot Readiness Evidence: {redacted.get('service_id', 'unknown')}",
        "",
        f"- Environment: `{redacted.get('environment', 'unknown')}`",
        f"- Release: `{redacted.get('release_version', 'unknown')}`",
        f"- Final status: **{redacted['final_status']}**",
        "",
        "## Checks",
        "",
        "| check | status |",
        "| --- | --- |",
        f"| healthz | {_check_status(redacted.get('healthz'))} |",
        f"| readyz | {_check_status(redacted.get('readyz'))} |",
        "",
        "## Thresholds",
        "",
        "| preset | gate | pass_rate | risk_pass_rate |",
        "| --- | --- | ---: | ---: |",
    ]

    thresholds = redacted.get("thresholds", {})
    if isinstance(thresholds, Mapping):
        for preset in ("strict", "balanced", "exploratory"):
            run = thresholds.get(preset)
            if isinstance(run, Mapping):
                lines.append(
                    "| {preset} | {gate} | {pass_rate} | {risk_pass_rate} |".format(
                        preset=preset,
                        gate="PASS" if run.get("gate_passed") else "FAIL",
                        pass_rate=_percent(run.get("pass_rate")),
                        risk_pass_rate=_percent(run.get("risk_pass_rate")),
                    )
                )

    lines.extend(
        ["", "## Runtime Smokes", "", "| case | decision | trace_id |", "| --- | --- | --- |"]
    )
    smokes = redacted.get("smokes", {})
    if isinstance(smokes, Mapping):
        for name, result in smokes.items():
            if isinstance(result, Mapping):
                lines.append(
                    f"| {name} | {result.get('decision', 'unknown')} | "
                    f"{result.get('trace_id', '')} |"
                )

    lines.append("")
    return "\n".join(lines)


def _with_final_status(payload: dict[str, Any]) -> dict[str, Any]:
    health_ok = _check_status(payload.get("healthz")) == "PASS"
    ready_ok = _check_status(payload.get("readyz")) == "PASS"
    thresholds = payload.get("thresholds", {})
    balanced_ok = False
    if isinstance(thresholds, Mapping):
        balanced = thresholds.get("balanced")
        balanced_ok = isinstance(balanced, Mapping) and bool(balanced.get("gate_passed"))
    payload["final_status"] = "PASS" if health_ok and ready_ok and balanced_ok else "FAIL"
    return payload


def _check_status(value: Any) -> str:
    if not isinstance(value, Mapping):
        return "FAIL"
    status_code = value.get("status_code")
    status_text = value.get("status")
    if status_code == 200 and status_text in {"ok", "ready"}:
        return "PASS"
    return "FAIL"


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"
