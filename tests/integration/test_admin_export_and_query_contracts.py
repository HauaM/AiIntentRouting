from __future__ import annotations

import csv
import io
import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import MASKED_RUNTIME_LOG_FIELD_NAMES
from tests.integration.test_trace_audit_logs import (
    OTHER_SERVICE_ID,
    RAW_QUERY,
    SERVICE_ID,
    _admin_headers,
    _auditor_headers,
    _client,
    _create_runtime_trace,
    _operator_headers,
)


def test_masked_runtime_log_export_excludes_raw_query_and_secret_material(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID, actor_id="export-auditor"),
        json={
            "resource_type": "runtime_log",
            "format": "jsonl",
            "filters": {"trace_id": trace_id},
            "reason": "Investigating masked runtime log export contract",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["service_id"] == SERVICE_ID
    assert body["resource_type"] == "runtime_log"
    assert body["status"] == "completed"
    assert body["format"] == "jsonl"
    assert body["rejection_reason"] is None
    assert body["requested_by"] == "export-auditor"
    rows = [json.loads(line) for line in body["content"].splitlines()]
    assert len(rows) == 1
    assert rows[0]["trace_id"] == trace_id
    assert set(rows[0]) == set(MASKED_RUNTIME_LOG_FIELD_NAMES)
    serialized = json.dumps(body, ensure_ascii=False)
    assert RAW_QUERY not in serialized
    assert "query_raw" not in serialized
    assert "ciphertext" not in serialized
    assert "encrypted_dek" not in serialized
    assert "auth_tag" not in serialized
    assert "local-kek-001" not in serialized
    assert "irt_trace_audit_live_secret" not in serialized

    audit_events = [
        audit_log.event_type
        for audit_log in db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.service_id == SERVICE_ID)
            .where(models.AuditLog.actor_id == "export-auditor")
            .where(models.AuditLog.target_type == "export")
            .order_by(models.AuditLog.created_at, models.AuditLog.audit_id)
        )
    ]
    assert audit_events == ["export.requested", "export.completed"]


def test_export_audit_metadata_redacts_user_reason_text(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    malicious_reason = "Investigating RAW_QUERY ciphertext key_live_secret export"

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID, actor_id="reason-redaction-auditor"),
        json={
            "resource_type": "runtime_log",
            "format": "jsonl",
            "filters": {"trace_id": trace_id},
            "reason": malicious_reason,
        },
    )

    assert response.status_code == 200
    audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.service_id == SERVICE_ID)
            .where(models.AuditLog.actor_id == "reason-redaction-auditor")
            .where(models.AuditLog.target_type == "export")
            .order_by(models.AuditLog.created_at, models.AuditLog.audit_id)
        )
    )
    assert [audit_log.event_type for audit_log in audit_logs] == [
        "export.requested",
        "export.completed",
    ]
    serialized_audit = json.dumps(
        [
            {
                "view_reason": audit_log.view_reason,
                "before_state": audit_log.before_state,
                "after_state": audit_log.after_state,
            }
            for audit_log in audit_logs
        ],
        ensure_ascii=False,
        default=str,
    )
    assert "RAW_QUERY" not in serialized_audit
    assert "ciphertext" not in serialized_audit
    assert "key_live_secret" not in serialized_audit


def test_export_rejects_unsupported_filters_and_writes_audit(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID, actor_id="reject-auditor"),
        json={
            "resource_type": "runtime_log",
            "format": "jsonl",
            "filters": {"raw_query": RAW_QUERY},
            "reason": "Investigating unsupported export filter rejection",
        },
    )

    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert RAW_QUERY not in response.text
    assert "query_raw" not in response.text

    audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.service_id == SERVICE_ID)
            .where(models.AuditLog.actor_id == "reject-auditor")
            .where(models.AuditLog.target_type == "export")
            .order_by(models.AuditLog.created_at, models.AuditLog.audit_id)
        )
    )
    assert [audit_log.event_type for audit_log in audit_logs] == [
        "export.requested",
        "export.rejected",
    ]
    serialized_audit = json.dumps(
        [
            {
                "before_state": audit_log.before_state,
                "after_state": audit_log.after_state,
            }
            for audit_log in audit_logs
        ],
        ensure_ascii=False,
        default=str,
    )
    assert RAW_QUERY not in serialized_audit
    assert "raw_query" not in serialized_audit
    assert "query_raw" not in serialized_audit


