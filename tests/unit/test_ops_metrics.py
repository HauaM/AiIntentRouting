from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from intent_routing.db import models
from intent_routing.ops.metrics import (
    empty_runtime_metrics,
    raw_text_key_summary_from_counts,
    safe_audit_log_item,
)


def test_empty_runtime_metrics_includes_zero_decision_counts_and_null_latency() -> None:
    metrics = empty_runtime_metrics("it-helpdesk-pilot", window_hours=24)

    assert metrics == {
        "service_id": "it-helpdesk-pilot",
        "window_hours": 24,
        "request_count": 0,
        "decision_counts": {
            "confident": 0,
            "clarify": 0,
            "fallback": 0,
            "off_topic": 0,
            "risk": 0,
            "unauthorized": 0,
        },
        "error_counts": {},
        "latency_ms": {"p50": None, "p95": None, "max": None},
        "top_route_keys": [],
        "raw_query_retention": {
            "encrypted_count": 0,
            "incomplete_count": 0,
            "redacted_count": 0,
        },
    }


def test_raw_text_key_summary_counts_key_ids_without_key_material() -> None:
    summary = raw_text_key_summary_from_counts(
        service_id="it-helpdesk-pilot",
        active_key_id="pilot-kek-20260628-002",
        counts={
            "intent_examples": {
                "pilot-kek-20260628-002": 30,
                "pilot-kek-20260628-001": 4,
            },
            "runtime_logs": {"pilot-kek-20260628-002": 20},
            "runtime_logs_redacted": 5,
        },
    )

    assert summary == {
        "service_id": "it-helpdesk-pilot",
        "active_key_id": "pilot-kek-20260628-002",
        "intent_examples": [
            {"key_id": "pilot-kek-20260628-002", "count": 30},
            {"key_id": "pilot-kek-20260628-001", "count": 4},
        ],
        "runtime_logs": [
            {"key_id": "pilot-kek-20260628-002", "count": 20},
            {"key_id": None, "count": 5, "state": "raw_query_redacted"},
        ],
    }


def test_safe_audit_log_item_omits_state_snapshots() -> None:
    audit_log = models.AuditLog(
        audit_id=uuid4(),
        event_type="raw_query.viewed",
        actor_id="auditor-user",
        service_id="it-helpdesk-pilot",
        trace_id="irt-abc",
        target_type="runtime_log",
        target_id="irt-abc",
        view_reason="approval=SEC-20260628-001; reason=장애 분석 ticket INC-20260628-001",
        source_ip="127.0.0.1",
        before_state={"query_raw": "plain raw query"},
        after_state={
            "query_raw_ciphertext": "ciphertext",
            "query_raw_encrypted_dek": "encrypted-dek",
        },
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    item = safe_audit_log_item(audit_log)

    assert item == {
        "audit_id": str(audit_log.audit_id),
        "event_type": "raw_query.viewed",
        "actor_id": "auditor-user",
        "service_id": "it-helpdesk-pilot",
        "trace_id": "irt-abc",
        "target_type": "runtime_log",
        "target_id": "irt-abc",
        "view_reason": "approval=SEC-20260628-001; reason_redacted=true",
        "source_ip": "127.0.0.1",
        "created_at": datetime(2026, 6, 28, tzinfo=UTC),
    }
    assert "before_state" not in item
    assert "after_state" not in item


def test_safe_audit_log_item_sanitizes_view_reason() -> None:
    audit_log = models.AuditLog(
        audit_id=uuid4(),
        event_type="raw_query.viewed",
        actor_id="auditor-user",
        service_id="it-helpdesk-pilot",
        trace_id="irt-abc",
        target_type="runtime_log",
        target_id="irt-abc",
        view_reason=(
            "approval=SEC-20260628-001; "
            "reason=query_raw text_raw plain raw query; "
            "authorization=Bearer irt_secret_task6_token; "
            "kek_base64=bm90LWEtcmVhbC1rZWstYnV0LXNlbnNpdGl2ZQ==; "
            "details=plain customer raw text; "
            "note=some arbitrary plaintext secret"
        ),
        source_ip="127.0.0.1",
        before_state=None,
        after_state=None,
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    item = safe_audit_log_item(audit_log)

    assert item["view_reason"] == "approval=SEC-20260628-001; reason_redacted=true"
    serialized = str(item["view_reason"])
    assert "Bearer" not in serialized
    assert "irt_secret" not in serialized
    assert "bm90LWEtcmVhbC1rZWstYnV0LXNlbnNpdGl2ZQ==" not in serialized
    assert "query_raw" not in serialized
    assert "text_raw" not in serialized
    assert "plain raw query" not in serialized
    assert "plain customer raw text" not in serialized
    assert "some arbitrary plaintext secret" not in serialized
    assert "details" not in serialized
    assert "note" not in serialized


def test_safe_audit_log_item_preserves_only_allowlisted_view_reason_metadata() -> None:
    audit_log = models.AuditLog(
        audit_id=uuid4(),
        event_type="raw_query.viewed",
        actor_id="auditor-user",
        service_id="it-helpdesk-pilot",
        trace_id="irt-abc",
        target_type="runtime_log",
        target_id="irt-abc",
        view_reason=(
            "approval_id=SEC-20260628-001; "
            "ticket_id=INC-20260628-001; "
            "details=plain customer raw text"
        ),
        source_ip="127.0.0.1",
        before_state=None,
        after_state=None,
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    item = safe_audit_log_item(audit_log)

    assert item["view_reason"] == (
        "approval_id=SEC-20260628-001; "
        "ticket_id=INC-20260628-001; "
        "reason_redacted=true"
    )
