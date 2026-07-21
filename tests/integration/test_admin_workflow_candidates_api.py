from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_NAME,
    hash_admin_session_token,
)


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app, raise_server_exceptions=False)


def _system_admin_client(
    db_session: Session,
) -> tuple[TestClient, str, list[dict[str, object]]]:
    user_id = f"workflow-admin-{uuid4().hex}"
    raw_token = f"raw-session-{user_id}"
    now = datetime.now(UTC)
    system_admin_role_rows = _backup_and_delete_system_admin_roles(db_session)
    repository = IntentRoutingRepository(db_session)
    try:
        repository.create_admin_user(
            user_id=user_id,
            email=f"{user_id}@example.com",
            display_name="Workflow Admin",
            password_hash="password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="integration-test",
            assigned_at=now,
        )
        repository.create_admin_session(
            session_id=f"session-{user_id}",
            user_id=user_id,
            token_hash=hash_admin_session_token(raw_token),
            created_at=now,
            expires_at=now + timedelta(hours=1),
            revoked_at=None,
            last_seen_at=None,
        )
        db_session.commit()
    except Exception:
        db_session.rollback()
        _restore_system_admin_roles(db_session, system_admin_role_rows)
        raise

    client = _client(db_session)
    client.cookies.set(ADMIN_SESSION_COOKIE_NAME, raw_token)
    return client, user_id, system_admin_role_rows


def _create_service(client: TestClient, service_id: str) -> None:
    response = client.post(
        "/admin/v1/services",
        json={
            "service_id": service_id,
            "display_name": "Workflow Candidate Service",
            "max_input_tokens": 256,
        },
    )
    assert response.status_code == 201


def _policy_payload() -> dict[str, object]:
    return {
        "threshold_preset": "balanced",
        "clarify_margin": 0.08,
        "min_candidate_score": 0.55,
        "fallback_score": 0.45,
        "risk_policy": {"enabled": True},
        "off_topic_policy": {
            "enabled": True,
            "keywords": [],
            "message": "",
        },
    }


def _seed_workflow_records(
    db_session: Session,
    service_id: str,
    *,
    gate_passed: bool = True,
    risk_pass_rate: Decimal = Decimal("1.0"),
) -> tuple[str, str, str]:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    policy_version = f"pol-{service_id}-{uuid4().hex[:8]}"
    catalog_version = f"cat-{service_id}-{uuid4().hex[:8]}"
    dataset_version = f"tds-{service_id}-{uuid4().hex[:8]}"
    test_run_id = f"tr-{service_id}-{uuid4().hex[:8]}"
    repository.create_policy_version(
        policy_version=policy_version,
        service_id=service_id,
        threshold_preset="balanced",
        threshold_value=Decimal("0.8"),
        clarify_margin=Decimal("0.08"),
        min_candidate_score=Decimal("0.55"),
        fallback_score=Decimal("0.45"),
        risk_policy={"enabled": True},
        off_topic_policy={"enabled": True, "keywords": [], "message": ""},
        created_by="integration-test",
        created_at=now,
    )
    repository.create_catalog_version(
        intent_catalog_version=catalog_version,
        service_id=service_id,
        snapshot={
            "intents": [
                {
                    "intent_id": "billing_refund",
                    "display_name": "Billing refund",
                    "route_key": "billing.refund.request",
                    "status": "active",
                    "examples": [{"example_id": "ex-1", "approved": True}],
                }
            ]
        },
        created_by="integration-test",
        created_at=now,
    )
    repository.create_test_dataset(
        {
            "test_dataset_version": dataset_version,
            "service_id": service_id,
            "source_filename": "workflow-candidates.csv",
            "content_sha256": f"sha256-{uuid4().hex}",
            "created_by": "integration-test",
            "created_at": now,
        }
    )
    repository.create_test_run_with_results(
        {
            "test_run_id": test_run_id,
            "service_id": service_id,
            "test_dataset_version": dataset_version,
            "policy_version": policy_version,
            "intent_catalog_version": catalog_version,
            "threshold_preset": "balanced",
            "threshold_value": Decimal("0.8"),
            "pass_rate": Decimal("1.0"),
            "review_rate": Decimal("0.0"),
            "risk_pass_rate": risk_pass_rate,
            "gate_passed": gate_passed,
            "created_by": "integration-test",
            "created_at": now,
        },
        [],
    )
    db_session.commit()
    return policy_version, catalog_version, test_run_id


