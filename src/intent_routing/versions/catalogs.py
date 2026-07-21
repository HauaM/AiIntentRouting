from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import get_embedding_provider


class CatalogVersionValidationError(ValueError):
    pass


class CatalogVersionDependencyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CatalogVersionDiff:
    service_id: str
    from_version: str | None
    to_version: str
    added_intents: list[str]
    removed_intents: list[str]
    changed_intents: list[str]
    added_examples: list[dict[str, str]]
    removed_examples: list[dict[str, str]]
    changed_examples: list[dict[str, str]]


def next_display_version(repository: IntentRoutingRepository, service_id: str) -> str:
    existing = repository.list_catalog_display_versions(service_id)
    numbers = [
        int(value[1:])
        for value in existing
        if value.startswith("v") and value[1:].isdigit()
    ]
    return f"v{max(numbers, default=0) + 1}"


def normalize_description(description: str) -> str:
    normalized = description.strip()
    if len(normalized) < 10:
        raise CatalogVersionValidationError(
            "Catalog version description must be at least 10 characters."
        )
    return normalized


def create_catalog_version(
    repository: IntentRoutingRepository,
    service: models.Service,
    description: str,
    created_by: str,
    now: datetime,
    model_version: str,
    source_catalog_version: str | None = None,
) -> models.IntentCatalogVersion:
    description = normalize_description(description)
    if source_catalog_version is not None and repository.get_catalog_version(
        service.service_id, source_catalog_version
    ) is None:
        raise CatalogVersionDependencyError("Source catalog version does not exist.")

    repository.acquire_advisory_xact_lock(f"catalog-version:{service.service_id}")
    catalog_id = f"cat-{service.service_id}-{now:%Y%m%d}-{uuid4().hex[:8]}"
    display_version = next_display_version(repository, service.service_id)
    examples = [
        example
        for intent in repository.list_intents(service.service_id)
        for example in repository.list_examples(service.service_id, intent.intent_id)
    ]
    provider = get_embedding_provider()
    if provider.model_version != model_version:
        raise CatalogVersionValidationError("Embedding model version does not match provider.")
    embeddings = provider.embed_texts(
        [example.text_masked for example in examples],
        max_tokens=service.max_input_tokens,
    )
    if len(embeddings) != len(examples) or any(
        len(embedding) != provider.dimension for embedding in embeddings
    ):
        raise CatalogVersionValidationError("Embedding provider returned an invalid result.")

    snapshot = _catalog_snapshot(repository, service.service_id)
    catalog_version = repository.create_catalog_version(
        intent_catalog_version=catalog_id,
        service_id=service.service_id,
        display_version=display_version,
        description=description,
        status="active",
        reproducibility_status="complete",
        source_catalog_version=source_catalog_version,
        snapshot=snapshot,
        created_by=created_by,
        created_at=now,
        activated_at=now,
        deactivated_at=None,
    )
    vector_index_version = _vector_index_version_id(
        repository, catalog_id, model_version
    )
    repository.create_vector_index_version(
        vector_index_version=vector_index_version,
        service_id=service.service_id,
        intent_catalog_version=catalog_id,
        model_version=model_version,
        status="ready",
        created_at=now,
    )
    for example, embedding in zip(examples, embeddings, strict=True):
        repository.create_catalog_version_example_embedding(
            intent_catalog_version=catalog_id,
            service_id=service.service_id,
            model_version=model_version,
            vector_index_version=vector_index_version,
            intent_id=example.intent_id,
            example_id=example.example_id,
            example_type=example.example_type,
            text_raw_ciphertext=example.text_raw_ciphertext,
            text_raw_encrypted_dek=example.text_raw_encrypted_dek,
            text_raw_encrypted_dek_iv=example.text_raw_encrypted_dek_iv,
            text_raw_encrypted_dek_auth_tag=example.text_raw_encrypted_dek_auth_tag,
            text_raw_key_id=example.text_raw_key_id,
            text_raw_iv=example.text_raw_iv,
            text_raw_auth_tag=example.text_raw_auth_tag,
            text_raw_algorithm=example.text_raw_algorithm,
            text_masked=example.text_masked,
            embedding=embedding,
            embedding_status="active",
            created_at=now,
            deactivated_at=None,
        )
    return catalog_version


