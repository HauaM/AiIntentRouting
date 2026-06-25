from collections.abc import Iterable
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from intent_routing.db import models

ModelT = TypeVar("ModelT")


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

    def list_active_intents(self, service_id: str) -> list[models.Intent]:
        return list(
            self.session.scalars(
                select(models.Intent)
                .where(models.Intent.service_id == service_id)
                .where(models.Intent.status == "active")
                .order_by(models.Intent.intent_id)
            )
        )

    def create_example(self, **values: Any) -> models.IntentExample:
        return self._add_and_flush(models.IntentExample(**values))

    def create_policy_version(self, **values: Any) -> models.PolicyVersion:
        return self._add_and_flush(models.PolicyVersion(**values))

    def create_catalog_version(self, **values: Any) -> models.IntentCatalogVersion:
        return self._add_and_flush(models.IntentCatalogVersion(**values))

    def create_test_dataset(
        self,
        dataset_values: dict[str, Any],
        cases: Iterable[dict[str, Any]] = (),
    ) -> models.TestDataset:
        test_dataset_version = dataset_values["test_dataset_version"]
        dataset = models.TestDataset(**dataset_values)
        self.session.add(dataset)
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
