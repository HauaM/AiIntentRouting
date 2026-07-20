from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


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
