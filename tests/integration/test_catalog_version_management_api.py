from __future__ import annotations

import base64
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app


def _admin_headers() -> dict[str, str]:
    return {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "admin-user",
        "X-Actor-Roles": "system_admin",
    }


@pytest.fixture
def client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv(
        "RAW_TEXT_KEK_BASE64",
        base64.b64encode(b"0" * 32).decode("ascii"),
    )
    clear_embedding_provider_cache()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    clear_embedding_provider_cache()


@pytest.fixture
def service_id(client: TestClient) -> str:
    value = f"svc-catalog-{uuid4().hex}"
    response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(),
        json={
            "service_id": value,
            "display_name": "Catalog version test service",
            "environment": "test",
            "default_threshold_preset": "balanced",
            "max_input_tokens": 256,
        },
    )
    assert response.status_code == 201
    return value


def _create_intent(client: TestClient, service_id: str, *, status: str) -> str:
    intent_id = f"intent-{uuid4().hex}"
    response = client.post(
        f"/admin/v1/services/{service_id}/intents",
        headers=_admin_headers(),
        json={
            "intent_id": intent_id,
            "domain": "it",
            "display_name": "Catalog version intent",
            "description": "Route catalog version test traffic.",
            "route_key": "it.catalog.version",
            "include_keywords": ["catalog", "version"],
            "exclude_keywords": [],
        },
    )
    assert response.status_code == 201
    if status != "draft":
        response = client.patch(
            f"/admin/v1/services/{service_id}/intents/{intent_id}",
            headers=_admin_headers(),
            json={"status": status},
        )
        assert response.status_code == 200
    return intent_id


def _create_example(
    client: TestClient,
    service_id: str,
    intent_id: str,
    *,
    approved: bool,
) -> str:
    response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent_id}/examples",
        headers=_admin_headers(),
        json={
            "example_type": "positive",
            "text_raw": "Catalog version example text",
            "source": "catalog-version-test",
            "test_case_id": None,
        },
    )
    assert response.status_code == 201
    example_id = cast("dict[str, Any]", response.json())["example_id"]
    if approved:
        response = client.patch(
            f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
            headers=_admin_headers(),
        )
        assert response.status_code == 200
    return str(example_id)


def test_catalog_version_registration_requires_description(
    client: TestClient,
    service_id: str,
) -> None:
    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "짧음"},
    )

    assert response.status_code == 422


def test_catalog_version_registration_assigns_display_version_and_embeddings(
    client: TestClient,
    db_session: Session,
    service_id: str,
) -> None:
    intent_id = _create_intent(client, service_id, status="draft")
    _create_example(client, service_id, intent_id, approved=False)

    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "첫 번째 catalog 버전 등록"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["display_version"] == "v1"
    assert body["status"] == "active"
    assert body["reproducibility_status"] == "complete"
    assert body["description"] == "첫 번째 catalog 버전 등록"
    assert body["intent_count"] == 1
    assert body["example_count"] == 1

    rows = db_session.execute(
        text(
            "select count(*) from catalog_version_example_embeddings "
            "where intent_catalog_version = :version "
            "and model_version = :model_version "
            "and embedding_status = 'active'"
        ),
        {
            "version": body["intent_catalog_version"],
            "model_version": body["model_version"],
        },
    ).scalar_one()
    assert rows == 1


def test_catalog_version_deactivation_clears_version_scoped_vectors(
    client: TestClient,
    db_session: Session,
    service_id: str,
) -> None:
    intent_id = _create_intent(client, service_id, status="draft")
    _create_example(client, service_id, intent_id, approved=False)
    created = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "Deactivate catalog version"},
    )
    assert created.status_code == 201
    catalog_version = created.json()["intent_catalog_version"]

    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions/{catalog_version}:deactivate",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    rows = db_session.execute(
        text(
            "select count(*) from catalog_version_example_embeddings "
            "where intent_catalog_version = :version "
            "and embedding_status = 'active'"
        ),
        {"version": catalog_version},
    ).scalar_one()
    assert rows == 0
    null_vectors = db_session.execute(
        text(
            "select count(*) from catalog_version_example_embeddings "
            "where intent_catalog_version = :version and embedding is null"
        ),
        {"version": catalog_version},
    ).scalar_one()
    assert null_vectors == 1


