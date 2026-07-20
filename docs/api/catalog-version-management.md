# Catalog Version Management API

Base path: `/admin/v1`.

Catalog versions are immutable snapshots of the editable Intent Catalog. A
version includes the Intent snapshot, approved-in-version Example semantics,
and version-scoped Example embeddings for one embedding model.

## Lifecycle Rules

- `display_version` is assigned by the system per Service as `v1`, `v2`, `v3`, ...
- Creating a catalog version requires a trimmed `description` of at least 10 characters.
- The version snapshot treats included Intents as active and included Examples as approved.
- Version-scoped semantic search must use `intent_catalog_version + model_version`.
- Deactivation is blocked while any Release references the catalog version.
- Deactivation marks the catalog version inactive and removes active vectors from version-scoped embedding rows.
- Loading a version to draft copies the snapshot into the editable Intent/Example tables and does not mutate the historical version.

## POST /services/{service_id}/catalog-versions

Creates an immutable catalog version from the current editable Intent Catalog.

Request:

```json
{
  "description": "baseline after password reset examples",
  "source_catalog_version": "cat-svc-20260720-abc123"
}
```

`source_catalog_version` is optional. `description` is required and must be at least 10 characters after trimming.

Response: `CatalogVersionResponse`.

Important fields:

- `intent_catalog_version`
- `display_version`
- `description`
- `status`
- `released`
- `release_count`
- `model_version`
- `vector_index_version`
- `intent_count`
- `example_count`
- `embedding_count`
- `snapshot`

## GET /services/{service_id}/catalog-versions

Lists catalog versions newest first.

Query:

- `limit`: integer, 1 to 100, default 50.
- `status`: optional `active` or `inactive`.

When omitted, `status` returns both active and inactive versions. The Intents page uses `limit=1` without a status filter to show the latest history even if inactive. Test Runs use `status=active&limit=100`.

## GET /services/{service_id}/catalog-versions/{intent_catalog_version}

Returns the lifecycle metadata and immutable snapshot for one catalog version.

## GET /services/{service_id}/catalog-versions/{intent_catalog_version}/diff

Compares a target catalog version with another version.

Query:

- `compare_to`: optional baseline `intent_catalog_version`.

Response:

```json
{
  "service_id": "svc-it",
  "from_version": "cat-svc-it-old",
  "to_version": "cat-svc-it-new",
  "added_intents": ["it_password_reset"],
  "removed_intents": [],
  "changed_intents": [],
  "added_examples": [],
  "removed_examples": [],
  "changed_examples": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

The current diff payload returns IDs, not full object deltas.

## POST /services/{service_id}/catalog-versions/{intent_catalog_version}:deactivate

Deactivates a catalog version.

Rules:

- Returns conflict when any Release references the version.
- Marks version-scoped embeddings inactive and clears their vector values.
- Keeps encrypted/masked Example text payloads for restoration and later re-embedding.

## POST /services/{service_id}/catalog-versions/{intent_catalog_version}:load-to-draft

Copies the selected immutable version into the editable Intent Catalog.

Rules:

- Current editable Intents/Examples are replaced to match the selected snapshot.
- Restored Intents are draft-compatible editable rows.
- Restored Examples are unapproved editable rows.
- The historical catalog version row is not changed.

## Test Runs And Releases

CSV Test Runs store the selected catalog version, embedding `model_version`, and `vector_index_version`.

Release creation reuses a ready vector index for the requested catalog version and current embedding model. If a Test Run has model/vector metadata, release creation rejects mismatches so a release cannot point at embeddings that were not tested.
