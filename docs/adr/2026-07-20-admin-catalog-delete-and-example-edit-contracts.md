# ADR: Admin Catalog Delete and Example Edit Contracts

## Status

Accepted

## Context

The Admin Console already supports creating and updating Intents, and creating
and approving Examples. Operators also need to correct or remove catalog data
from the Intents page. Approved Examples store their embedding in the
`intent_examples.embedding` column, so Example updates and deletes must keep the
stored embedding state consistent with the visible catalog state.

## Decision

Add Admin API contracts for deleting Intents, updating Examples, and deleting
Examples:

- `DELETE /admin/v1/services/{sid}/intents/{intent_id}`
- `PATCH /admin/v1/services/{sid}/examples/{example_id}`
- `DELETE /admin/v1/services/{sid}/examples/{example_id}`

Intent delete removes the Intent and all connected Examples. Example update
replaces encrypted raw text and masked text when new text is provided. If the
Example is already approved, update regenerates the embedding and replaces the
previous vector. Example delete removes the row, which removes the stored
embedding with it. All writes require existing service catalog access and write
sanitized audit events.

## Alternatives Considered

### Option 1: Hard delete rows and audit sanitized before state

Pros:

- Matches the current schema, where embeddings live on the Example row.
- Removes stale embeddings immediately.
- Avoids a migration for deletion flags.

Cons:

- Deleted catalog rows are recoverable only from audit metadata, not as active
  records.
- Active catalog versions remain historical snapshots and are not rewritten.

### Option 2: Soft delete Intents and Examples

Pros:

- Easier to restore mistakenly deleted rows.
- Preserves row-level metadata for later inspection.

Cons:

- Requires schema and query changes across catalog listing, release snapshots,
  embedding search, and tests.
- Stale embeddings could remain queryable unless every read path is updated.

### Option 3: Disable delete and only support deprecated status

Pros:

- Lowest immediate data-loss risk.
- Uses existing Intent status behavior.

Cons:

- Does not satisfy the operator need to remove mistaken Examples.
- Does not remove approved Example embeddings.

## Consequences

The Admin UI can now expose delete and edit controls for catalog correction.
Runtime behavior remains based on releases and catalog snapshots; deleting a
current catalog row does not mutate previously created catalog versions. Audit
logs become the source for investigating deleted catalog records.

## Implementation Notes

Use `ConfirmActionButton` for delete actions. Do not expose raw text from
existing Examples in the UI; the edit form should accept replacement raw text
only when the operator explicitly enters it. Keep normal browser Admin UI auth
on Umi `request` and session cookies.

## Verification

Validate with backend integration tests for Example update re-embedding,
Example delete, and Intent delete cascading to Examples. Validate frontend
service and page contract tests for the new service functions and controls.

## Rollback or Revisit Conditions

Revisit this decision if catalog restore becomes a product requirement, if
compliance requires retained deleted row metadata outside audit logs, or if
embedding storage moves from `intent_examples.embedding` into a separate vector
index/table.
