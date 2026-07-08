import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from tests.integration.test_trace_audit_logs import (
    RAW_QUERY,
    SERVICE_ID,
    VIEW_REASON,
    _auditor_headers,
    _client,
    _create_runtime_trace,
    _operator_headers,
)


def test_raw_query_two_person_approval_flow(
    db_session: Session,
    monkeypatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    created = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}/raw-query-view-requests",
        headers=_operator_headers(SERVICE_ID),
        json={
            "reason": "Investigating support ticket INC-20260708-raw-query",
            "ticket_ref": "INC-20260708-raw-query",
        },
    )
    assert created.status_code == 201
    request_id = created.json()["request_id"]
    assert created.json()["status"] == "pending"
    assert created.json()["requested_by"] == "operator-user"

    self_approved = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:approve",
        headers=_operator_headers(SERVICE_ID),
        json={"reason": "Trying to approve my own request"},
    )
    assert self_approved.status_code == 403

    token_before_approval = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:issue-token",
        headers=_operator_headers(SERVICE_ID),
        json={},
    )
    assert token_before_approval.status_code == 409

    approved = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:approve",
        headers=_auditor_headers(SERVICE_ID, actor_id="auditor-approver"),
        json={"reason": "Ticket reason is valid"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["decided_by"] == "auditor-approver"

    direct_decrypt = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(SERVICE_ID, actor_id="auditor-approver"),
        json={"view_reason": VIEW_REASON},
    )
    assert direct_decrypt.status_code == 403
    assert RAW_QUERY not in direct_decrypt.text

    issued = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:issue-token",
        headers=_operator_headers(SERVICE_ID),
        json={},
    )
    assert issued.status_code == 200
    raw_query_view_token = issued.json()["token"]
    assert raw_query_view_token
    assert raw_query_view_token not in {
        token.token_hash
        for token in db_session.scalars(select(models.RawQueryViewToken)).all()
    }

    decrypted = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_operator_headers(SERVICE_ID),
        json={
            "view_reason": VIEW_REASON,
            "raw_query_view_token": raw_query_view_token,
        },
    )
    assert decrypted.status_code == 200
    assert decrypted.json()["query_raw"] == RAW_QUERY
    assert decrypted.json()["viewed_by"] == "operator-user"

    viewed_audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.event_type == "raw_query.viewed")
        .where(models.AuditLog.actor_id == "operator-user")
        .where(models.AuditLog.trace_id == trace_id)
    )
    assert viewed_audit_log is not None
    assert viewed_audit_log.after_state == {
        "trace_id": trace_id,
        "service_id": SERVICE_ID,
        "query_raw_viewed": True,
    }


def test_raw_query_view_token_cannot_decrypt_twice(
    db_session: Session,
    monkeypatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    raw_query_view_token = _approved_raw_query_view_token(client, trace_id)

    first = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_operator_headers(SERVICE_ID),
        json={
            "view_reason": VIEW_REASON,
            "raw_query_view_token": raw_query_view_token,
        },
    )
    second = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_operator_headers(SERVICE_ID),
        json={
            "view_reason": VIEW_REASON,
            "raw_query_view_token": raw_query_view_token,
        },
    )

    assert first.status_code == 200
    assert first.json()["query_raw"] == RAW_QUERY
    assert second.status_code == 403
    assert RAW_QUERY not in second.text
    assert raw_query_view_token not in second.text
    viewed_audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.event_type == "raw_query.viewed")
            .where(models.AuditLog.trace_id == trace_id)
        )
    )
    assert len(viewed_audit_logs) == 1


def test_repository_consumes_raw_query_view_token_once(
    db_session: Session,
    monkeypatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    _approved_raw_query_view_token(client, trace_id)
    token_model = db_session.scalar(
        select(models.RawQueryViewToken).where(
            models.RawQueryViewToken.trace_id == trace_id
        )
    )
    assert token_model is not None
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)

    consumed = repository.consume_raw_query_view_token(
        token_hash=token_model.token_hash,
        service_id=SERVICE_ID,
        trace_id=trace_id,
        consumed_at=now,
    )
    repeated = repository.consume_raw_query_view_token(
        token_hash=token_model.token_hash,
        service_id=SERVICE_ID,
        trace_id=trace_id,
        consumed_at=now,
    )

    assert consumed is token_model
    assert consumed.viewed_at == now
    assert consumed.request.status == "viewed"
    assert repeated is None


