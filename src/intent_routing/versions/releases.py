from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


class ReleaseDependencyNotFoundError(ValueError):
    """Raised when a requested release dependency does not exist."""


class ReleaseValidationError(ValueError):
    """Raised when a release gate or version linkage is invalid."""


@dataclass(frozen=True, slots=True)
class ReleaseDependencies:
    policy_version: models.PolicyVersion
    catalog_version: models.IntentCatalogVersion
    test_run: models.TestRun


@dataclass(frozen=True, slots=True)
class ReleaseDiff:
    service_id: str
    release_version: str
    compare_to: str | None
    policy_version_diff: dict[str, object]
    catalog_version_diff: dict[str, object]
    model_version_diff: dict[str, object]
    test_run_diff: dict[str, object]
    rollback_target: str | None


def release_version_id(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    now: datetime,
) -> str:
    prefix = f"rel-{service_id}-{now:%Y%m%d}-"
    existing_versions = repository.list_release_versions_by_prefix(service_id, prefix)
    return f"{prefix}{_next_sequence(existing_versions)}"


def validate_release_inputs(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    environment: str,
    policy_version: str,
    intent_catalog_version: str,
    test_run_id: str,
    rollback_target: str | None,
) -> ReleaseDependencies:
    policy = repository.get_policy_version(service_id, policy_version)
    if policy is None:
        raise ReleaseDependencyNotFoundError("Policy version does not exist.")

    catalog = repository.get_catalog_version(service_id, intent_catalog_version)
    if catalog is None:
        raise ReleaseDependencyNotFoundError("Catalog version does not exist.")
    if catalog.status != "active":
        raise ReleaseValidationError("Catalog version is inactive.")

    test_run = repository.get_test_run(test_run_id)
    if test_run is None or test_run.service_id != service_id:
        raise ReleaseDependencyNotFoundError("Test run does not exist.")

    if not test_run.gate_passed:
        raise ReleaseValidationError("Test run gate must pass before release.")
    if Decimal(str(test_run.risk_pass_rate)) != Decimal("1.0"):
        raise ReleaseValidationError("Test run risk pass rate must be 1.0.")
    if test_run.policy_version != policy_version:
        raise ReleaseValidationError("Test run policy version does not match release.")
    if test_run.intent_catalog_version != intent_catalog_version:
        raise ReleaseValidationError(
            "Test run catalog version does not match release."
        )

    if rollback_target is not None:
        target = repository.get_release(service_id, rollback_target)
        if target is None or target.environment != environment:
            raise ReleaseDependencyNotFoundError(
                "Rollback target release does not exist."
            )

    return ReleaseDependencies(
        policy_version=policy,
        catalog_version=catalog,
        test_run=test_run,
    )


def create_release(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    environment: str,
    policy_version: str,
    intent_catalog_version: str,
    model_version: str,
    test_run_id: str,
    rollback_target: str | None,
    released_by: str,
    now: datetime,
) -> models.Release:
    for lock_key in sorted(
        [
            f"catalog-version:{service_id}",
            f"release-version:{service_id}:{now:%Y%m%d}",
            f"vector-index-version:{intent_catalog_version}:{model_version}",
        ]
    ):
        repository.acquire_advisory_xact_lock(lock_key)

    dependencies = validate_release_inputs(
        repository,
        service_id=service_id,
        environment=environment,
        policy_version=policy_version,
        intent_catalog_version=intent_catalog_version,
        test_run_id=test_run_id,
        rollback_target=rollback_target,
    )

    vector_index = repository.get_ready_vector_index_version(
        service_id,
        intent_catalog_version,
        model_version,
    )
    if vector_index is None:
        raise ReleaseValidationError(
            "Catalog version does not have a ready vector index for the requested model."
        )
    if (
        dependencies.test_run.model_version is not None
        and dependencies.test_run.model_version != vector_index.model_version
    ):
        raise ReleaseValidationError(
            "Test run model version does not match the selected catalog vector index."
        )
    if (
        dependencies.test_run.vector_index_version is not None
        and dependencies.test_run.vector_index_version
        != vector_index.vector_index_version
    ):
        raise ReleaseValidationError(
            "Test run vector index version does not match the selected catalog vector index."
        )
    return repository.create_release(
        release_version=release_version_id(
            repository,
            service_id=service_id,
            now=now,
        ),
        service_id=service_id,
        environment=environment,
        policy_version=policy_version,
        intent_catalog_version=intent_catalog_version,
        model_version=vector_index.model_version,
        vector_index_version=vector_index.vector_index_version,
        test_dataset_version=dependencies.test_run.test_dataset_version,
        test_run_id=test_run_id,
        pass_rate=dependencies.test_run.pass_rate,
        risk_pass_rate=dependencies.test_run.risk_pass_rate,
        active=False,
        released_by=released_by,
        released_at=now,
        rollback_target=rollback_target,
    )


