from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.diagnostics.models import CatalogVersionDiagnosticStats
from intent_routing.diagnostics.test_runs import diagnose_test_run
from intent_routing.main import create_app
from intent_routing.testing.csv_runner import CsvTestRunSummary


def _admin_headers() -> dict[str, str]:
    return {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "admin-user",
        "X-Actor-Roles": "system_admin",
    }


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


def test_repository_returns_catalog_version_diagnostic_stats(db_session: Session) -> None:
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]
    service = models.Service(
        service_id=f"diagnostics-service-{suffix}",
        display_name="Diagnostics Service",
        environment="test",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="test",
        created_at=now,
        updated_at=now,
    )
    catalog = models.IntentCatalogVersion(
        intent_catalog_version=f"cat-diagnostics-service-{suffix}",
        display_version="v1",
        service_id=service.service_id,
        snapshot={
            "service_id": service.service_id,
            "intents": [
                {
                    "intent_id": "program_supported_question",
                    "examples": [{"example_id": str(uuid4()), "example_type": "positive"}],
                }
            ],
        },
        description="diagnostic test version",
        status="active",
        reproducibility_status="complete",
        source_catalog_version=None,
        activated_at=now,
        deactivated_at=None,
        created_by="test",
        created_at=now,
    )
    db_session.add_all([service, catalog])
    db_session.flush()

    vector_index = models.VectorIndexVersion(
        vector_index_version=f"viv-diagnostics-service-{suffix}",
        service_id=service.service_id,
        intent_catalog_version=catalog.intent_catalog_version,
        model_version="fake-embedding-v1",
        status="ready",
        created_at=now,
    )
    db_session.add(vector_index)
    db_session.flush()

    embedding = models.CatalogVersionExampleEmbedding(
        id=uuid4(),
        intent_catalog_version=catalog.intent_catalog_version,
        service_id=service.service_id,
        model_version="fake-embedding-v1",
        vector_index_version=vector_index.vector_index_version,
        intent_id="program_supported_question",
        example_id=None,
        example_type="positive",
        text_raw_ciphertext=b"ciphertext",
        text_raw_encrypted_dek=b"dek",
        text_raw_encrypted_dek_iv=b"dek-iv",
        text_raw_encrypted_dek_auth_tag=b"dek-tag",
        text_raw_key_id="test-key",
        text_raw_iv=b"raw-iv",
        text_raw_auth_tag=b"raw-tag",
        text_raw_algorithm="AES-256-GCM",
        text_masked="masked diagnostic example",
        embedding=[0.0] * 1024,
        embedding_status="active",
        created_at=now,
        deactivated_at=None,
    )
    db_session.add(embedding)
    db_session.commit()

    stats = IntentRoutingRepository(db_session).get_catalog_version_diagnostic_record(
        service.service_id,
        catalog.intent_catalog_version,
        model_version=vector_index.model_version,
        vector_index_version=vector_index.vector_index_version,
    )

    assert stats is not None
    assert stats.intent_catalog_version == catalog.intent_catalog_version
    assert stats.display_version == "v1"
    assert stats.status == "active"
    assert stats.reproducibility_status == "complete"
    assert stats.intent_count == 1
    assert stats.example_count == 1
    assert stats.embedding_count == 1
    assert stats.ready_vector_index_version == vector_index.vector_index_version
    assert stats.ready_vector_index_model_version == vector_index.model_version


