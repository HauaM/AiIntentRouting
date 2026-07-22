# ADR: Test Run CSV Contract And Risk Pack

## Status

Accepted

## Context

The current Test Run CSV asks users to provide `case_type`, but users are primarily testing whether a query routes to the intended Catalog Intent. Service-specific out-of-business routes such as `off_topic_other_subject` can be valid Catalog Intents and should be tested like any other expected Intent. The current runtime checks service `off_topic_policy` before semantic scoring, so this decision also requires the runtime to let a confident registered Catalog Intent win before `Decision.off_topic` is returned. Risk behavior is different: it is a common guardrail that must still block before normal Intent routing and should not require every service team to register risk Intents.

## Decision

The Admin Console user-facing Test Run CSV will use `case_id,query,expected_intent,memo`. Each row is internally stored as `case_type=positive` and `expected_decision=confident`. The backend derives expected `route_key` from the selected Catalog version and compares both actual Intent and actual route key for the new four-column contract. Risk cases are added from a versioned common risk pack plus optional service-specific risk CSV and are internally stored as `case_type=risk`, `expected_decision=risk`.

Common or custom risk rows require `risk_policy.enabled=True`; a risk-disabled policy fails fast with a clear validation error.

The existing database columns `case_type`, `expected_decision`, and `expected_intent` remain unchanged. This change includes no database migration.

## Alternatives Considered

### Option 1: Keep `case_type` in user CSV

* Pros: No migration work; existing fixtures remain unchanged.
* Cons: Users confuse `case_type` with Intent IDs; service-specific off-topic Intents cannot be represented naturally.

### Option 2: Remove `case_type` everywhere

* Pros: Simple user mental model.
* Cons: Loses internal risk gate accounting and existing DB/result semantics; requires larger migration.

### Option 3: Hide `case_type` externally but keep it internally

* Pros: Simple user CSV, preserves gate accounting, supports risk guardrails, and avoids DB migration.
* Cons: Requires a compatibility layer and explicit risk-pack versioning.

## Consequences

Normal CSVs become easier to create. Test quality is preserved by deriving internal expectations, checking Catalog existence, checking route keys for the new contract, appending risk cases, and blocking releases without risk coverage. Existing legacy five-column fixtures remain supported during migration without adding route-key comparison to legacy rows.

## Implementation Notes

Normal Admin Console CSV import/export uses four columns. Backend parsing accepts four-column v2 CSVs and legacy five-column v1 CSVs. New v2 Test Runs include `common-risk-pack-v1` by default. Release validation checks actual Test Results for at least one `case_type=risk` row and requires all risk rows to pass. `content_sha256` remains the hash of the uploaded user CSV text; the common risk-pack version is tracked through risk case IDs and documentation, not by changing DB hash semantics.

Existing committed pilot CSVs and baseline files remain legacy-format artifacts unless baseline regeneration is explicitly performed. A `review_rate > 0.15` remains advisory and is not a blocking release criterion in this change.

## Verification

Run backend unit tests for CSV parsing/gate, routing precedence, frontend Test Runs contract tests, release-flow tests, and pilot fixture tests. Verify that `expected_intent=off_topic_other_subject` is accepted in the UI CSV and can produce `Decision.confident` even when service `off_topic_policy` would otherwise match the query.

## Rollback or Revisit Conditions

Revisit if services need query-only exploration tests, risk policy needs service-specific allow/deny categories, or route-key comparison produces false failures due to Catalog snapshot inconsistency.