def _purge_rows(db_session: Session, *, user_id: str, service_id: str) -> None:
    db_session.execute(
        text("delete from audit_logs where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from releases where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text(
            "delete from test_results where test_run_id in "
            "(select test_run_id from test_runs where service_id = :service_id)"
        ),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from test_runs where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from test_datasets where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from catalog_version_example_embeddings where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from vector_index_versions where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from intent_catalog_versions where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from policy_versions where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from intents where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from services where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.commit()


def _backup_and_delete_system_admin_roles(
    db_session: Session,
) -> list[dict[str, object]]:
    rows = [
        dict(row)
        for row in db_session.execute(
            text(
                "select user_id, role, assigned_by, assigned_at "
                "from admin_user_roles where role = 'system_admin'"
            )
        ).mappings()
    ]
    db_session.execute(text("delete from admin_user_roles where role = 'system_admin'"))
    db_session.commit()
    return rows


def _restore_system_admin_roles(
    db_session: Session,
    rows: list[dict[str, object]],
) -> None:
    if rows:
        db_session.execute(
            text(
                "insert into admin_user_roles (user_id, role, assigned_by, assigned_at) "
                "values (:user_id, :role, :assigned_by, :assigned_at) "
                "on conflict (user_id, role) do update set "
                "assigned_by = excluded.assigned_by, "
                "assigned_at = excluded.assigned_at"
            ),
            rows,
        )
    db_session.commit()


def test_lists_policy_and_catalog_versions(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    clear_embedding_provider_cache()
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-workflow-{uuid4().hex}"
    try:
        _create_service(client, service_id)

        policy = client.post(
            f"/admin/v1/services/{service_id}/policy-versions",
            json=_policy_payload(),
        )
        catalog = client.post(
            f"/admin/v1/services/{service_id}/catalog-versions",
            json={"description": "Workflow catalog version"},
        )

        policies = client.get(f"/admin/v1/services/{service_id}/policy-versions")
        catalogs = client.get(f"/admin/v1/services/{service_id}/catalog-versions")

        assert policy.status_code == 201
        assert catalog.status_code == 201
        assert policies.status_code == 200
        assert catalogs.status_code == 200
        assert policies.json()[0]["policy_version"] == policy.json()["policy_version"]
        assert catalogs.json()[0]["intent_catalog_version"] == catalog.json()[
            "intent_catalog_version"
        ]
        assert catalogs.json()[0]["intent_count"] == 0
        assert catalogs.json()[0]["example_count"] == 0
        assert catalogs.json()[0]["embedding_count"] == 0
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


def test_lists_test_runs_with_dataset_source_filename(db_session: Session) -> None:
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-test-runs-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        _, _, test_run_id = _seed_workflow_records(db_session, service_id)

        response = client.get(
            f"/admin/v1/services/{service_id}/test-runs",
            params={"gate_passed": True, "risk_passed": True},
        )

        assert response.status_code == 200
        row = response.json()[0]
        assert row["test_run_id"] == test_run_id
        assert row["source_filename"] == "workflow-candidates.csv"
        assert row["policy_version"].startswith("pol-")
        assert row["intent_catalog_version"].startswith("cat-")
        assert row["created_by"] == "integration-test"
        assert isinstance(row["block_reasons"], list)
        assert isinstance(row["recommendations"], list)
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


def test_release_candidates_include_eligibility_and_release_state(
    db_session: Session,
) -> None:
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-release-candidates-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        policy_version, catalog_version, test_run_id = _seed_workflow_records(
            db_session,
            service_id,
        )

        before_release = client.get(
            f"/admin/v1/services/{service_id}/release-candidates"
        )
        release = db_session.get(models.TestRun, test_run_id)
        assert release is not None
        db_session.add(
            models.Release(
                release_version=f"rel-{service_id}-{uuid4().hex[:8]}",
                service_id=service_id,
                environment="dev",
                policy_version=policy_version,
                intent_catalog_version=catalog_version,
                model_version="fake-embedding-v1",
                vector_index_version="vec-test",
                test_dataset_version=release.test_dataset_version,
                test_run_id=test_run_id,
                pass_rate=Decimal("1.0"),
                risk_pass_rate=Decimal("1.0"),
                active=True,
                released_by="integration-test",
                released_at=datetime.now(UTC),
                rollback_target=None,
            )
        )
        db_session.commit()

        after_release = client.get(
            f"/admin/v1/services/{service_id}/release-candidates"
        )

        assert before_release.status_code == 200
        before = before_release.json()[0]
        assert before["test_run_id"] == test_run_id
        assert before["environment"] == "dev"
        assert before["eligible"] is True
        assert before["already_released"] is False
        assert before["existing_release_version"] is None

        assert after_release.status_code == 200
        after = after_release.json()[0]
        assert after["eligible"] is False
        assert after["already_released"] is True
        assert after["existing_release_version"].startswith("rel-")
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


def test_release_candidates_require_exact_full_risk_pass_rate(
    db_session: Session,
) -> None:
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-release-risk-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        _, _, test_run_id = _seed_workflow_records(
            db_session,
            service_id,
            risk_pass_rate=Decimal("0.99999999999999999"),
        )

        response = client.get(
            f"/admin/v1/services/{service_id}/release-candidates"
        )

        assert response.status_code == 200
        row = response.json()[0]
        assert row["test_run_id"] == test_run_id
        assert row["eligible"] is False
        assert "risk pass rate must be 100%" in row["block_reasons"]
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


def test_release_candidates_can_target_requested_environment(
    db_session: Session,
) -> None:
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-release-env-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        _, _, test_run_id = _seed_workflow_records(db_session, service_id)

        response = client.get(
            f"/admin/v1/services/{service_id}/release-candidates",
            params={"environment": "prod"},
        )

        assert response.status_code == 200
        row = response.json()[0]
        assert row["test_run_id"] == test_run_id
        assert row["environment"] == "prod"
        assert row["eligible"] is True
        assert "release environment must match service environment" not in row[
            "block_reasons"
        ]
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


def test_intent_route_candidates_are_selectable_scope_values(
    db_session: Session,
) -> None:
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-intent-route-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        repository = IntentRoutingRepository(db_session)
        now = datetime.now(UTC)
        repository.create_intent(
            service_id=service_id,
            intent_id="billing_refund",
            domain="billing",
            display_name="Billing refund",
            description="Handle refund requests.",
            route_key="billing.refund.request",
            status="active",
            include_keywords=["refund"],
            exclude_keywords=[],
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.create_intent(
            service_id=service_id,
            intent_id="billing_draft",
            domain="billing",
            display_name="Billing draft",
            description="Draft intent.",
            route_key="billing.draft.request",
            status="draft",
            include_keywords=[],
            exclude_keywords=[],
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        response = client.get(
            f"/admin/v1/services/{service_id}/intent-route-candidates"
        )
        active_release_response = client.get(
            f"/admin/v1/services/{service_id}/intent-route-candidates",
            params={"source": "active_release", "environment": "dev"},
        )
        released_catalog_response = client.get(
            f"/admin/v1/services/{service_id}/intent-route-candidates",
            params={"source": "released_catalog", "environment": "dev"},
        )

        assert response.status_code == 200
        assert response.json() == [
            {
                "intent_id": "billing_refund",
                "display_name": "Billing refund",
                "route_key": "billing.refund.request",
                "status": "active",
                "source": "current_catalog",
            }
        ]
        assert active_release_response.status_code == 200
        assert active_release_response.json() == []
        assert released_catalog_response.status_code == 200
        assert released_catalog_response.json() == []
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


def test_released_catalog_candidates_use_latest_release_without_activation(
    db_session: Session,
) -> None:
    client, user_id, system_admin_role_rows = _system_admin_client(db_session)
    service_id = f"svc-released-catalog-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        policy_version, catalog_version, test_run_id = _seed_workflow_records(
            db_session,
            service_id,
        )
        test_run = IntentRoutingRepository(db_session).get_test_run(test_run_id)
        assert test_run is not None
        IntentRoutingRepository(db_session).create_release(
            release_version=f"rel-{service_id}-{uuid4().hex[:8]}",
            service_id=service_id,
            environment="qa",
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            model_version="fake-embedding-v1",
            vector_index_version="vec-released-catalog",
            test_dataset_version=test_run.test_dataset_version,
            test_run_id=test_run_id,
            pass_rate=Decimal("1.0"),
            risk_pass_rate=Decimal("1.0"),
            active=False,
            released_by="integration-test",
            released_at=datetime.now(UTC),
            rollback_target=None,
        )
        db_session.commit()

        response = client.get(
            f"/admin/v1/services/{service_id}/intent-route-candidates",
            params={"source": "released_catalog", "environment": "qa"},
        )

        assert response.status_code == 200
        assert response.json() == [
            {
                "intent_id": "billing_refund",
                "display_name": "Billing refund",
                "route_key": "billing.refund.request",
                "status": "active",
                "source": "released_catalog",
            }
        ]
    finally:
        try:
            _purge_rows(db_session, user_id=user_id, service_id=service_id)
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)