def test_expired_raw_query_view_token_attempt_expires_request_and_writes_audit(
    db_session: Session,
    monkeypatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    raw_query_view_token = _approved_raw_query_view_token(
        client,
        trace_id,
        ttl_seconds=1,
    )
    token_model = db_session.scalar(
        select(models.RawQueryViewToken).where(
            models.RawQueryViewToken.trace_id == trace_id
        )
    )
    assert token_model is not None
    token_model.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    request_id = token_model.request_id
    db_session.commit()

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_operator_headers(SERVICE_ID),
        json={
            "view_reason": VIEW_REASON,
            "raw_query_view_token": raw_query_view_token,
        },
    )

    assert response.status_code == 403
    assert RAW_QUERY not in response.text
    assert raw_query_view_token not in response.text
    db_session.expire_all()
    request_model = db_session.get(models.GovernedActionRequest, request_id)
    token_model = db_session.get(models.RawQueryViewToken, token_model.token_id)
    assert request_model is not None
    assert token_model is not None
    assert request_model.status == "expired"
    assert token_model.expired_at is not None
    expired_audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.event_type == "raw_query.token_expired")
        .where(models.AuditLog.target_id == request_id)
    )
    assert expired_audit_log is not None
    serialized_audit = json.dumps(
        {
            "view_reason": expired_audit_log.view_reason,
            "before_state": expired_audit_log.before_state,
            "after_state": expired_audit_log.after_state,
        },
        ensure_ascii=False,
        default=str,
    )
    assert RAW_QUERY not in serialized_audit
    assert raw_query_view_token not in serialized_audit
    assert "ciphertext" not in serialized_audit
    assert "key_live_secret" not in serialized_audit


def test_phase2_raw_query_audit_metadata_redacts_user_reason_text(
    db_session: Session,
    monkeypatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    malicious_reason = "Investigating RAW_QUERY ciphertext key_live_secret marker"
    malicious_decision_reason = (
        "Approving RAW_QUERY ciphertext key_live_secret marker review"
    )

    created = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}/raw-query-view-requests",
        headers=_operator_headers(SERVICE_ID),
        json={"reason": malicious_reason},
    )
    assert created.status_code == 201
    request_id = created.json()["request_id"]
    assert created.json()["reason"] == malicious_reason

    approved = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:approve",
        headers=_auditor_headers(SERVICE_ID, actor_id="auditor-approver"),
        json={"reason": malicious_decision_reason},
    )
    assert approved.status_code == 200
    assert approved.json()["decision_reason"] == malicious_decision_reason

    issued = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:issue-token",
        headers=_operator_headers(SERVICE_ID),
        json={},
    )
    assert issued.status_code == 200

    audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.target_id == request_id)
            .where(
                models.AuditLog.event_type.in_(
                    {
                        "raw_query.requested",
                        "raw_query.approved",
                        "raw_query.token_issued",
                    }
                )
            )
            .order_by(models.AuditLog.created_at, models.AuditLog.audit_id)
        )
    )
    assert [audit_log.event_type for audit_log in audit_logs] == [
        "raw_query.requested",
        "raw_query.approved",
        "raw_query.token_issued",
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


def test_raw_query_reject_is_terminal(
    db_session: Session,
    monkeypatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    created = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}/raw-query-view-requests",
        headers=_operator_headers(SERVICE_ID),
        json={"reason": "Investigating support ticket INC-20260708-reject"},
    )
    request_id = created.json()["request_id"]

    rejected = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:reject",
        headers=_auditor_headers(SERVICE_ID, actor_id="auditor-approver"),
        json={"reason": "Ticket does not justify raw query access"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    issued = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:issue-token",
        headers=_operator_headers(SERVICE_ID),
        json={},
    )
    assert issued.status_code == 409

    request_model = db_session.get(models.GovernedActionRequest, request_id)
    assert request_model is not None
    assert request_model.status == "rejected"
    assert request_model.decided_at <= datetime.now(UTC)


def _approved_raw_query_view_token(
    client,
    trace_id: str,
    *,
    ttl_seconds: int = 300,
) -> str:
    created = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}/raw-query-view-requests",
        headers=_operator_headers(SERVICE_ID),
        json={"reason": "Investigating support ticket INC-20260708-token"},
    )
    assert created.status_code == 201
    request_id = created.json()["request_id"]
    approved = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:approve",
        headers=_auditor_headers(SERVICE_ID, actor_id="auditor-approver"),
        json={"reason": "Ticket reason is valid"},
    )
    assert approved.status_code == 200
    issued = client.post(
        f"/admin/v1/services/{SERVICE_ID}/raw-query-view-requests/{request_id}:issue-token",
        headers=_operator_headers(SERVICE_ID),
        json={"ttl_seconds": ttl_seconds},
    )
    assert issued.status_code == 200
    return str(issued.json()["token"])