def test_catalog_version_deactivation_is_blocked_when_release_references_it(
    client: TestClient,
    db_session: Session,
    service_id: str,
) -> None:
    intent_id = _create_intent(client, service_id, status="draft")
    _create_example(client, service_id, intent_id, approved=False)
    created = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "Release referenced catalog"},
    )
    assert created.status_code == 201
    catalog_version = created.json()["intent_catalog_version"]
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    policy_version = f"policy-{uuid4().hex}"
    dataset_version = f"dataset-{uuid4().hex}"
    test_run_id = f"run-{uuid4().hex}"
    repository.create_policy_version(
        policy_version=policy_version, service_id=service_id, threshold_preset="balanced",
        threshold_value=Decimal("0.8"), clarify_margin=Decimal("0.1"),
        min_candidate_score=Decimal("0.5"), fallback_score=Decimal("0.4"),
        risk_policy={}, off_topic_policy={}, created_by="test", created_at=now,
    )
    repository.create_test_dataset(
        {"test_dataset_version": dataset_version, "service_id": service_id,
         "source_filename": "test.csv", "content_sha256": "test",
         "created_by": "test", "created_at": now}
    )
    repository.create_test_run_with_results(
        {"test_run_id": test_run_id, "service_id": service_id,
         "test_dataset_version": dataset_version, "policy_version": policy_version,
         "intent_catalog_version": catalog_version, "threshold_preset": "balanced",
         "threshold_value": Decimal("0.8"), "pass_rate": Decimal("1"),
         "review_rate": Decimal("0"), "risk_pass_rate": Decimal("1"),
         "gate_passed": True, "created_by": "test", "created_at": now}, []
    )
    repository.create_release(
        release_version=f"release-{uuid4().hex}", service_id=service_id, environment="test",
        policy_version=policy_version, intent_catalog_version=catalog_version,
        model_version=created.json()["model_version"],
        vector_index_version=created.json()["vector_index_version"],
        test_dataset_version=dataset_version, test_run_id=test_run_id,
        pass_rate=Decimal("1"), risk_pass_rate=Decimal("1"), active=False,
        released_by="test", released_at=now, rollback_target=None,
    )
    db_session.commit()

    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions/{catalog_version}:deactivate",
        headers=_admin_headers(),
    )

    assert response.status_code == 409
    assert "Release" in response.text


def test_catalog_version_load_to_draft_restores_editable_snapshot(
    client: TestClient,
    db_session: Session,
    service_id: str,
) -> None:
    intent_id = _create_intent(client, service_id, status="draft")
    _create_example(client, service_id, intent_id, approved=False)
    created = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "Load catalog into draft"},
    )
    version = created.json()["intent_catalog_version"]
    assert client.delete(
        f"/admin/v1/services/{service_id}/intents/{intent_id}",
        headers=_admin_headers(),
    ).status_code == 204

    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions/{version}:load-to-draft",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    intent = db_session.scalar(
        text(
            "select status from intents where service_id = :service_id "
            "and intent_id = :intent_id"
        ),
        {"service_id": service_id, "intent_id": intent_id},
    )
    assert intent == "draft"
    examples = client.get(
        f"/admin/v1/services/{service_id}/intents/{intent_id}/examples",
        headers=_admin_headers(),
    ).json()
    assert examples[0]["text_masked"] == "Catalog version example text"
    assert examples[0]["approved"] is False
    assert db_session.execute(
        text("select embedding is null from intent_examples where example_id = :id"),
        {"id": examples[0]["example_id"]},
    ).scalar_one()
    assert db_session.execute(
        text("select count(*) from audit_logs where event_type = 'catalog_version.loaded_to_draft'")
    ).scalar_one() >= 1


def test_catalog_version_diff_reports_added_example(
    client: TestClient,
    service_id: str,
) -> None:
    intent_id = _create_intent(client, service_id, status="draft")
    _create_example(client, service_id, intent_id, approved=False)
    first = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(), json={"description": "First diff catalog"},
    ).json()["intent_catalog_version"]
    _create_example(client, service_id, intent_id, approved=False)
    second = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(), json={"description": "Second diff catalog"},
    ).json()["intent_catalog_version"]

    response = client.get(
        f"/admin/v1/services/{service_id}/catalog-versions/{second}/diff",
        headers=_admin_headers(), params={"compare_to": first},
    )

    assert response.status_code == 200
    assert len(response.json()["added_examples"]) == 1