def build_catalog_version_diff(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    intent_catalog_version: str,
    compare_to: str | None,
) -> CatalogVersionDiff:
    target = repository.get_catalog_version(service_id, intent_catalog_version)
    if target is None:
        raise CatalogVersionDependencyError("Catalog version does not exist.")
    baseline = (
        repository.get_catalog_version(service_id, compare_to)
        if compare_to is not None
        else None
    )
    if compare_to is not None and baseline is None:
        raise CatalogVersionDependencyError("Compare catalog version does not exist.")
    before = _snapshot_items(baseline.snapshot if baseline is not None else {})
    after = _snapshot_items(target.snapshot)
    return CatalogVersionDiff(
        service_id=service_id,
        from_version=baseline.intent_catalog_version if baseline is not None else None,
        to_version=target.intent_catalog_version,
        added_intents=sorted(set(after[0]) - set(before[0])),
        removed_intents=sorted(set(before[0]) - set(after[0])),
        changed_intents=_changed(before[0], after[0]),
        added_examples=_example_diff_entries(
            sorted(set(after[1]) - set(before[1])), after[1]
        ),
        removed_examples=_example_diff_entries(
            sorted(set(before[1]) - set(after[1])), before[1]
        ),
        changed_examples=_example_diff_entries(
            _changed_examples(before[1], after[1]), after[1]
        ),
    )


def _catalog_snapshot(repository: IntentRoutingRepository, service_id: str) -> dict[str, object]:
    intents: list[dict[str, object]] = []
    for intent in repository.list_intents(service_id):
        examples = repository.list_examples(service_id, intent.intent_id)
        intents.append(
            {
                "intent_id": intent.intent_id,
                "domain": intent.domain,
                "display_name": intent.display_name,
                "description": intent.description,
                "route_key": intent.route_key,
                "status": "active",
                "include_keywords": list(intent.include_keywords or []),
                "exclude_keywords": list(intent.exclude_keywords or []),
                "examples": [
                    {
                        "example_id": str(example.example_id),
                        "example_type": example.example_type,
                        "text_masked": example.text_masked,
                        "approved": True,
                    }
                    for example in examples
                ],
            }
        )
    return {"service_id": service_id, "intents": intents}


def _vector_index_version_id(
    repository: IntentRoutingRepository,
    catalog_id: str,
    model_version: str,
) -> str:
    prefix = f"vec-{catalog_id}-{model_version}-"
    existing = repository.list_vector_index_versions_by_prefix(prefix)
    numbers = [
        int(value.rpartition("-")[2])
        for value in existing
        if value.rpartition("-")[2].isdigit()
    ]
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


def _snapshot_items(
    snapshot: object,
) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    if not isinstance(snapshot, dict):
        return {}, {}
    intents = snapshot.get("intents", [])
    if not isinstance(intents, list):
        return {}, {}
    intent_items: dict[str, object] = {
        str(item["intent_id"]): item
        for item in intents
        if isinstance(item, dict) and "intent_id" in item
    }
    examples: dict[str, dict[str, object]] = {}
    for item in intents:
        if not isinstance(item, dict) or not isinstance(item.get("examples"), list):
            continue
        for example in item["examples"]:
            if not isinstance(example, dict) or "example_id" not in example:
                continue
            examples[str(example["example_id"])] = {
                **example,
                "intent_id": item.get("intent_id"),
                "intent_display_name": item.get("display_name"),
                "route_key": item.get("route_key"),
            }
    return intent_items, examples


def _changed(before: dict[str, object], after: dict[str, object]) -> list[str]:
    return sorted(key for key in set(before) & set(after) if before[key] != after[key])


def _changed_examples(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
) -> list[str]:
    return sorted(
        key
        for key in set(before) & set(after)
        if _example_comparison_state(before[key]) != _example_comparison_state(after[key])
    )


def _example_comparison_state(example: dict[str, object]) -> dict[str, object]:
    return {
        "intent_id": example.get("intent_id"),
        "example_type": example.get("example_type"),
        "text_masked": example.get("text_masked"),
        "approved": example.get("approved"),
    }


def _example_diff_entries(
    example_ids: list[str],
    examples: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "intent_id": str(example.get("intent_id") or "-"),
            "intent_display_name": str(example.get("intent_display_name") or "-"),
            "route_key": str(example.get("route_key") or "-"),
            "example_type": str(example.get("example_type") or "-"),
            "text_masked": str(example.get("text_masked") or "-"),
        }
        for example_id in example_ids
        if (example := examples.get(example_id)) is not None
    ]
