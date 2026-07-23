# Test Run Results UX Clarity API Follow-Ups

## Confirmed Frontend-Only Limits

The current Test Run result response includes `actual_route_key` but does not include `expected_route_key`. The frontend therefore cannot honestly show expected and actual route keys side by side for route-key mismatch rows.

The current row response includes `confidence` but does not include the applied threshold, margin, top candidates, or a decision reason. The frontend therefore cannot fully explain why a row became `clarify`, `fallback`, or `review`.

The current result rows do not include a first-class `case_source` field. The frontend must not present row source or provenance as confirmed, and must not infer row source or provenance from `case_id` prefixes.

The current result rows also lack display metadata for expected and actual intents. The frontend can show the returned identifiers, but cannot reliably present a user-facing display name, domain, or intent ID for both sides of a mismatch.

## Recommended API Additions

- Add `expected_route_key` to `TestRunResultResponse`.
- Add `case_source` with values such as `uploaded_csv`, `common_risk_pack`, or `custom_risk_csv` when those values are backend-confirmed.
- Add a row-level explanation object for threshold outcomes: `threshold_value`, `confidence`, `margin`, `top_candidates`, and `decision_reason`.
- Add display metadata for expected and actual intents: `display_name`, `domain`, and `intent_id`.

## Product Rule

Until these fields exist, the Admin UI must not claim more precision than the backend response supports.
