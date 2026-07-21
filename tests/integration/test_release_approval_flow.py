from __future__ import annotations

import json
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from tests.integration.test_release_flow import (
    _admin_headers,
    _approve_example,
    _audit_log,
    _create_catalog_version,
    _create_example,
    _create_valid_release,
    _release_setup,
    _seed_test_run,
)


def test_release_diff_compares_candidate_to_active_release(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    active = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    assert client.post(
        f"/admin/v1/services/{service_id}/releases/{active}:activate",
        headers=_admin_headers(),
    ).status_code == 200

    new_example = _create_example(
        client,
        service_id,
        "intent-api-timeout",
        "api timeout customer cannot reach gateway",
    )
    _approve_example(client, service_id, new_example["example_id"])
    candidate_catalog_version = _create_catalog_version(client, service_id)
    candidate_test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=candidate_catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )
    candidate = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=candidate_catalog_version,
        test_run_id=candidate_test_run_id,
        rollback_target=active,
    )

    response = client.get(
        f"/admin/v1/services/{service_id}/releases/{candidate}/diff",
        headers=_owner_headers(service_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["service_id"] == service_id
    assert body["release_version"] == candidate
    assert body["compare_to"] == active
    assert body["rollback_target"] == active
    assert body["policy_version_diff"] == {
        "from": policy_version,
        "to": policy_version,
        "changed": False,
    }
    assert body["catalog_version_diff"] == {
        "from": catalog_version,
        "to": candidate_catalog_version,
        "changed": True,
    }
    assert body["model_version_diff"]["changed"] is False
    assert body["test_run_diff"]["to"] == candidate_test_run_id
    assert body["test_run_diff"]["gate_passed"] is True


def test_release_activation_denies_service_developer_governed_publish_flow(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )

    direct = client.post(
        f"/admin/v1/services/{service_id}/releases/{release_version}:activate",
        headers=_developer_headers(service_id),
    )
    assert direct.status_code == 403

    requested = client.post(
        f"/admin/v1/services/{service_id}/publish-requests",
        headers=_developer_headers(service_id),
        json={
            "resource_type": "release",
            "resource_id": release_version,
            "action": "activate",
            "target_version": release_version,
            "reason": "Promote tested release after green gate",
        },
    )
    assert requested.status_code == 403
    assert requested.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_publish_request_rejects_evidence_refs_field(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/publish-requests",
        headers=_owner_headers(service_id),
        json={
            "resource_type": "release",
            "resource_id": release_version,
            "action": "activate",
            "target_version": release_version,
            "reason": "Promote tested release after green gate",
            "evidence_refs": ["release-diff-reviewed"],
        },
    )

    assert response.status_code == 422
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_publish_request_audit_metadata_redacts_user_reason_text(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    malicious_reason = "Promote RAW_QUERY ciphertext key_live_secret release"
    malicious_decision_reason = "Approved RAW_QUERY ciphertext key_live_secret review"

    requested = client.post(
        f"/admin/v1/services/{service_id}/publish-requests",
        headers=_owner_headers(service_id),
        json={
            "resource_type": "release",
            "resource_id": release_version,
            "action": "activate",
            "target_version": release_version,
            "reason": malicious_reason,
        },
    )
    assert requested.status_code == 201
    request_id = requested.json()["request_id"]
    assert requested.json()["reason"] == malicious_reason

    approved = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:approve",
        headers=_owner_headers(service_id, actor_id="reviewer-owner"),
        json={"reason": malicious_decision_reason},
    )
    assert approved.status_code == 200
    assert approved.json()["decision_reason"] == malicious_decision_reason

    audit_logs = list(
        db_session.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.target_id == request_id)
            .where(
                models.AuditLog.event_type.in_(
                    {"publish.requested", "publish.approved"}
                )
            )
            .order_by(models.AuditLog.created_at, models.AuditLog.audit_id)
        )
    )
    assert [audit_log.event_type for audit_log in audit_logs] == [
        "publish.requested",
        "publish.approved",
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


def test_release_reject_is_terminal(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    requested = client.post(
        f"/admin/v1/services/{service_id}/publish-requests",
        headers=_owner_headers(service_id),
        json={
            "resource_type": "release",
            "resource_id": release_version,
            "action": "activate",
            "target_version": release_version,
            "reason": "Promote tested release after green gate",
        },
    )
    request_id = requested.json()["request_id"]

    rejected = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:reject",
        headers=_owner_headers(service_id, actor_id="reviewer-owner"),
        json={"reason": "Diff review found missing stakeholder approval"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    late_approval = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:approve",
        headers=_owner_headers(service_id, actor_id="second-owner"),
        json={"reason": "Trying to approve after rejection"},
    )
    assert late_approval.status_code == 409

    activation = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:activate",
        headers=_owner_headers(service_id),
    )
    assert activation.status_code == 409

    request_model = db_session.scalar(
        select(models.GovernedActionRequest).where(
            models.GovernedActionRequest.request_id == request_id
        )
    )
    assert request_model is not None
    assert request_model.status == "rejected"
    assert _audit_log(db_session, "publish.rejected", request_id) is not None


def test_system_admin_can_still_activate_release_directly(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/releases/{release_version}:activate",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["active"] is True


def _developer_headers(
    service_id: str,
    *,
    actor_id: str = "developer-user",
) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": "service_developer",
            "X-Service-Scope": service_id,
        }
    )


def _owner_headers(
    service_id: str,
    *,
    actor_id: str = "owner-user",
) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": "service_owner",
            "X-Service-Scope": service_id,
        }
    )


def _auditor_headers(
    service_id: str,
    *,
    actor_id: str = "auditor-user",
) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": "auditor",
            "X-Service-Scope": service_id,
        }
    )
