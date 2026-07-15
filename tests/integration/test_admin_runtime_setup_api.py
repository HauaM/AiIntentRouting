from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_NAME,
    hash_admin_session_token,
)


@dataclass(frozen=True)
class _SessionFixture:
    user_id: str
    session_id: str
    created_user: bool


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app, raise_server_exceptions=False)


def _system_admin_client(
    db_session: Session,
) -> tuple[TestClient, _SessionFixture]:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    user_id = db_session.scalar(
        select(models.AdminUserRole.user_id)
        .where(models.AdminUserRole.role == "system_admin")
        .limit(1)
    )
    created_user = False
    if user_id is None:
        created_user = True
        user_id = f"runtime-setup-admin-{uuid4().hex}"
        repository.create_admin_user(
            user_id=user_id,
            email=f"{user_id}@example.com",
            display_name="Runtime Setup Admin",
            password_hash="password-hash",
            status="active",
            admin_access_reason="integration test runtime setup system admin",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="integration-test",
            assigned_at=now,
        )
    raw_token = f"raw-session-{user_id}-{uuid4().hex}"
    session_id = f"session-{user_id}-{uuid4().hex}"
    repository.create_admin_session(
        session_id=session_id,
        user_id=user_id,
        token_hash=hash_admin_session_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(hours=1),
        revoked_at=None,
        last_seen_at=None,
    )
    db_session.commit()

    client = _client(db_session)
    client.cookies.set(ADMIN_SESSION_COOKIE_NAME, raw_token)
    return client, _SessionFixture(
        user_id=user_id,
        session_id=session_id,
        created_user=created_user,
    )


def _application_admin_client(
    db_session: Session,
    *,
    service_roles: tuple[tuple[str, str], ...] = (),
) -> tuple[TestClient, _SessionFixture]:
    now = datetime.now(UTC)
    user_id = f"runtime-setup-app-admin-{uuid4().hex}"
    raw_token = f"raw-session-{user_id}"
    session_id = f"session-{user_id}"
    repository = IntentRoutingRepository(db_session)
    repository.create_admin_user(
        user_id=user_id,
        email=f"{user_id}@example.com",
        display_name="Runtime Setup Application Admin",
        password_hash="password-hash",
        status="active",
        admin_access_reason="integration test runtime setup application admin",
        created_at=now,
        updated_at=now,
    )
    repository.assign_admin_user_role(
        user_id=user_id,
        role="application_admin",
        assigned_by="integration-test",
        assigned_at=now,
    )
    for service_id, role in service_roles:
        repository.assign_user_service_role(
            user_id=user_id,
            service_id=service_id,
            role=role,
            assigned_by="integration-test",
            assigned_at=now,
        )
    repository.create_admin_session(
        session_id=session_id,
        user_id=user_id,
        token_hash=hash_admin_session_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(hours=1),
        revoked_at=None,
        last_seen_at=None,
    )
    db_session.commit()

    client = _client(db_session)
    client.cookies.set(ADMIN_SESSION_COOKIE_NAME, raw_token)
    return client, _SessionFixture(
        user_id=user_id,
        session_id=session_id,
        created_user=True,
    )


def _create_service(client: TestClient, service_id: str) -> None:
    response = client.post(
        "/admin/v1/services",
        json={
            "service_id": service_id,
            "display_name": "Runtime Setup Service",
            "environment": "dev",
            "default_threshold_preset": "balanced",
            "max_input_tokens": 256,
        },
    )
    assert response.status_code == 201