def test_repository_distinguishes_stale_selected_vector_index(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]
    service = models.Service(
        service_id=f"diagnostics-stale-index-service-{suffix}",
        display_name="Diagnostics Stale Index Service",
        environment="test",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="test",
        created_at=now,
        updated_at=now,
    )
    catalog = models.IntentCatalogVersion(
        intent_catalog_version=f"cat-diagnostics-stale-index-{suffix}",
        display_version="v1",
        service_id=service.service_id,
        snapshot={
            "service_id": service.service_id,
            "intents": [
                {
                    "intent_id": "program_supported_question",
                    "examples": [
                        {
                            "example_id": str(uuid4()),
                            "example_type": "positive",
                        }
                    ],
                }
            ],
        },
        description="diagnostic stale index test version",
        status="active",
        reproducibility_status="complete",
        source_catalog_version=None,
        activated_at=now,
        deactivated_at=None,
        created_by="test",
        created_at=now,
    )
    selected_index = models.VectorIndexVersion(
        vector_index_version=f"viv-diagnostics-stale-selected-{suffix}",
        service_id=service.service_id,
        intent_catalog_version=catalog.intent_catalog_version,
        model_version="fake-embedding-v1",
        status="building",
        created_at=now,
    )
    ready_index = models.VectorIndexVersion(
        vector_index_version=f"viv-diagnostics-stale-ready-{suffix}",
        service_id=service.service_id,
        intent_catalog_version=catalog.intent_catalog_version,
        model_version="fake-embedding-v1",
        status="ready",
        created_at=now,
    )
    db_session.add_all([service, catalog, selected_index, ready_index])
    db_session.commit()

    stats = IntentRoutingRepository(db_session).get_catalog_version_diagnostic_record(
        service.service_id,
        catalog.intent_catalog_version,
        model_version=selected_index.model_version,
        vector_index_version=selected_index.vector_index_version,
    )

    assert stats is not None
    assert stats.ready_vector_index_version == ready_index.vector_index_version
    diagnostics = diagnose_test_run(
        CsvTestRunSummary(
            test_run_id="tr-diagnostics-stale-index",
            test_dataset_version="tds-diagnostics-stale-index",
            model_version=selected_index.model_version,
            vector_index_version=selected_index.vector_index_version,
            threshold_preset="balanced",
            threshold_value=0.8,
            pass_rate=1.0,
            review_rate=0.0,
            risk_pass_rate=1.0,
            gate_passed=True,
            block_reasons=[],
            recommendations=[],
        ),
        CatalogVersionDiagnosticStats(
            intent_catalog_version=stats.intent_catalog_version,
            display_version=stats.display_version,
            status=stats.status,
            reproducibility_status=stats.reproducibility_status,
            intent_count=stats.intent_count,
            example_count=stats.example_count,
            embedding_count=stats.embedding_count,
            test_run_model_version=stats.test_run_model_version,
            test_run_vector_index_version=stats.test_run_vector_index_version,
            ready_vector_index_version=stats.ready_vector_index_version,
            ready_vector_index_model_version=stats.ready_vector_index_model_version,
        ),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "test_run_vector_index_not_ready"


def test_get_test_run_diagnostics_reports_selected_catalog_readiness(
    client: TestClient,
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]
    service = models.Service(
        service_id=f"diagnostics-api-service-{suffix}",
        display_name="Diagnostics API Service",
        environment="test",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="test",
        created_at=now,
        updated_at=now,
    )
    policy = models.PolicyVersion(
        policy_version=f"pol-diagnostics-api-service-{suffix}",
        service_id=service.service_id,
        threshold_preset="balanced",
        threshold_value=Decimal("0.8"),
        clarify_margin=Decimal("0.08"),
        min_candidate_score=Decimal("0.55"),
        fallback_score=Decimal("0.45"),
        risk_policy={"enabled": True},
        off_topic_policy={"enabled": True, "keywords": [], "message": ""},
        created_by="test",
        created_at=now,
    )
    catalog = models.IntentCatalogVersion(
        intent_catalog_version=f"cat-diagnostics-api-service-{suffix}",
        display_version="v1",
        service_id=service.service_id,
        snapshot={"service_id": service.service_id, "intents": []},
        description="진단 API 테스트 버전입니다",
        status="active",
        reproducibility_status="complete",
        source_catalog_version=None,
        activated_at=now,
        deactivated_at=None,
        created_by="test",
        created_at=now,
    )
    dataset = models.TestDataset(
        test_dataset_version=f"tds-diagnostics-api-service-{suffix}",
        service_id=service.service_id,
        source_filename="test-cases.csv",
        content_sha256="0" * 64,
        created_by="test",
        created_at=now,
    )
    test_run = models.TestRun(
        test_run_id=f"tr-diagnostics-api-service-{suffix}",
        service_id=service.service_id,
        test_dataset_version=dataset.test_dataset_version,
        policy_version=policy.policy_version,
        intent_catalog_version=catalog.intent_catalog_version,
        model_version=None,
        vector_index_version=None,
        threshold_preset="balanced",
        threshold_value=Decimal("0.8"),
        pass_rate=Decimal("0.0"),
        review_rate=Decimal("0.0"),
        risk_pass_rate=Decimal("1.0"),
        gate_passed=False,
        created_by="test",
        created_at=now,
    )
    result = models.TestResult(
        test_run_id=test_run.test_run_id,
        case_id="C001",
        query_masked="인터넷뱅킹 화면에서 500 오류가 발생해요",
        case_type="positive",
        expected_decision="confident",
        expected_intent="program_supported_question",
        actual_decision="fallback",
        actual_intent=None,
        actual_route_key=None,
        confidence=None,
        result="FAIL",
        reason="actual decision did not match expected decision",
    )
    db_session.add_all([service, policy, catalog, dataset, test_run, result])
    db_session.commit()

    response = client.get(
        f"/admin/v1/services/{service.service_id}/test-runs/{test_run.test_run_id}/diagnostics",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["primary_issue"]["code"] == "catalog_version_has_no_intents"
    assert body["catalog_version"]["intent_catalog_version"] == catalog.intent_catalog_version
    assert body["catalog_version"]["intent_count"] == 0
    assert body["result_counts"]["FAIL"] == 1
    assert body["actual_decision_counts"]["fallback"] == 1
