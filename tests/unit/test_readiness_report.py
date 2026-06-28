from __future__ import annotations

import json

from intent_routing.ops.readiness_report import (
    redact_secret_values,
    render_readiness_json,
    render_readiness_markdown,
)


def test_readiness_report_renders_checklist_without_secrets() -> None:
    payload = _payload()

    json_text = render_readiness_json(payload)
    markdown = render_readiness_markdown(payload)

    parsed = json.loads(json_text)
    assert parsed["service_id"] == "svc-test"
    assert parsed["final_status"] == "PASS"
    assert "| healthz | PASS |" in markdown
    assert "| readyz | PASS |" in markdown
    assert "| balanced | PASS | 80.0% | 100.0% |" in markdown
    for text in (json_text, markdown):
        assert "irt_secret_value" not in text
        assert "Authorization" not in text
        assert "RAW_TEXT_KEK_BASE64" not in text
        assert "super secret raw query" not in text
        assert ".secret.json" not in text


def test_redact_secret_values_recurses_through_nested_payloads() -> None:
    redacted = redact_secret_values(
        {
            "api_key": "irt_secret_value",
            "headers": {"Authorization": "Bearer irt_secret_value"},
            "items": [{"query_raw": "super secret raw query"}],
            "safe": "visible",
        }
    )

    assert redacted == {
        "api_key": "REDACTED",
        "headers": {"Authorization": "REDACTED"},
        "items": [{"query_raw": "REDACTED"}],
        "safe": "visible",
    }


def _payload() -> dict[str, object]:
    return {
        "service_id": "svc-test",
        "environment": "dev",
        "state_path": "var/pilot/svc-test.state.secret.json",
        "healthz": {"status_code": 200, "status": "ok"},
        "readyz": {"status_code": 200, "status": "ready"},
        "release_version": "rel-svc-test-001",
        "api_key": "irt_secret_value",
        "thresholds": {
            "balanced": {
                "gate_passed": True,
                "pass_rate": 0.8,
                "risk_pass_rate": 1.0,
            }
        },
        "smokes": {
            "confident": {"decision": "confident", "trace_id": "trace-1"},
            "risk": {"decision": "risk", "trace_id": "trace-2"},
            "off_topic": {"decision": "off_topic", "trace_id": "trace-3"},
            "fallback": {"decision": "fallback", "trace_id": "trace-4"},
            "clarify": {"decision": "clarify", "trace_id": "trace-5"},
        },
        "trace_audit": {
            "raw_query_viewed": True,
            "query_raw": "super secret raw query",
        },
    }