def _seed_active_release(db_session: Session, service_id: str) -> str:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    policy_version = f"pol-{service_id}-{uuid4().hex[:8]}"
    catalog_version = f"cat-{service_id}-{uuid4().hex[:8]}"
    dataset_version = f"tds-{service_id}-{uuid4().hex[:8]}"
    test_run_id = f"tr-{service_id}-{uuid4().hex[:8]}"
    release_version = f"rel-{service_id}-{uuid4().hex[:8]}"

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
                },
                {
                    "intent_id": "billing_draft",
                    "display_name": "Billing draft",
                    "route_key": "billing.draft.request",
                    "status": "draft",
                    "examples": [],
                },
            ]
        },
        created_by="integration-test",
        created_at=now,
    )
    repository.create_test_dataset(
        {
            "test_dataset_version": dataset_version,
            "service_id": service_id,
            "source_filename": "runtime-setup.csv",
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
            "risk_pass_rate": Decimal("1.0"),
            "gate_passed": True,
            "created_by": "integration-test",
            "created_at": now,
        },
        [],
    )
    repository.create_release(
        release_version=release_version,
        service_id=service_id,
        environment="dev",
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        model_version="fake-embedding-v1",
        vector_index_version="vec-runtime-setup",
        test_dataset_version=dataset_version,
        test_run_id=test_run_id,
        pass_rate=Decimal("1.0"),
        risk_pass_rate=Decimal("1.0"),
        active=True,
        released_by="integration-test",
        released_at=now,
        rollback_target=None,
    )
    db_session.commit()
    return release_version


def _api_key_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "environment": "dev",
        "app_id": "dify-helpdesk",
        "allowed_intents": ["billing_refund"],
        "allowed_route_keys": ["billing.refund.request"],
        "expires_in_days": 90,
    }
    payload.update(overrides)
    return payload


def _purge_rows(
    db_session: Session,
    *,
    service_ids: list[str],
) -> None:
    for service_id in service_ids:
        db_session.execute(
            text("delete from user_service_roles where service_id = :service_id"),
            {"service_id": service_id},
        )
    for service_id in service_ids:
        db_session.execute(
            text("delete from audit_logs where service_id = :service_id"),
            {"service_id": service_id},
        )
        db_session.execute(
            text("delete from api_keys where service_id = :service_id"),
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
    db_session.commit()


def _purge_session_fixture(db_session: Session, fixture: _SessionFixture) -> None:
    db_session.execute(
        text("delete from admin_sessions where session_id = :session_id"),
        {"session_id": fixture.session_id},
    )
    if fixture.created_user:
        db_session.execute(
            text("delete from user_service_roles where user_id = :user_id"),
            {"user_id": fixture.user_id},
        )
        db_session.execute(
            text("delete from admin_user_roles where user_id = :user_id"),
            {"user_id": fixture.user_id},
        )
        db_session.execute(
            text("delete from admin_users where user_id = :user_id"),
            {"user_id": fixture.user_id},
        )
    db_session.commit()


def test_service_scoped_api_key_lifecycle_never_replays_secret(
    db_session: Session,
) -> None:
    client, session_fixture = _system_admin_client(db_session)
    service_id = f"svc-runtime-setup-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        release_version = _seed_active_release(db_session, service_id)

        created = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            json=_api_key_payload(),
        )

        assert created.status_code == 201
        created_body = created.json()
        raw_secret = created_body["api_key"]
        key_id = created_body["key_id"]
        assert raw_secret.startswith("irt_")
        assert created_body["api_key_displayed_once"] is True
        assert created_body["service_id"] == service_id
        assert created_body["revoked_at"] is None
        assert created_body["allowed_intents"] == ["billing_refund"]
        assert created_body["allowed_route_keys"] == ["billing.refund.request"]

        inventory = client.get(
            f"/admin/v1/services/{service_id}/api-keys",
            params={"environment": "dev", "status": "active"},
        )
        assert inventory.status_code == 200
        inventory_body = inventory.json()
        assert len(inventory_body) == 1
        assert inventory_body[0]["key_id"] == key_id
        assert "api_key" not in inventory_body[0]

        guidance = client.get(
            f"/admin/v1/services/{service_id}/runtime-setup",
            params={"environment": "dev", "app_id": "dify-helpdesk", "key_id": key_id},
        )
        assert guidance.status_code == 200
        guidance_body = guidance.json()
        assert guidance_body["service_id"] == service_id
        assert guidance_body["environment"] == "dev"
        assert guidance_body["runtime_endpoint"] == "/v1/intent-route"
        assert guidance_body["recommended_timeout_seconds"] == 8
        assert guidance_body["active_release"]["release_version"] == release_version
        assert guidance_body["selected_key"]["key_id"] == key_id
        assert guidance_body["selected_key"]["key_fingerprint"] == created_body[
            "key_fingerprint"
        ]
        assert guidance_body["headers_template"]["Authorization"] == (
            "Bearer {{intent_routing_api_key}}"
        )
        assert guidance_body["headers_template"]["X-Key-Id"] == key_id
        assert "intent_routing_api_key" in json.dumps(guidance_body)
        assert raw_secret not in json.dumps(guidance_body, sort_keys=True)

        revoked = client.post(
            f"/admin/v1/services/{service_id}/api-keys/{key_id}:revoke",
        )
        assert revoked.status_code == 200
        revoked_body = revoked.json()
        assert revoked_body["status"] == "revoked"
        assert "api_key" not in revoked_body
        revoked_at = revoked_body["revoked_at"]

        second_revoke = client.post(
            f"/admin/v1/services/{service_id}/api-keys/{key_id}:revoke",
        )
        assert second_revoke.status_code == 200
        assert second_revoke.json()["revoked_at"] == revoked_at

        audit_logs = list(
            db_session.scalars(
                select(models.AuditLog).where(models.AuditLog.target_id == key_id)
            )
        )
        assert audit_logs
        assert [log.event_type for log in audit_logs].count("api_key.revoked") == 1
        for audit_log in audit_logs:
            serialized = json.dumps(
                {
                    "before": audit_log.before_state,
                    "after": audit_log.after_state,
                },
                sort_keys=True,
            )
            assert raw_secret not in serialized
    finally:
        _purge_rows(db_session, service_ids=[service_id])
        _purge_session_fixture(db_session, session_fixture)


