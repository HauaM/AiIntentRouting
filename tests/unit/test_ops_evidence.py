from __future__ import annotations

import json

from intent_routing.ops.evidence import (
    render_ops_evidence_json,
    render_ops_evidence_markdown,
)

FORBIDDEN_MARKERS = (
    "query_raw",
    "text_raw",
    "Authorization",
    "RAW_TEXT_KEK_BASE64",
    "irt_secret",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=",
    "Bearer task7-token",
    "ciphertext-value",
    "encrypted-dek-value",
)


def test_ops_evidence_json_and_markdown_include_required_evidence() -> None:
    payload = _payload()

    json_text = render_ops_evidence_json(payload)
    markdown = render_ops_evidence_markdown(payload)

    parsed = json.loads(json_text)
    assert parsed["service_id"] == "svc-task7"
    assert parsed["active_release"]["release_version"] == "rel-task7-001"
    assert parsed["readyz"]["status"] == "ready"
    assert parsed["readyz"]["status_code"] == 200
    assert parsed["runtime_metrics"]["request_count"] == 12
    assert parsed["runtime_metrics"]["raw_query_retention"]["redacted_count"] == 5
    assert parsed["raw_text_key_summary"]["active_key_id"] == "pilot-kek-20260628-002"
    assert parsed["latest_rewrap_runs"][0]["rewrap_run_id"] == "rtr-20260628-002"
    assert parsed["audit_evidence"]["count"] == 2

    for section in (
        "# Intent Routing Operations Evidence",
        "## Service",
        "## Readiness",
        "## Runtime Metrics",
        "## Raw Text Key Summary",
        "## KEK Rewrap Runs",
        "## Runtime Raw-Query Retention",
        "## Audit Evidence",
        "## Secret Redaction Statement",
    ):
        assert section in markdown
    for expected in (
        "Service ID: `svc-task7`",
        "Active release: `rel-task7-001`",
        "Readyz: `ready` (`200`)",
        "Request count: `12`",
        "Active raw text key: `pilot-kek-20260628-002`",
        "rtr-20260628-002",
        "Raw query redacted count: `5`",
        "Audit event count: `2`",
        "Sensitive fields and secret-looking substrings were redacted recursively.",
    ):
        assert expected in markdown


def test_ops_evidence_redacts_sensitive_keys_and_substrings_recursively() -> None:
    payload = _payload()

    json_text = render_ops_evidence_json(payload)
    markdown = render_ops_evidence_markdown(payload)

    for rendered in (json_text, markdown):
        for forbidden in FORBIDDEN_MARKERS:
            assert forbidden not in rendered
        assert "REDACTED" in rendered
    assert "masked summary is safe" in json_text


def test_ops_evidence_redacts_legacy_kek_json_key_and_arbitrary_kek_value() -> None:
    legacy_kek_value = "QkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkI="
    payload = {
        "service_id": "svc-task7",
        "environment": "dev",
        "RAW_TEXT_LEGACY_KEKS_JSON": f'{{"old-kek":"{legacy_kek_value}"}}',
        "rotation": {
            "legacyKekBase64": legacy_kek_value,
            "legacy_keks_json": {"old-kek": legacy_kek_value},
            "operator_note": (
                "operator set "
                f'RAW_TEXT_LEGACY_KEKS_JSON={{"old-kek":"{legacy_kek_value}"}}'
            ),
            "safe_note": "visible summary",
        },
        "metadata": {
            "RAW_TEXT_LEGACY_KEKS_JSON": f'{{"old-kek":"{legacy_kek_value}"}}',
        },
    }

    json_text = render_ops_evidence_json(payload)
    markdown = render_ops_evidence_markdown(payload)

    for rendered in (json_text, markdown):
        assert "RAW_TEXT_LEGACY_KEKS_JSON" not in rendered
        assert "legacy_keks_json" not in rendered
        assert "legacyKekBase64" not in rendered
        assert "old-kek" not in rendered
        assert legacy_kek_value not in rendered
        assert "REDACTED" in rendered
    assert "visible summary" in json_text


def _payload() -> dict[str, object]:
    return {
        "service_id": "svc-task7",
        "environment": "dev",
        "collected_at": "2026-06-29T00:00:00Z",
        "readyz": {
            "status_code": 200,
            "status": "ready",
            "body": {"status": "ready"},
        },
        "active_release": {
            "release_version": "rel-task7-001",
            "environment": "dev",
            "policy_version": "pol-task7-001",
            "intent_catalog_version": "cat-task7-001",
            "active": True,
        },
        "runtime_metrics": {
            "service_id": "svc-task7",
            "window_hours": 24,
            "request_count": 12,
            "decision_counts": {"confident": 9, "fallback": 3},
            "error_counts": {"AUTHENTICATION_FAILED": 1},
            "latency_ms": {"p50": 21, "p95": 87, "max": 120},
            "top_route_keys": [{"route_key": "it.api_timeout.manual_lookup", "count": 7}],
            "raw_query_retention": {"encrypted_count": 8, "redacted_count": 5},
        },
        "raw_text_key_summary": {
            "service_id": "svc-task7",
            "active_key_id": "pilot-kek-20260628-002",
            "intent_examples": [
                {"key_id": "pilot-kek-20260628-002", "count": 4},
                {"key_id": "pilot-kek-20260628-001", "count": 1},
            ],
            "runtime_logs": [
                {"key_id": "pilot-kek-20260628-002", "count": 8},
                {"key_id": None, "count": 5, "state": "raw_query_redacted"},
            ],
        },
        "latest_rewrap_runs": [
            {
                "rewrap_run_id": "rtr-20260628-002",
                "service_id": "svc-task7",
                "target_key_id": "pilot-kek-20260628-002",
                "source_key_ids": ["pilot-kek-20260628-001"],
                "dry_run": False,
                "approval_id": "SEC-20260628-REWRAP-001",
                "status": "completed",
                "scanned_count": 6,
                "rewrapped_count": 4,
                "skipped_count": 2,
                "failed_count": 0,
                "started_at": "2026-06-28T00:00:00Z",
                "completed_at": "2026-06-28T00:00:01Z",
                "report": {
                    "query_raw": "plain raw text",
                    "query_raw_ciphertext": "ciphertext-value",
                    "query_raw_encrypted_dek": "encrypted-dek-value",
                },
            }
        ],
        "runtime_raw_query_retention": {"encrypted_count": 8, "redacted_count": 5},
        "audit_evidence": {
            "count": 2,
            "events": [
                {
                    "event_type": "raw_text.rewrap.executed",
                    "actor_id": "security-operator",
                    "view_reason": "approval=SEC-20260628-REWRAP-001",
                },
                {
                    "event_type": "raw_query.viewed",
                    "actor_id": "auditor-user",
                    "view_reason": (
                        "approval=SEC-20260628-RAW; "
                        "Authorization=Bearer task7-token; "
                        "details=query_raw text_raw RAW_TEXT_KEK_BASE64 "
                        "irt_secret_runtime "
                        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= "
                        "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="
                    ),
                },
            ],
        },
        "nested": [
            {
                "headers": {"Authorization": "Bearer task7-token"},
                "RAW_TEXT_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                "legacy_kek_base64": "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=",
                "query_raw": "raw query plaintext",
                "text_raw": "raw example plaintext",
                "safe_note": "masked summary is safe",
            }
        ],
    }