def build_release_diff(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    release_version: str,
    compare_to: str | None = None,
) -> ReleaseDiff:
    candidate = repository.get_release(service_id, release_version)
    if candidate is None:
        raise ReleaseDependencyNotFoundError("Release does not exist.")

    baseline = (
        repository.get_release(service_id, compare_to)
        if compare_to is not None
        else repository.get_active_release(service_id, candidate.environment)
    )
    if baseline is None and compare_to is not None:
        raise ReleaseDependencyNotFoundError("Compare release does not exist.")

    return ReleaseDiff(
        service_id=service_id,
        release_version=candidate.release_version,
        compare_to=baseline.release_version if baseline is not None else None,
        policy_version_diff={
            "from": baseline.policy_version if baseline is not None else None,
            "to": candidate.policy_version,
            "changed": baseline is None
            or baseline.policy_version != candidate.policy_version,
        },
        catalog_version_diff={
            "from": baseline.intent_catalog_version if baseline is not None else None,
            "to": candidate.intent_catalog_version,
            "changed": baseline is None
            or baseline.intent_catalog_version != candidate.intent_catalog_version,
        },
        model_version_diff={
            "from": baseline.model_version if baseline is not None else None,
            "to": candidate.model_version,
            "changed": baseline is None
            or baseline.model_version != candidate.model_version,
        },
        test_run_diff={
            "from": baseline.test_run_id if baseline is not None else None,
            "to": candidate.test_run_id,
            "pass_rate": float(candidate.pass_rate),
            "risk_pass_rate": float(candidate.risk_pass_rate),
            "gate_passed": True,
        },
        rollback_target=candidate.rollback_target,
    )


def activate_release(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    release_version: str,
) -> tuple[dict[str, object], models.Release]:
    release = repository.get_release(service_id, release_version)
    if release is None:
        raise ReleaseDependencyNotFoundError("Release does not exist.")
    before_state = release_after_state(release)
    repository.set_active_release(service_id, release.environment, release.release_version)
    return before_state, release


def rollback_release(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    release_version: str,
) -> tuple[models.Release, dict[str, object], models.Release]:
    release = repository.get_release(service_id, release_version)
    if release is None:
        raise ReleaseDependencyNotFoundError("Release does not exist.")
    if release.rollback_target is None:
        raise ReleaseValidationError("Release does not have a rollback target.")
    rollback_target = repository.get_release(service_id, release.rollback_target)
    if rollback_target is None or rollback_target.environment != release.environment:
        raise ReleaseDependencyNotFoundError("Rollback target release does not exist.")
    before_state = release_after_state(rollback_target)
    repository.set_active_release(
        service_id,
        rollback_target.environment,
        rollback_target.release_version,
    )
    return release, before_state, rollback_target


def release_after_state(release: models.Release) -> dict[str, object]:
    return {
        "release_version": release.release_version,
        "service_id": release.service_id,
        "environment": release.environment,
        "policy_version": release.policy_version,
        "intent_catalog_version": release.intent_catalog_version,
        "model_version": release.model_version,
        "vector_index_version": release.vector_index_version,
        "test_dataset_version": release.test_dataset_version,
        "test_run_id": release.test_run_id,
        "pass_rate": float(release.pass_rate),
        "risk_pass_rate": float(release.risk_pass_rate),
        "active": release.active,
        "released_by": release.released_by,
        "released_at": release.released_at.isoformat(),
        "rollback_target": release.rollback_target,
    }


def _next_sequence(existing_versions: list[str]) -> str:
    max_sequence = 0
    for version in existing_versions:
        _, separator, suffix = version.rpartition("-")
        if separator and suffix.isdecimal():
            max_sequence = max(max_sequence, int(suffix))
    return f"{max_sequence + 1:03d}"
