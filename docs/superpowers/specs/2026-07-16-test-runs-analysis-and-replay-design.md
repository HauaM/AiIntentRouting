# Test Runs Analysis And Replay Design

**Date:** 2026-07-16  
**Status:** Approved direction — implementation specification  
**Target:** Admin Console route `/test-runs` and its service-scoped Admin APIs

## Context

The Test Runs page can create a CSV validation run and render its result, but it
does not provide a usable history-first workflow. Operators must know a
`test_run_id`, failure analysis is compressed into table cells, and the page
does not support comparing or replaying an earlier run. This conflicts with
`TC-027` through `TC-030`, which define Test Runs as the release gate and require
an efficient failure-improvement-retest loop.

The approved direction is the full workflow redesign, including two backend
contract additions: a stable trace ID for every result row and owner-only access
to reconstruct a prior CSV dataset for editing and replay.

## Goals

- Make recent Test Runs the primary entry point instead of manual ID lookup.
- Make gate status and pass/review/risk rates comparable across runs.
- Make failed and review rows easy to isolate and inspect.
- Give every result row a stable, copyable evidence identifier.
- Let authorized owners reconstruct, edit, and rerun a prior CSV dataset.
- Record every raw dataset read and replay in the audit log.
- Keep normal result and history access available to existing catalog roles.

## Non-goals

- Store or return the original byte-for-byte uploaded CSV file.
- Add server pagination, polling, export downloads, or compound result filters.
- Allow `service_developer`, `service_operator`, or `auditor` to read raw test
  queries through the replay contract.
- Add an approval workflow for test dataset reads.
- Change release gate formulas or threshold preset semantics.
- Expose raw test queries in list, summary, result, or audit-log responses.

## Backend design

### Result trace IDs

Add a non-null, unique `trace_id` column to `test_results`. Generate an opaque
`trc-<uuid>` identifier when each CSV row is evaluated. Include it in
`TestRunResultResponse` and use it as the frontend table row key and evidence ID.

The identifier is a Test Run evidence trace; it does not claim that a runtime
request log exists. Existing rows receive deterministic migration values based
on their row UUID so the migration is reversible and does not require routing
re-execution.

### Raw dataset reconstruction endpoint

Add:

`GET /admin/v1/services/{service_id}/test-runs/{test_run_id}/replay-source`

Response:

```json
{
  "test_run_id": "tr-...",
  "source_filename": "test-cases.csv",
  "policy_version": "pv-...",
  "intent_catalog_version": "icv-...",
  "threshold_preset": "balanced",
  "csv_text": "case_id,query,expected_intent,case_type,memo\n..."
}
```

The server reconstructs `csv_text` with Python CSV serialization from ordered
`TestCase` rows. The result is semantically equivalent input, not the original
formatting, quoting, line endings, or row order. Cases are ordered by `case_id`
to make the response deterministic.

Authorization is limited to a global `system_admin` or `service_owner` for the
target Service. Service existence and Test Run ownership are checked before any
case data is returned. Other roles receive `403`; a missing or cross-Service run
returns the existing sanitized `404` response.

Every successful response writes an audit event:

- `event_type`: `test_run.replay_source_viewed`
- `target_type`: `test_run`
- `target_id`: the Test Run ID
- `service_id`: the selected Service
- `trace_id`: `null`
- `after_state`: metadata only: dataset version, case count, source filename

The audit record must not contain `csv_text`, queries, memo text, or reconstructed
rows.

### Replay execution

Replay uses the existing `POST /test-runs` contract after the authorized client
loads and optionally edits the reconstructed CSV. The create endpoint accepts an
optional `replay_source_test_run_id`. When supplied, the server verifies the same
owner-only permission, verifies the source run belongs to the Service, and adds
an audit event `test_run.replayed` after successful creation. The event records
only source and new Test Run IDs plus version metadata.

The existing create behavior without `replay_source_test_run_id` remains
available to `system_admin`, `service_owner`, and `service_developer`.

## Frontend design

### Page hierarchy

Use this order inside `AdminShell`:

1. Compact toolbar with `새 Test Run` as the sole primary action.
2. Recent Test Runs table.
3. Selected-run comparison and summary.
4. Selected-run result toolbar and result table.
5. Result detail drawer.

The Phase 2 CSV export notice moves from the top of the page to a disabled
action in the result toolbar so it no longer outranks the supported workflow.

### Recent runs

Load `listTestRuns(serviceId)` through ProTable `request`. Provide one compact
`Segmented` filter for `전체`, `통과`, and `차단`; reload when the Service or
filter changes. Columns are filename, created time, threshold preset, pass rate,
review rate, risk pass rate, gate status, and creator. Selecting a row loads its
summary and results.