def test_export_rejects_malicious_trace_id_without_audit_metadata_leak(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    malicious_trace_id = f"{RAW_QUERY} ciphertext key_live_secret"

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID, actor_id="malicious-filter-auditor"),
        json={
            "resource_type": "runtime_log",
            "format": "jsonl",
            "filters": {"trace_id": malicious_trace_id},
            "reason": "Investigating malicious export filter rejection",
        },
    )

    assert response.status_code == 400
    assert RAW_QUERY not in response.text
    assert "ciphertext" not in response.text
    assert "key_live_secret" not in response.text

    audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.service_id == SERVICE_ID)
            .where(models.AuditLog.actor_id == "malicious-filter-auditor")
            .where(models.AuditLog.target_type == "export")
            .order_by(models.AuditLog.created_at, models.AuditLog.audit_id)
        )
    )
    assert [audit_log.event_type for audit_log in audit_logs] == [
        "export.requested",
        "export.rejected",
    ]
    for audit_log in audit_logs:
        assert audit_log.trace_id is None
    serialized_audit = json.dumps(
        [
            {
                "trace_id": audit_log.trace_id,
                "before_state": audit_log.before_state,
                "after_state": audit_log.after_state,
            }
            for audit_log in audit_logs
        ],
        ensure_ascii=False,
        default=str,
    )
    assert RAW_QUERY not in serialized_audit
    assert "ciphertext" not in serialized_audit
    assert "key_live_secret" not in serialized_audit


def test_export_requires_auditor_owner_or_system_admin(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    payload = {
        "resource_type": "runtime_log",
        "format": "jsonl",
        "filters": {"trace_id": trace_id},
        "reason": "Investigating export role based access",
    }

    operator = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_operator_headers(SERVICE_ID),
        json=payload,
    )
    owner = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_owner_headers(SERVICE_ID),
        json=payload,
    )
    admin = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_admin_headers(actor_id="export-admin"),
        json=payload,
    )

    assert operator.status_code == 403
    assert operator.json()["status"] == "error"
    assert operator.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    assert owner.status_code == 200
    assert owner.json()["status"] == "completed"
    assert admin.status_code == 200
    assert admin.json()["status"] == "completed"


def test_export_denies_auditor_or_owner_scoped_to_other_service_without_audit(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    payload = {
        "resource_type": "runtime_log",
        "format": "jsonl",
        "filters": {"trace_id": trace_id},
        "reason": "Investigating export cross service access denial",
    }

    wrong_scope_auditor = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(OTHER_SERVICE_ID, actor_id="wrong-scope-auditor"),
        json=payload,
    )
    wrong_scope_owner = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_owner_headers(OTHER_SERVICE_ID, actor_id="wrong-scope-owner"),
        json=payload,
    )

    assert wrong_scope_auditor.status_code == 403
    assert wrong_scope_auditor.json()["status"] == "error"
    assert wrong_scope_auditor.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    assert wrong_scope_owner.status_code == 403
    assert wrong_scope_owner.json()["status"] == "error"
    assert wrong_scope_owner.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    export_audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.service_id == SERVICE_ID)
            .where(
                models.AuditLog.actor_id.in_(
                    {"wrong-scope-auditor", "wrong-scope-owner"}
                )
            )
            .where(models.AuditLog.target_type == "export")
        )
    )
    assert export_audit_logs == []


def test_runtime_log_export_supports_csv_headers_from_masked_projection(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID),
        json={
            "resource_type": "runtime_log",
            "format": "csv",
            "filters": {"trace_id": trace_id},
            "reason": "Investigating masked runtime log csv export",
        },
    )

    assert response.status_code == 200
    body = response.json()
    reader = csv.DictReader(io.StringIO(body["content"]))
    assert reader.fieldnames == list(MASKED_RUNTIME_LOG_FIELD_NAMES)
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["trace_id"] == trace_id
    assert RAW_QUERY not in body["content"]
    assert "query_raw" not in body["content"]


def _owner_headers(service_id: str, *, actor_id: str = "owner-user") -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": "service_owner",
            "X-Service-Scope": service_id,
        }
    )
