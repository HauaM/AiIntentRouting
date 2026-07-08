from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
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