def test_service_scoped_key_creation_requires_active_release_candidates(
    db_session: Session,
) -> None:
    client, session_fixture = _system_admin_client(db_session)
    service_id = f"svc-runtime-scope-{uuid4().hex}"
    try:
        _create_service(client, service_id)

        without_release = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            json=_api_key_payload(),
        )
        assert without_release.status_code == 422
        assert "active release" in without_release.json()["error"]["message"].lower()

        _seed_active_release(db_session, service_id)
        unknown_intent = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            json=_api_key_payload(allowed_intents=["manual_internal_id"]),
        )
        unknown_route = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            json=_api_key_payload(allowed_route_keys=["manual.internal.route"]),
        )
        wrong_environment = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            json=_api_key_payload(environment="prod"),
        )

        assert unknown_intent.status_code == 422
        assert "allowed_intents" in unknown_intent.json()["error"]["message"]
        assert unknown_route.status_code == 422
        assert "allowed_route_keys" in unknown_route.json()["error"]["message"]
        assert wrong_environment.status_code == 422
        assert "environment" in wrong_environment.json()["error"]["message"]
    finally:
        _purge_rows(db_session, service_ids=[service_id])
        _purge_session_fixture(db_session, session_fixture)


def test_application_admin_service_developer_can_manage_assigned_service_api_keys(
    db_session: Session,
) -> None:
    system_admin_client, system_admin_session_fixture = _system_admin_client(db_session)
    service_a = f"svc-runtime-app-admin-a-{uuid4().hex}"
    service_b = f"svc-runtime-app-admin-b-{uuid4().hex}"
    application_admin_session_fixture: _SessionFixture | None = None

    try:
        _create_service(system_admin_client, service_a)
        _create_service(system_admin_client, service_b)
        _seed_active_release(db_session, service_a)
        _seed_active_release(db_session, service_b)
        other_service_key = system_admin_client.post(
            f"/admin/v1/services/{service_b}/api-keys",
            json=_api_key_payload(app_id="dify-service-b"),
        )
        assert other_service_key.status_code == 201

        client, application_admin_session_fixture = _application_admin_client(
            db_session,
            service_roles=((service_a, "service_developer"),),
        )
        created = client.post(
            f"/admin/v1/services/{service_a}/api-keys",
            json=_api_key_payload(),
        )

        assert created.status_code == 201
        created_body = created.json()
        key_id = created_body["key_id"]
        assert created_body["service_id"] == service_a

        inventory = client.get(
            f"/admin/v1/services/{service_a}/api-keys",
            params={"environment": "dev", "status": "active"},
        )
        guidance = client.get(
            f"/admin/v1/services/{service_a}/runtime-setup",
            params={"environment": "dev", "app_id": "dify-helpdesk", "key_id": key_id},
        )
        revoked = client.post(
            f"/admin/v1/services/{service_a}/api-keys/{key_id}:revoke",
        )
        denied_other_create = client.post(
            f"/admin/v1/services/{service_b}/api-keys",
            json=_api_key_payload(app_id="dify-other"),
        )
        denied_other_list = client.get(f"/admin/v1/services/{service_b}/api-keys")
        denied_other_guidance = client.get(
            f"/admin/v1/services/{service_b}/runtime-setup",
            params={"environment": "dev"},
        )
        denied_other_revoke = client.post(
            (
                f"/admin/v1/services/{service_b}/api-keys/"
                f"{other_service_key.json()['key_id']}:revoke"
            ),
        )

        assert inventory.status_code == 200
        assert any(row["key_id"] == key_id for row in inventory.json())
        assert guidance.status_code == 200
        assert guidance.json()["selected_key"]["key_id"] == key_id
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"
        for denied in (
            denied_other_create,
            denied_other_list,
            denied_other_guidance,
            denied_other_revoke,
        ):
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"

        persisted_other_key = db_session.get(models.ApiKey, other_service_key.json()["key_id"])
        assert persisted_other_key is not None
        assert persisted_other_key.status == "active"
    finally:
        _purge_rows(db_session, service_ids=[service_a, service_b])
        if application_admin_session_fixture is not None:
            _purge_session_fixture(db_session, application_admin_session_fixture)
        _purge_session_fixture(db_session, system_admin_session_fixture)


