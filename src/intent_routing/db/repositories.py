from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import bindparam, select, text, update
from sqlalchemy.orm import Session

from intent_routing.db import models

ModelT = TypeVar("ModelT")


@dataclass(frozen=True, slots=True)
class ExampleSearchResult:
    example_id: UUID
    intent_id: str
    example_type: str
    similarity: float


class IntentRoutingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _add_and_flush(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def create_service(self, **values: Any) -> models.Service:
        return self._add_and_flush(models.Service(**values))

    def get_service(self, service_id: str) -> models.Service | None:
        return self.session.get(models.Service, service_id)

    def create_api_key(self, **values: Any) -> models.ApiKey:
        return self._add_and_flush(models.ApiKey(**values))

    def get_api_key_by_id(self, key_id: str) -> models.ApiKey | None:
        return self.session.get(models.ApiKey, key_id)

    def revoke_api_key(
        self,
        api_key: models.ApiKey,
        *,
        revoked_at: datetime,
    ) -> models.ApiKey:
        api_key.status = "revoked"
        api_key.revoked_at = revoked_at
        self.session.flush()
        return api_key

    def create_intent(self, **values: Any) -> models.Intent:
        return self._add_and_flush(models.Intent(**values))

    def get_intent(self, service_id: str, intent_id: str) -> models.Intent | None:
        return self.session.scalar(
            select(models.Intent)
            .where(models.Intent.service_id == service_id)
            .where(models.Intent.intent_id == intent_id)
        )

    def list_intents(self, service_id: str) -> list[models.Intent]:
        return list(
            self.session.scalars(
                select(models.Intent)
                .where(models.Intent.service_id == service_id)
                .order_by(models.Intent.intent_id)
            )
        )

    def list_active_intents(self, service_id: str) -> list[models.Intent]:
        return list(
            self.session.scalars(
                select(models.Intent)
                .where(models.Intent.service_id == service_id)
                .where(models.Intent.status == "active")
                .order_by(models.Intent.intent_id)
            )
        )

    def update_intent(self, intent: models.Intent, **values: Any) -> models.Intent:
        for key, value in values.items():
            setattr(intent, key, value)
        self.session.flush()
        return intent

    def create_example(self, **values: Any) -> models.IntentExample:
        return self._add_and_flush(models.IntentExample(**values))

    def get_example(
        self,
        service_id: str,
        example_id: UUID,
    ) -> models.IntentExample | None:
        return self.session.scalar(
            select(models.IntentExample)
            .where(models.IntentExample.service_id == service_id)
            .where(models.IntentExample.example_id == example_id)
        )

    def list_examples(self, service_id: str, intent_id: str) -> list[models.IntentExample]:
        return list(
            self.session.scalars(
                select(models.IntentExample)
                .where(models.IntentExample.service_id == service_id)
                .where(models.IntentExample.intent_id == intent_id)
                .order_by(models.IntentExample.created_at, models.IntentExample.example_id)
            )
        )

    def approve_example(
        self,
        example: models.IntentExample,
        *,
        embedding: list[float] | None = None,
    ) -> models.IntentExample:
        example.approved = True
        if embedding is not None:
            example.embedding = embedding
        self.session.flush()
        return example

    def search_approved_examples_by_embedding(
        self,
        service_id: str,
        query_embedding: list[float],
        *,
        limit: int,
    ) -> list[ExampleSearchResult]:
        if len(query_embedding) != 1024:
            raise ValueError("query_embedding must have 1024 dimensions")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        statement = text(
            """
            SELECT example_id,
                   intent_id,
                   example_type,
                   1 - (embedding <=> :query_embedding) AS similarity
            FROM intent_examples
            WHERE service_id = :service_id
              AND approved = true
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :query_embedding
            LIMIT :limit
            """
        ).bindparams(bindparam("query_embedding", type_=Vector(1024)))
        rows = self.session.execute(
            statement,
            {
                "service_id": service_id,
                "query_embedding": query_embedding,
                "limit": limit,
            },
        ).mappings()
        return [
            ExampleSearchResult(
                example_id=row["example_id"],
                intent_id=row["intent_id"],
                example_type=row["example_type"],
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]

    def create_policy_version(self, **values: Any) -> models.PolicyVersion:
        return self._add_and_flush(models.PolicyVersion(**values))

    def get_policy_version(
        self,
        service_id: str,
        policy_version: str,
    ) -> models.PolicyVersion | None:
        return self.session.scalar(
            select(models.PolicyVersion)
            .where(models.PolicyVersion.service_id == service_id)
            .where(models.PolicyVersion.policy_version == policy_version)
        )

    def create_catalog_version(self, **values: Any) -> models.IntentCatalogVersion:
        return self._add_and_flush(models.IntentCatalogVersion(**values))

    def get_catalog_version(
        self,
        service_id: str,
        intent_catalog_version: str,
    ) -> models.IntentCatalogVersion | None:
        return self.session.scalar(
            select(models.IntentCatalogVersion)
            .where(models.IntentCatalogVersion.service_id == service_id)
            .where(
                models.IntentCatalogVersion.intent_catalog_version
                == intent_catalog_version
            )
        )

    def create_test_dataset(
        self,
        dataset_values: dict[str, Any],
        cases: Iterable[dict[str, Any]] = (),
    ) -> models.TestDataset:
        test_dataset_version = dataset_values["test_dataset_version"]
        dataset = models.TestDataset(**dataset_values)
        self.session.add(dataset)
        self.session.flush()
        for case_values in cases:
            normalized_case_values = dict(case_values)
            case_dataset_version = normalized_case_values.setdefault(
                "test_dataset_version",
                test_dataset_version,
            )
            if case_dataset_version != test_dataset_version:
                raise ValueError("case test_dataset_version must match dataset")
            self.session.add(models.TestCase(**normalized_case_values))
        self.session.flush()
        return dataset

    def create_test_run_with_results(
        self,
        test_run_values: dict[str, Any],
        results: Iterable[dict[str, Any]],
    ) -> models.TestRun:
        test_run = models.TestRun(**test_run_values)
        self.session.add(test_run)
        self.session.flush()
        for result_values in results:
            self.session.add(
                models.TestResult(test_run_id=test_run.test_run_id, **result_values)
            )
        self.session.flush()
        return test_run

    def get_test_run(self, test_run_id: str) -> models.TestRun | None:
        return self.session.get(models.TestRun, test_run_id)

    def list_test_results(self, test_run_id: str) -> list[models.TestResult]:
        return list(
            self.session.scalars(
                select(models.TestResult)
                .where(models.TestResult.test_run_id == test_run_id)
                .order_by(models.TestResult.case_id)
            )
        )

    def create_release(self, **values: Any) -> models.Release:
        return self._add_and_flush(models.Release(**values))

    def get_active_release(self, service_id: str, environment: str) -> models.Release | None:
        return self.session.scalar(
            select(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.environment == environment)
            .where(models.Release.active.is_(True))
            .order_by(models.Release.released_at.desc())
        )

    def set_active_release(self, service_id: str, environment: str, release_version: str) -> None:
        target_release = self.session.scalar(
            select(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.environment == environment)
            .where(models.Release.release_version == release_version)
        )
        if target_release is None:
            raise ValueError("release_version does not match service_id and environment")

        self.session.execute(
            update(models.Release)
            .where(models.Release.service_id == service_id)
            .where(models.Release.environment == environment)
            .values(active=False)
        )
        target_release.active = True
        self.session.flush()

    def insert_runtime_log(self, **values: Any) -> models.RuntimeLog:
        return self._add_and_flush(models.RuntimeLog(**values))

    def insert_audit_log(self, **values: Any) -> models.AuditLog:
        return self._add_and_flush(models.AuditLog(**values))