Manual `test_run_id` input is removed. Empty state copy directs the user to
create the first Test Run.

### Create and replay form

The long Validation Bundle and CSV form remains an inline page section rather
than a modal or drawer. `새 Test Run` opens it and `취소` returns to history.
After successful creation, the history reloads and the new run becomes selected.

For users with replay-source permission, the selected-run actions include
`CSV 불러와 재실행`. It loads the replay-source response into the form, shows the
source Test Run ID, and preserves `replay_source_test_run_id` on submit. Users
without permission do not see this raw-source action. The server remains the
authorization source of truth.

### Comparison and results

Allow one comparison run to be selected from the loaded history. Show current
and comparison values for pass, review, and risk pass rates with explicit
percentage-point deltas. Do not imply statistical significance or compare row
contents.

The result toolbar uses a four-option `Segmented` control: `전체`, `실패`,
`검토`, `통과`. Filtering is local over the complete result array returned by
the existing endpoint and does not imply a server filter.

Keep result cells single-line. Use separate columns for expected decision,
expected intent, actual decision, actual intent, result, and reason. Result rows
use the shared semantic status component. Long masked queries and reasons use
ellipsis plus tooltip.

Clicking a row opens a 560px DetailDrawer containing copyable trace and case IDs,
masked query, expected/actual values, confidence, result, and the full reason.
Failed and review rows provide `Intent Catalog로 이동` and, when authorized,
`CSV 불러와 재실행` actions.

### Route and language

Add `/test-run` as a redirect to `/test-runs`. Standardize page, card, action,
empty-state, and notification copy in Korean while retaining technical field
names such as Test Run, CSV, ID, pass, and review where they improve precision.

## Component boundaries

- `pages/TestRuns/index.tsx`: session-aware data flow, selection, create/replay
  orchestration, and page composition.
- `pages/TestRuns/TestRunHistoryTable.tsx`: history request, filter, selection,
  and reload interface.
- `pages/TestRuns/TestRunResultsTable.tsx`: local result filtering, columns, and
  result detail drawer.
- `pages/TestRuns/TestRunComparison.tsx`: summary comparison and delta display.
- `pages/TestRuns/ValidationBundlePanel.tsx`: existing bundle selection and
  creation behavior.
- `services/adminServices.ts`: typed history, replay-source, result, and create
  requests through Umi `request` with credentials.
- Backend model/repository/API files: trace persistence, source reconstruction,
  authorization, and sanitized audit writes.

## Error handling

- History load failures use the existing request error handling and keep a
  reload affordance.
- If selected result loading fails, history remains usable and the result area
  shows a retry state.
- A replay-source `403` shows a short permission message and does not open the
  form.
- A stale or deleted source run produces a sanitized not-found message.
- Create failures preserve the edited CSV and selected bundle so users can fix
  and retry.
- Audit persistence participates in the same database transaction as the raw
  source read metadata or replay creation; no raw query content enters logs.

## Testing

- Migration test: existing Test Result rows receive unique non-null trace IDs.
- CSV runner test: new results contain stable-format trace IDs.
- API integration tests: result responses include trace IDs; system admins and
  Service owners can read replay source; developers and unrelated owners cannot;
  cross-Service IDs return sanitized not-found responses.
- Audit tests: source view and replay events contain metadata but no raw query,
  memo, or CSV text.
- Replay tests: reconstructed CSV parses successfully, edits can create a new
  run, and the source/new relationship appears only in sanitized audit metadata.
- Frontend service tests: replay-source URL, payload, encoding, and session-cookie
  request behavior.
- Frontend component tests: history-first hierarchy, gate filter, comparison
  delta, result filter, DetailDrawer fields, owner-only replay action, Korean
  copy, and `/test-run` redirect.
- Verification: focused tests, backend integration tests, frontend unit suite,
  TypeScript check, production build, prohibited-pattern search, and authenticated
  browser smoke when credentials are available.

## Acceptance criteria

- Operators can find and open a Test Run without typing an internal ID.
- Fail and review results can be isolated in one action.
- Every result row has a unique copyable trace ID and case ID.
- Summary rates can be compared against another run with clear deltas.
- Only `system_admin` and the target Service's `service_owner` can obtain raw
  reconstructed CSV content.
- Raw source reads and successful replay creations are audited without raw text.
- An authorized user can edit reconstructed CSV and create a new Test Run linked
  to its source in audit metadata.
- Unsupported export remains visibly unavailable without taking primary space.
- `/test-run` redirects to `/test-runs`.
- No prohibited frontend dependency, trusted browser header, fake pagination,
  or live polling is introduced.