def test_application_admin_read_only_service_roles_cannot_manage_service_api_keys(
    db_session: Session,
) -> None:
    system_admin_client, system_admin_session_fixture = _system_admin_client(db_session)
    service_id = f"svc-runtime-app-admin-readonly-{uuid4().hex}"
    fixtures: list[_SessionFixture] = []
    try:
        _create_service(system_admin_client, service_id)
        _seed_active_release(db_session, service_id)

        for role in ("service_operator", "auditor"):
            client, fixture = _application_admin_client(
                db_session,
                service_roles=((service_id, role),),
            )
            fixtures.append(fixture)
            response = client.post(
                f"/admin/v1/services/{service_id}/api-keys",
                json=_api_key_payload(app_id=f"dify-{role}"),
            )

            assert response.status_code == 403, role
            assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    finally:
        _purge_rows(db_session, service_ids=[service_id])
        for fixture in fixtures:
            _purge_session_fixture(db_session, fixture)
        _purge_session_fixture(db_session, system_admin_session_fixture)


def test_service_scoped_revoke_and_guidance_reject_cross_service_key(
    db_session: Session,
) -> None:
    client, session_fixture = _system_admin_client(db_session)
    service_a = f"svc-runtime-a-{uuid4().hex}"
    service_b = f"svc-runtime-b-{uuid4().hex}"
    try:
        _create_service(client, service_a)
        _create_service(client, service_b)
        _seed_active_release(db_session, service_a)
        _seed_active_release(db_session, service_b)
        created = client.post(
            f"/admin/v1/services/{service_a}/api-keys",
            json=_api_key_payload(app_id="dify-service-a"),
        )
        assert created.status_code == 201
        key_id = created.json()["key_id"]

        guidance = client.get(
            f"/admin/v1/services/{service_b}/runtime-setup",
            params={"environment": "dev", "app_id": "dify-service-a", "key_id": key_id},
        )
        revoked = client.post(
            f"/admin/v1/services/{service_b}/api-keys/{key_id}:revoke",
        )

        assert guidance.status_code == 403
        assert guidance.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
        assert revoked.status_code == 403
        assert revoked.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"

        persisted_key = db_session.get(models.ApiKey, key_id)
        assert persisted_key is not None
        assert persisted_key.status == "active"
    finally:
        _purge_rows(db_session, service_ids=[service_a, service_b])
        _purge_session_fixture(db_session, session_fixture)
