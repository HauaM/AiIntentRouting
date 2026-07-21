# Implementation Plan Review

Reviewed plan: `docs/superpowers/plans/2026-07-21-test-run-results-actionable-diagnostics-ux.md`
Reviewed at: 2026-07-21
Repo state: branch `main`, working tree contains unrelated Catalog-version diff changes (see `git status --short`).

Evidence for this review was gathered by reading:

- `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`
- `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- `frontend/intent-routing-console/src/types/api.d.ts`
- `frontend/intent-routing-console/src/components/StatusTag.tsx`
- `frontend/intent-routing-console/package.json`, `vitest.config.ts`, `tsconfig.json`
- `src/intent_routing/testing/csv_runner.py`, `src/intent_routing/testing/gate.py`
- `src/intent_routing/diagnostics/test_runs.py`
- `src/intent_routing/domain/enums.py`
- `AGENTS.md`

---

## 1. Review Summary

### Overall Assessment

**Major revision should be considered**

### Summary

The plan's direction matches the user requirement well: it targets Korean reason copy, importance-ordered sections, failure-pattern aggregation, and next actions, and it correctly concludes that no backend contract change is strictly required (the diagnostics API already returns `issues`, `result_counts`, `actual_decision_counts`, and the catalog stats). Task decomposition (pure helpers first, then panel, then table, then summary, then verification) is sound and each task is independently committable.

The most important risks are concentrated in three places:

1. **Reason-string fidelity.** The plan's Korean reason map is keyed on English strings produced by the backend, but at least one key is wrong and one is missing. `src/intent_routing/testing/csv_runner.py:417` emits `"requires human inspection"`, not `"requires human review"` as the plan's map and its own test assert. `csv_runner.py:416,426` also emit `"matched expected decision"` (a distinct string from `"matched expected decision and intent"`), which the plan's map does not contain. Under the plan as written, every `REVIEW` row and every intent-less `PASS` row would render `해석되지 않은 사유: <English>` — i.e. the exact outcome the user asked to eliminate, for two of the five possible reason values. The same class of gap exists for `formatDecisionLabel`, which omits two of the six `Decision` enum values.

2. **Existing contract tests conflict with the planned refactor.** `testRunDiagnosticsPanelContract.test.ts` asserts, against the raw source of `TestRunDiagnosticsPanel.tsx`, that issue-code strings, `label="결과 집계"`, `label="실제 결정 집계"`, and `'백엔드 진단에서 주요 이슈를 찾지 못했습니다.'` are present. The plan moves the issue-code map into a new file and replaces the panel body without those Descriptions or that sentence, and does not list updating those assertions. Tasks 3 and 6 would fail on pre-existing tests, not just on the new ones.

3. **The wireframe's section 6 placement is not achievable with the planned component ownership.** `TestRunDiagnosticsPanel` is rendered in `index.tsx:444–447`, i.e. between the summary `<section>` and the `<ProTable>`. The plan keeps `Catalog / Vector 상태` inside that panel while requiring it to appear *below* 상세 결과. The plan's own Task 3 note acknowledges the panel owns "sections 2, 3, 4, and 6", but does not resolve how a single block rendered above the table produces an item at position 6.

Additionally, every verification command in the plan is likely non-executable as written: `package.json` defines `test:unit` (not `test`), and `--runInBand` is a Jest flag, not a Vitest one.

Priorities for the Coding Agent to re-check, in order: F-1 (reason strings), F-2 (existing contract tests), F-3 (section-6 placement), F-4 (verification commands), then the rest.

---

## 2. Validated Parts of the Plan

### V-1. No backend contract change is needed for the planned insights

* Plan section: Self-Review, "Scope check"; Task 2 Interfaces
* Assessment: Accurate.
* Evidence: `src/types/api.d.ts:556–562` defines `TestRunDiagnostics` with `primary_issue`, `issues`, `catalog_version`, `result_counts`, `actual_decision_counts`. `api.d.ts:520–532` defines `TestRunResult` with `expected_decision`, `expected_intent`, `actual_decision`, `actual_intent`, `actual_route_key`, `result`, `reason`. `api.d.ts:496–509` defines `TestRunSummary` with `block_reasons` and `recommendations`. All fields the plan consumes are already typed and already served.
* Why this appears appropriate: Keeping the change frontend-only limits blast radius and avoids a deploy-ordering dependency between API and console.

### V-2. `formatBlockReason` / `formatRecommendation` regexes match the real backend strings

* Plan section: Task 1 Step 3
* Assessment: Correct as written.
* Evidence: `src/intent_routing/testing/gate.py:34` appends exactly `"pass rate below 70%"`; `gate.py:36` appends `"risk case failed"`; `gate.py:40` appends `"review rate above 15%"`. The plan's `/^pass rate below ([0-9]+)%$/` and `/^review rate above ([0-9]+)%$/` patterns and the `'risk case failed'` equality check all match these three literals exactly, and these are the only three strings `evaluate_gate` can produce.
* Why this appears appropriate: Parameterizing the percentage rather than hardcoding "70%" survives a future threshold change in `gate.py` without a frontend edit.

### V-3. Issue codes used by the copy map are the complete backend set

* Plan section: Task 1 `issueTitleCopy`
* Assessment: Complete — all 12 codes covered, no extras.
* Evidence: `src/intent_routing/diagnostics/test_runs.py:14–27` (`ISSUE_CODE_PRIORITY`) enumerates exactly the 12 codes the plan maps. `test_runs.py:168` sorts by `ISSUE_CODE_PRIORITY[issue.code]`, which would `KeyError` on any unlisted code, so this dict is authoritative.
* Why this appears appropriate: The map is exhaustive against the current backend, and the `해석되지 않은 진단 코드: {code}` fallback degrades safely if a code is added later.

### V-4. Pure-function helpers are compatible with the existing test environment

* Plan section: Tasks 1–2 (new `.test.ts` files)
* Assessment: Compatible.
* Evidence: `vitest.config.ts` sets `environment: 'node'` and `globals: true`; `tsconfig.json` includes `vitest/globals`. `api.d.ts:1` declares a global `namespace API`, so `API.TestRunResult` resolves in test files without an import. Neither planned helper imports from the `@/` alias — which matters because `vitest.config.ts` defines no alias resolution, so a `@/`-importing module under test would fail to resolve.
* Why this appears appropriate: Keeping the new helpers dependency-free is what makes them unit-testable in this `node`-environment setup, where no component rendering is possible.

### V-5. Masking constraint is respected

* Plan section: Global Constraints; Task 4
* Assessment: Consistent with current behavior.
* Evidence: `index.tsx:204–208` renders only `query_masked`; the backend masks at `csv_runner.py:394` (`mask_pii(test_case.query)`) and never returns raw query text in `TestRunResult` (`api.d.ts:520–532`). The plan does not add any raw-query surface.
* Why this appears appropriate: No new PII exposure path is introduced. Note also that `title={row.reason}` (Task 4 Step 5) exposes only the backend's fixed English reason enum, not user data — see F-9 for a separate concern about that attribute.

### V-6. Desktop-only scope is respected

* Plan section: Global Constraints; Task 6 Step 5
* Assessment: Consistent with `AGENTS.md`.
* Evidence: `AGENTS.md` "Admin Console Viewport Scope" forbids mobile-specific UX and card-list replacements for tables, while requiring narrow-desktop resilience. The plan keeps the detailed results in a `ProTable`, states FHD desktop verification, and includes "Table columns remain readable in a narrowed desktop browser window" as acceptance.
* Why this appears appropriate: It follows the repository-specific instruction rather than a generic responsive-design default.

---

## 3. Review Findings

### F-1. The Korean reason map does not match the backend's actual reason strings

* Severity: **Blocker**
* Category: correctness / requirement coverage
* Plan section: Task 1 Step 1 test, Task 1 Step 3 `resultReasonCopy`
* Evidence type: Confirmed fact
* Current plan: `resultReasonCopy` maps four keys, including `'requires human review'`, and the Step 1 test asserts `formatResultReason('requires human review') === '사람의 검토가 필요한 케이스입니다.'`.
* Review finding: The backend produces five distinct reason strings, and the plan's map is wrong on one and missing another.
  - `csv_runner.py:417` returns `("REVIEW", "requires human inspection")` — **inspection**, not **review**. The plan's key never matches.
  - `csv_runner.py:416` and `csv_runner.py:426` return `("PASS", "matched expected decision")` — a distinct literal from `"matched expected decision and intent"` (`csv_runner.py:427`), emitted when `expected_intent is None` or when a clarify case matched. The plan's map has no entry for it.
  - The two the plan gets right: `csv_runner.py:430` `"actual decision did not match expected decision"`, `csv_runner.py:431` `"actual intent did not match expected intent"`.
* Evidence: `src/intent_routing/testing/csv_runner.py:409–431` (`_compare_result`) is the sole producer of the `reason` field, written at `csv_runner.py:405`. Cross-check: `tests/unit/test_ops_reports.py:168,186,273` also use the literal `"requires human inspection"`.
* Potential impact: Every `REVIEW` row and every intent-less `PASS` row renders `해석되지 않은 사유: requires human inspection` / `해석되지 않은 사유: matched expected decision` — English text in the visible column, which is precisely what the user asked to remove. Since `review_rate_above_guidance` exists as a diagnostic, REVIEW rows are an expected and common case, not an edge case. The plan's own unit test would also encode the wrong contract, so the failure is invisible to the test suite.
* What the Coding Agent should verify: The exhaustive set of `reason` literals `_compare_result` can return, and whether any other code path writes `reason` into a test-run result row.
* How to verify:
  ```bash
  grep -n "return \"PASS\"\|return \"FAIL\"\|return \"REVIEW\"" src/intent_routing/testing/csv_runner.py
  grep -rn '"reason"' src/intent_routing/
  ```
* Decision criteria: If `_compare_result` is the only producer and returns exactly the five literals above, the map must be keyed on those five exact strings and the Step 1 test corrected. If another producer exists (e.g. a re-scoring or import path), the map needs those literals too. Consider adding a test that asserts no reason literal in `csv_runner.py` falls through to the `해석되지 않은 사유` branch, so future backend reason changes fail loudly in CI rather than silently leaking English into the UI.
* Possible response:
  * Modify the current plan (correct the map keys and the Step 1 test)
  * Add an additional step (a fallthrough-guard test keyed on the backend source)

### F-2. Task 3's panel rewrite breaks four existing contract assertions the plan does not update

* Severity: **Blocker**
* Category: regression / plan completeness
* Plan section: Task 3 Step 1 and Step 3; Task 6 Step 2
* Evidence type: Confirmed fact
* Current plan: Task 3 adds two new `it(...)` blocks to `testRunDiagnosticsPanelContract.test.ts` and replaces the panel body, but lists no removal or modification of existing assertions.
* Review finding: The existing contract test asserts on the raw text of `TestRunDiagnosticsPanel.tsx`, and the planned refactor removes four things it requires:
  1. `testRunDiagnosticsPanelContract.test.ts:22–29` requires the source to contain `'catalog_version_not_active'`, `'catalog_version_not_reproducible'`, `'fallback_failures_dominant'`, `'intent_mismatch_exists'`. The plan moves `issueCopy` out of the panel into `testRunResultCopy.ts` (Task 1), so these literals leave the panel file.
  2. `testRunDiagnosticsPanelContract.test.ts:53–54` requires `label="결과 집계"` and `label="실제 결정 집계"`. The plan's Step 3 replacement JSX contains no such `Descriptions` block; the existing one is at `TestRunDiagnosticsPanel.tsx:134–143`.
  3. `testRunDiagnosticsPanelContract.test.ts:56` requires `'백엔드 진단에서 주요 이슈를 찾지 못했습니다.'`. The plan's new `Alert` description is built from `insights.impactBullets` and never emits that sentence (currently at `TestRunDiagnosticsPanel.tsx:102`).
  4. `testRunDiagnosticsPanelContract.test.ts:55` requires `"?? '없음'"` — still satisfied only if the Catalog `Descriptions` items are carried over verbatim, which the plan represents as a `{/* keep existing Catalog descriptions here */}` comment rather than explicit content.
* Evidence: File contents as cited above.
* Potential impact: Task 3 Step 5 ("Expected: PASS") and Task 6 Step 1/2 fail on pre-existing tests. Worse, an implementer under time pressure may delete the failing assertions without deciding whether the underlying behavior (result/decision count visibility, the no-issue empty-state sentence) should actually be dropped — a silent feature regression disguised as a test fix.
* What the Coding Agent should verify: Which of these four behaviors are intentionally being removed vs. relocated, and whether `결과 집계` / `실제 결정 집계` should survive in some form.
* How to verify:
  ```bash
  cd frontend/intent-routing-console
  npm run test:unit -- testRunDiagnosticsPanelContract
  ```
  Run this *before* implementing to capture the green baseline, then after Task 3.
* Decision criteria: Note that the current `결과 집계` rendering is `JSON.stringify(diagnostics.result_counts)` (`TestRunDiagnosticsPanel.tsx:136`) — raw JSON, arguably a legitimate target for the user's readability requirement. If the intent is to replace it with `insights.impactBullets` prose, the plan should say so explicitly and update the assertion to require the new Korean sentence instead of merely deleting the old one. If the counts should remain browsable, keep the block and move it near 상세 결과.
* Possible response:
  * Modify the current plan (add explicit steps to update the four existing assertions, with a stated rationale per assertion)

### F-3. `Catalog / Vector 상태` cannot reach wireframe position 6 while it lives inside the diagnostics panel

* Severity: **Blocker**
* Category: requirement coverage / architecture
* Plan section: Task 3 Interfaces + Note; Wireframe Acceptance Order; Task 6 Step 5
* Evidence type: Confirmed fact
* Current plan: The panel owns sections 2, 3, 4, and 6; the wireframe requires order 요약 → 문제 → 패턴 → 조치 → 상세 결과 → Catalog/Vector.
* Review finding: `index.tsx:368–464` renders, inside one vertical `Space`: the summary `<section>` (`:370–443`), then `<TestRunDiagnosticsPanel>` (`:444–447`), then `<ProTable>` (`:448–463`). Everything the panel renders is therefore between 요약 and 상세 결과. A single component in that slot cannot emit a child that lands below the `ProTable`. The plan's own note names the contradiction ("panel owns sections 2, 3, 4, and 6") without resolving it.
* Evidence: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx:368–464`.
* Potential impact: The manual acceptance in Task 6 Step 5 fails at item 6, after all five implementation tasks are committed. Meanwhile the *source-order* contract test added in Task 3 Step 1 (`catalogIndex > nextActionIndex` within the panel file) passes, so the automated suite reports green on a requirement that is not met — the worst combination.
* What the Coding Agent should verify: Whether the desired end state is (a) splitting the panel into two rendered slots, (b) moving the Catalog block out of the panel into `index.tsx` below the `ProTable`, or (c) revising the wireframe so Catalog/Vector stays above the table.
* How to verify: Read `index.tsx:368–464` and trace the JSX child order in the `currentStep === 2` branch; confirm no CSS `order` or flex reordering is applied to `.ds-page-card` children in `src/global.less`.
* Decision criteria: Option (b) is the smallest change and keeps a single component per screen region, but splits diagnostics data-fetching from one of its consumers (the Catalog block needs `diagnostics.catalog_version`, which the panel fetches). Option (a) — e.g. the panel accepting a `section` prop, or exporting a second `TestRunCatalogStatusPanel` that receives the already-fetched diagnostics — avoids a duplicate `fetchTestRunDiagnostics` call but adds a prop-drilling or lifted-state concern. Prefer lifting the diagnostics fetch into `index.tsx` if and only if two rendered slots are confirmed necessary; prefer (c) if the user's intent is "supporting metadata last *within the diagnostics block*" rather than "last on the page." This is worth confirming with the user, since it is a requirement interpretation, not a technical choice.
* Possible response:
  * Perform further investigation before deciding
  * Modify the current plan

### F-4. Every verification command in the plan is likely non-executable as written

* Severity: **Major**
* Category: verification / plan executability
* Plan section: Tasks 1–6, all "Run:" blocks
* Evidence type: Confirmed fact (npm script), Needs verification (`rg`)
* Current plan: `npm test -- <file> --runInBand` in Tasks 1–5; `npm test -- --runInBand` and `npm run typecheck` in Task 6; `rg -n "..."` in Task 6 Steps 3–4.
* Review finding: Three separate problems.
  1. `frontend/intent-routing-console/package.json` `scripts` contains `dev`, `dev:local`, `build`, `typecheck`, `test:unit` — there is **no** `test` script. `npm test` will fail with "Missing script: test".
  2. `--runInBand` is a Jest flag. The runner is Vitest 0.34.6 (`devDependencies`), invoked as `vitest run` via `test:unit`. Vitest does not accept `--runInBand`; the serial equivalents are `--no-threads` (v0.34) or `--pool=forks --poolOptions.forks.singleFork`. There is also no stated reason serial execution is needed here.
  3. `rg` (ripgrep) was not resolvable when this review's tooling attempted it (the plan-heading extraction supplied to this review failed with `[Errno 2] No such file or directory: 'rg'`). It may still resolve in an interactive shell via a wrapper function.
  Note also `package.json` declares `"packageManager": "pnpm@11.9.0"`, so `npm` may not be the intended invocation at all.
* Evidence: `frontend/intent-routing-console/package.json:7–14`; `vitest.config.ts`; the `rg` failure recorded in this review's input.
* Potential impact: The TDD loop (`Step 2: Run the test to verify it fails`) fails for the wrong reason — a missing npm script rather than a missing module — which defeats the point of the red step and can mislead an agent into believing the red state is confirmed. Task 6's guardrail searches silently do not run.
* What the Coding Agent should verify: The correct runner invocation and file-filter syntax, and whether `rg` or `grep` is the repo's convention.
* How to verify:
  ```bash
  cd frontend/intent-routing-console
  cat package.json
  npm run test:unit -- testRunResultCopy      # confirm the filter selects the file
  npm run typecheck
  command -v rg
  grep -rn "npm run test:unit\|pnpm test" ../../docs/ 2>/dev/null | head
  ```
* Decision criteria: Use whatever `package.json` actually defines; drop `--runInBand` unless a concrete flakiness problem is observed. If `rg` is unavailable, `grep -rn -E` with the same patterns is equivalent for these searches. Check other plans under `docs/superpowers/plans/` for the established command convention before inventing one.
* Possible response:
  * Modify the current plan (replace all command blocks)

### F-5. `formatDecisionLabel` omits two of the six `Decision` enum values

* Severity: **Major**
* Category: correctness / requirement coverage
* Plan section: Task 1 `decisionCopy`
* Evidence type: Confirmed fact
* Current plan: Maps `confident`, `clarify`, `fallback`, `risk`; falls back to the raw value otherwise.
* Review finding: `src/intent_routing/domain/enums.py:4–10` defines `Decision` with six members: `confident`, `clarify`, `fallback`, `off_topic`, `risk`, `unauthorized`. `actual_decision` is written from `decision.decision.value` (`csv_runner.py:398`), so `off_topic` and `unauthorized` are reachable values. Both would render as raw English in the 기대 결과 / 실제 결과 columns.
* Evidence: `src/intent_routing/domain/enums.py:4–10`; `src/intent_routing/testing/csv_runner.py:398`. Supporting signal: `StatusTag.tsx` already lists `off_topic` in its `AdminStatus` union, indicating the console elsewhere treats it as a real, displayable state.
* Potential impact: Partial fulfillment of the Korean-copy requirement, appearing only on runs that produce off-topic or unauthorized decisions — likely to survive review and surface later in production.
* What the Coding Agent should verify: Whether `expected_decision` (a CSV-supplied value) can also carry values outside the enum, which would affect whether the raw-value fallback is acceptable for the expected column.
* How to verify:
  ```bash
  grep -n "class Decision" -A 10 src/intent_routing/domain/enums.py
  grep -rn "expected_decision" src/intent_routing/testing/csv_runner.py
  ```
* Decision criteria: Add the two missing entries regardless. Separately decide whether the unknown-value fallback should stay as the raw value (consistent with the existing `resultLabel[normalizedResult] ?? row.result` pattern at `index.tsx:254`) or use the `해석되지 않은 …` prefix used elsewhere in the plan — the plan is currently inconsistent between these two fallback styles across `formatDecisionLabel` and `formatResultReason`.
* Possible response:
  * Modify the current plan

### F-6. Pattern `StatusTag status` values are unmapped and render as neutral grey

* Severity: **Minor**
* Category: consistency / visual semantics
* Plan section: Task 3 Step 3, `<StatusTag status={pattern.kind} label={...} />`
* Evidence type: Confirmed fact
* Current plan: Uses `pattern.kind` (`'intent_mismatch' | 'decision_mismatch' | 'fallback'`) as the `status`.
* Review finding: `StatusTag.tsx` resolves tone via `STATUS_TONE[normalized] ?? STATUS_TONE.none`. `fallback` is mapped (grey `#EEF0F3`); `intent_mismatch` and `decision_mismatch` are absent and fall back to `none` — also grey `#EEF0F3`. All three pattern kinds therefore render visually identical, and the tag conveys only the count, contradicting the intent of using `StatusTag` "for semantic states" stated in the plan's own Global Constraints.
* Evidence: `frontend/intent-routing-console/src/components/StatusTag.tsx` (`AdminStatus` union and `STATUS_TONE` map).
* Potential impact: Cosmetic only; no functional failure. The pattern kind is still inferable from the `expected → actual` text.
* What the Coding Agent should verify: Whether extending `AdminStatus`/`STATUS_TONE` is in scope, given the plan's "keep changes scoped to Test Runs UI" constraint.
* How to verify: Read `StatusTag.tsx`; check whether other pages pass ad-hoc status strings that also fall through to `none`.
* Decision criteria: If the failure-pattern severity is meant to be visually ranked, map the kinds to existing tones (e.g. `warning` for mismatches, `fallback` for fallback) rather than adding new `STATUS_TONE` entries — this stays inside Test Runs and reuses the established palette. If the tag is purely a count badge, consider a plain `Typography.Text` and drop the semantic-tag implication.
* Possible response:
  * Modify the current plan
  * Keep the current plan (if grey-for-all is acceptable)

### F-7. `topPatterns` slices to 5 before the primary-problem decision is made

* Severity: **Minor**
* Category: correctness
* Plan section: Task 2 Step 3, `buildTestRunInsights`
* Evidence type: Reasoned inference (from the plan's own code; no runtime evidence)
* Current plan: `const patterns = topPatterns([...patternMap.values()]);` slices to the top 5, and `primaryProblem`, `nextActions`, and the fallback/mismatch detection all read from that sliced array.
* Review finding: With more than five distinct `expected→actual` pairs, a genuine `intent_mismatch` pattern with a lower count than five other patterns is dropped before `mismatchPattern` is computed, so `primaryProblem` can report "분류 실패로 떨어진 케이스가 먼저 보입니다" even when intent mismatches exist. The backend takes the opposite view: `diagnostics/test_runs.py:134` raises `intent_mismatch_exists` on **any** mismatch (`if intent_mismatch_count:`), regardless of rank. The panel's headline and the backend's `primary_issue` could then disagree on the same screen.
* Evidence: Plan Task 2 Step 3 code; `src/intent_routing/diagnostics/test_runs.py:41–45, 134–141`; priority ordering at `test_runs.py:22–26` places `fallback_failures_dominant` (20) above `intent_mismatch_exists` (21).
* Potential impact: Misleading "가장 먼저 확인할 문제" headline on large, diverse test sets. Note the plan's Alert already prefers `primaryIssue` (backend) over `insights.primaryProblem` when a `primaryIssue` exists, so this only surfaces when `diagnostics` is absent or has no issues — narrowing the impact considerably.
* What the Coding Agent should verify: Whether `primaryProblem` is ever actually rendered given the `primaryIssue ? … : insights.primaryProblem` precedence in Task 3 Step 3.
* How to verify: Add a unit case to `testRunResultInsights.test.ts` with six or more distinct mismatch pairs where the sole intent-mismatch pair has count 1, and assert the expected `primaryProblem`.
* Decision criteria: If `insights.primaryProblem` is genuinely a rarely-hit fallback, computing detection over the unsliced map (and slicing only for display) is a one-line fix worth taking. If the headline is meant to always mirror the backend's `primary_issue`, consider deriving `primaryProblem` from `diagnostics.issues` ordering instead of re-deriving it client-side — see O-1.
* Possible response:
  * Modify the current plan
  * Keep the current plan

### F-8. Fallback classification shadows the intent-mismatch reason

* Severity: **Minor**
* Category: correctness
* Plan section: Task 2 Step 3, kind resolution
* Evidence type: Reasoned inference
* Current plan:
  ```ts
  if (row.actual_decision === 'fallback') kind = 'fallback';
  else if (row.reason === 'actual intent did not match expected intent') kind = 'intent_mismatch';
  ```
* Review finding: The `fallback` check runs first, so a row is classified as `fallback` regardless of its reason. Per `csv_runner.py:429–431`, a row with `actual_decision === 'fallback'` and a *matching* expected decision of `fallback` but a differing intent yields reason `"actual intent did not match expected intent"` — that row is counted as a fallback pattern, not an intent mismatch. Whether this ordering is intended is not stated in the plan.
* Evidence: `src/intent_routing/testing/csv_runner.py:419–431`; plan Task 2 Step 3.
* Potential impact: Pattern counts skew toward `fallback` for catalogs that legitimately expect fallback decisions; the suggested next action ("… 관련 표현을 Catalog 예시에 추가하세요") would be the wrong advice for such rows.
* What the Coding Agent should verify: How common `expected_decision === 'fallback'` is in real test CSVs, and whether the reason should take precedence over the decision.
* How to verify: Inspect the CSV template at `index.tsx:51–55` and any fixture CSVs under `tests/`; add a unit case with `expected_decision: 'fallback'`, `expected_intent` set, `actual_decision: 'fallback'`, and the intent-mismatch reason, then assert the expected `kind`.
* Decision criteria: If test datasets rarely expect `fallback`, the current ordering is harmless and simpler — keep it, but add a comment noting the precedence is deliberate. If expected-fallback cases are common, key the classification on `reason` first and use `actual_decision === 'fallback'` only to disambiguate decision mismatches.
* Possible response:
  * Keep the current plan
  * Modify the current plan

### F-9. Task 4's negative assertion is malformed and will not test what it claims

* Severity: **Minor**
* Category: test quality
* Plan section: Task 4 Step 1
* Evidence type: Confirmed fact
* Current plan:
  ```ts
  expect(source).not.toContain('dataIndex: \\'reason\\',\\n      search: false,\\n      ellipsis: true');
  ```
* Review finding: As written in a `.ts` file, `\\'` is a literal backslash followed by an end-of-string quote — this is a syntax error, and even if repaired to `\'`, the `\\n` sequences are literal backslash-`n` pairs rather than newlines, so the string can never match the source. The assertion would vacuously pass. Separately, the intent is questionable: the plan's Step 5 replacement *retains* `dataIndex: 'reason'`, `search: false`, and `ellipsis: true` — it only adds a `render`. So the property this assertion tries to enforce is not the property the implementation produces.
  Also worth checking in the same test: `expect(source).toContain('title={row.reason}')` places the raw English reason in a native `title` attribute rather than an Ant Design `Tooltip`. This satisfies the plan's "tooltip/title text" constraint literally, but note that `ellipsis: true` on a ProTable column already installs its own tooltip behavior — the two may interact.
* Evidence: Plan Task 4 Steps 1 and 5; `index.tsx:259–264` for the current column definition.
* Potential impact: A test that always passes provides false confidence. Low blast radius.
* What the Coding Agent should verify: Whether a positive assertion (the presence of `render:` with `formatResultReason` in the reason column) expresses the intent more directly than a fragile whitespace-sensitive negative assertion.
* How to verify: Write the assertion, then temporarily revert the source change and confirm the test actually goes red.
* Decision criteria: Prefer positive assertions over multi-line negative source matches throughout — note that the existing suite already leans this way (`testRunsPageContract.test.ts` uses `not.toContain` only for short, single-line literals). Every new `not.toContain` should be proven to go red against the pre-change source.
* Possible response:
  * Modify the current plan
  * Remove the planned step

### F-10. Two issue-copy rewrites lose accuracy relative to the backend's trigger conditions

* Severity: **Minor**
* Category: copy accuracy
* Plan section: Task 1 `issueTitleCopy`
* Evidence type: Confirmed fact
* Current plan: Changes `intent_mismatch_exists` from the current `'Decision은 맞았지만 Intent가 다른 실패가 있습니다.'` to `'기대 Intent와 실제 Intent가 다른 실패가 있습니다.'`, and `fallback_failures_dominant` from `'실패한 케이스 중 fallback 결과가 많습니다.'` to `'분류 실패로 떨어진 케이스가 많습니다.'`.
* Review finding: Both rewrites drop information the backend condition actually encodes.
  - `intent_mismatch_exists` fires on reason `"actual intent did not match expected intent"` (`test_runs.py:41–45`), which `_compare_result` returns only when `decision_matches` is true (`csv_runner.py:429–431`). The **existing** wording ("Decision은 맞았지만") captures that precondition; the plan's replacement does not, and an operator reading it may look for decision problems that cannot be present.
  - `fallback_failures_dominant` fires when `fallback_fail_count / len(failed_rows) >= 0.5` (`test_runs.py:123`) — a *ratio among failures*, not an absolute count. "케이스가 많습니다" reads as an absolute count and would be misleading on a run with 2 failures, both fallback.
* Evidence: `TestRunDiagnosticsPanel.tsx:20–21` (current copy); `src/intent_routing/diagnostics/test_runs.py:38–45, 123–141`; `src/intent_routing/testing/csv_runner.py:419–431`.
* Potential impact: Slightly misleading diagnosis text. This cuts against the user's stated goal of making results easier to understand and act on.
* What the Coding Agent should verify: Whether the rewrite was intentional (plainer language) or incidental (retyping from memory during the file move).
* How to verify: Diff the plan's `issueTitleCopy` against `TestRunDiagnosticsPanel.tsx:11–24` entry by entry; for each changed string, re-read the corresponding trigger in `diagnostics/test_runs.py`.
* Decision criteria: The existing strings already passed a Korean-copy review (they are asserted by `testRunDiagnosticsPanelContract.test.ts:22–29` and are already Korean). Prefer carrying them over verbatim unless a specific readability problem is identified; where a rewrite is kept, confirm it still matches the trigger condition. `risk_case_failed` is worth the same check — the plan's "위험 질문 차단 테스트" implies blocking semantics, while `test_runs.py:115` fires on `summary.risk_pass_rate < 1.0`, i.e. any risk-typed case not passing.
* Possible response:
  * Keep the current plan (retain existing strings)
  * Modify the current plan

### F-11. Insights are computed from a `results` array that is transiently empty

* Severity: **Minor**
* Category: UX / lifecycle
* Plan section: Task 3 Step 4 (`results={results}`)
* Evidence type: Confirmed fact (state flow), Reasoned inference (visible effect)
* Current plan: Pass `results` from `index.tsx` into the panel; the panel computes `buildTestRunInsights(results ?? [], diagnostics)`.
* Review finding: There are windows where `summary` is set but `results` is `[]`:
  - `index.tsx:150–154`: `setSummary(created)` and `setCurrentStep(2)` happen *before* `await fetchTestRunResults`, so the results step renders with `results === []`.
  - `index.tsx:168–172`: `handleHistoryRunSelect` sets `setSummary(testRun); setResults([]);` while still on step 0.
  - `index.tsx:159`: if the results fetch fails after a successful create, `results` stays `[]` permanently while `summary` and the diagnostics panel remain populated — a state the existing suite deliberately preserves (`testRunsPageContract.test.ts:137–143`).
  Because the panel keys its fetch on `testRunId` only, `diagnostics` may arrive while `results` is still empty, producing `'실패 케이스가 없습니다.'` and empty pattern/action cards alongside a real blocker diagnosis.
* Evidence: `index.tsx:150–166, 168–172`; plan Task 3 Step 3 `impactBullets`.
* Potential impact: A brief flash in the normal path; a persistently contradictory screen in the results-fetch-failure path ("차단 사유 있음" + "실패 케이스가 없습니다").
* What the Coding Agent should verify: Whether the panel can distinguish "results not loaded yet / failed to load" from "results loaded and contain no failures".
* How to verify: Read `index.tsx:126–166`; simulate by making `fetchTestRunResults` reject in the browser devtools network panel and observing the results step.
* Decision criteria: If the distinction matters, pass `results?: API.TestRunResult[] | undefined` (undefined = not loaded) rather than defaulting to `[]`, and render a distinct state; note `diagnostics.result_counts` is authoritative for counts regardless of whether rows loaded, so the impact bullets could be sourced from it alone. If the flash is judged acceptable, document that decision in the plan so it is not re-litigated during review.
* Possible response:
  * Modify the current plan
  * Keep the current plan

---

## 4. Potentially Missing Work

### M-1. Regression check for `off_topic` / `unauthorized` / `REVIEW` rows end to end

* Related requirement: "결과 사유는 영어가 아니라 한글로 표시한다"
* Why it may be needed: F-1 and F-5 show the plan's maps are incomplete for exactly the values that are least likely to appear in a hand-written happy-path test fixture. Without a test that enumerates the backend's full value set, the gap reappears whenever the backend adds a decision or reason.
* Evidence: `src/intent_routing/domain/enums.py:4–10` (6 decisions); `src/intent_routing/testing/csv_runner.py:409–431` (5 reasons).
* What should be checked: Whether a test can assert that no backend-producible `reason` or `decision` value falls through to an untranslated branch.
* Apply when: The Coding Agent agrees the maps must be exhaustive against the backend rather than best-effort.
* Do not apply when: The team accepts graceful English fallback for rare values and prefers not to couple a frontend test to Python source.
* Suggested verification: A `testRunResultCopy.test.ts` case iterating a hardcoded list of the five reasons and six decisions, asserting none of the returned strings contains `해석되지 않은` and that each result matches `/[가-힣]/`. Optionally pair with a Python-side test asserting `_compare_result` returns only those five literals, so the two sides fail together if they drift.

### M-2. Explicit decision on what happens to `결과 집계` / `실제 결정 집계`

* Related requirement: "화면은 중요도 기준으로 위에서 아래로 구성"
* Why it may be needed: The plan's Task 3 replacement JSX silently omits the `Descriptions` block currently at `TestRunDiagnosticsPanel.tsx:134–143`, and the wireframe has no slot for it. This is a user-visible removal that the plan never states as a decision.
* Evidence: `TestRunDiagnosticsPanel.tsx:134–143`; `testRunDiagnosticsPanelContract.test.ts:53–54`; the plan's 6-section wireframe.
* What should be checked: Whether operators use these aggregate counts, and whether `insights.impactBullets` fully replaces them (it reports FAIL/REVIEW/PASS but not the `actual_decision_counts` breakdown).
* Apply when: The counts carry information not otherwise available on the screen — `actual_decision_counts` in particular has no replacement in the planned wireframe.
* Do not apply when: The `JSON.stringify` presentation is judged to be exactly the kind of unreadable output the user asked to remove, and the aggregate is deemed redundant with the 실패 패턴 요약 section.
* Suggested verification: Compare the fields in `insights.impactBullets` against `diagnostics.result_counts` and `diagnostics.actual_decision_counts` and confirm nothing operators rely on disappears without replacement.

### M-3. Behavior when `diagnostics` fails to load but `results` are present

* Related requirement: Actionable result review
* Why it may be needed: The panel returns early on `!testRunId` and renders an error `Alert` when the diagnostics fetch rejects (`TestRunDiagnosticsPanel.tsx:145–146`). In that branch, none of the new sections (패턴 요약, 다음 조치) render at all — even though they are derivable from `results` alone, which `buildTestRunInsights` explicitly supports via its optional `diagnostics` parameter.
* Evidence: `TestRunDiagnosticsPanel.tsx:89, 145–149`; plan Task 2 signature `buildTestRunInsights(results, diagnostics?)`.
* What should be checked: Whether the pattern/action sections should render from `results` when diagnostics are unavailable.
* Apply when: Diagnostics failures are plausible in operation (a separate endpoint from the results fetch, so an independent failure mode) and degraded-but-useful is preferred to nothing.
* Do not apply when: The team prefers a single clear error state over partially-populated diagnostics that might be mistaken for complete.
* Suggested verification: Force `fetchTestRunDiagnostics` to reject; confirm the resulting screen matches the intended degraded design.

### M-4. Whether the plan file itself should be committed

* Related requirement: Repository hygiene
* Why it may be needed: `docs/superpowers/plans/2026-07-21-test-run-results-actionable-diagnostics-ux.md` is untracked (`??` in `git status --short`), and none of the plan's six `git add` commands include it. Every other plan in `docs/superpowers/plans/` is tracked.
* Evidence: `git status --short`; `ls docs/superpowers/plans/` shows 20 tracked plan files.
* What should be checked: The repository convention for committing plan documents.
* Apply when: Plans are conventionally tracked in this repo (the directory listing suggests they are).
* Do not apply when: The working-tree plan is intentionally scratch.
* Suggested verification: `git log --oneline -- docs/superpowers/plans/ | head`

---

## 5. Unverified Assumptions

### A-1. `insights.primaryProblem` is reachable in the rendered UI

* Assumption in the plan: The `primaryProblem` string computed in Task 2 is user-visible and worth the branching logic it carries.
* Available evidence: Task 3 Step 3 renders `{primaryIssue ? formatIssueTitle(primaryIssue.code) : insights.primaryProblem}`. `diagnostics.primary_issue` is `issues[0] if issues else None` (`src/intent_routing/diagnostics/test_runs.py:171`), so `primaryProblem` renders only when the issue list is entirely empty.
* Why the assumption matters: If `issues` is rarely empty on a run worth diagnosing, most of `buildTestRunInsights`'s `primaryProblem` branching is dead code, and F-7's slicing bug is moot.
* Verification target: How often `diagnose_test_run` returns zero issues.
* Verification method: Read `src/intent_routing/diagnostics/test_runs.py:47–166` and enumerate the conditions under which no issue is appended (roughly: active + reproducible catalog with intents/examples/embeddings/ready index, `risk_pass_rate == 1.0`, no intent mismatches, fallback under 50% of failures, pass rate ≥ 70%, review rate ≤ 15%) — i.e. a fully healthy run.
* Impact if false: `primaryProblem` displays only on healthy runs, where "진단 가능한 주요 패턴이 없습니다." is the only branch that ever shows. The three-way ternary could then be simplified to a constant, reducing both code and test surface.

### A-2. Backend `reason` strings are a stable contract safe to key UI copy on

* Assumption in the plan: Mapping Korean copy by exact English string match is a durable approach.
* Available evidence: The strings are inline literals in `_compare_result` (`csv_runner.py:409–431`) with no enum, constant, or schema backing them. `tests/unit/test_ops_reports.py` also hardcodes them, so at least one other consumer is already coupled.
* Why the assumption matters: A one-word backend edit (exactly the `review`/`inspection` discrepancy in F-1) silently degrades the UI to English with no test failure anywhere.
* Verification target: Whether the reason strings are treated as a contract elsewhere, and whether an integration test pins them.
* Verification method:
  ```bash
  grep -rn "matched expected decision\|did not match expected" tests/ src/
  ```
* Impact if false: Recurring silent regressions. Mitigations range from cheap (a frontend test enumerating the five literals — see M-1) to structural (promote reasons to a `StrEnum` in `domain/enums.py` and emit a stable code alongside the prose). The latter is a backend contract change and exceeds the plan's stated scope; note it as future work rather than folding it in.

### A-3. `results` are fully loaded whenever the diagnostics panel renders

* Assumption in the plan: `buildTestRunInsights(results ?? [], …)` receives a complete result set.
* Available evidence: Contradicted by `index.tsx:150–154, 159, 168–172` — see F-11 for the specific windows.
* Why the assumption matters: An empty `results` array is indistinguishable from "no failures", and the plan's copy asserts the latter.
* Verification target: The ordering of `setSummary` / `setCurrentStep` / `setResults` in all three entry paths (create, history load, service switch).
* Verification method: Read `index.tsx:83–99` (service reset), `:112–124` (`loadRun`), `:126–166` (`handleCreate`), `:168–172` (`handleHistoryRunSelect`).
* Impact if false: Misleading empty states, worst in the create-succeeded/results-failed path that `testRunsPageContract.test.ts:137–143` explicitly protects.

### A-4. Vitest can filter to a single test file with the plan's argument form

* Assumption in the plan: `npm test -- <file> --runInBand` selects one file.
* Available evidence: `package.json` has no `test` script; the runner is `vitest run` under `test:unit`. Vitest treats bare positional arguments as filename filters, so `npm run test:unit -- testRunResultCopy` is the likely working form — but this has not been executed.
* Why the assumption matters: Every task's red/green loop depends on it.
* Verification method: `cd frontend/intent-routing-console && npm run test:unit -- testRunsPageContract` and confirm exactly one file runs.
* Impact if false: Each task's verification steps need rewriting mid-implementation; a "red" step that fails for the wrong reason invalidates the TDD signal.

### A-5. `rg` is available in the execution environment

* Assumption in the plan: Task 6 Steps 3–4 guardrail searches run.
* Available evidence: The `rg` invocation used to extract this plan's headings for review failed with `[Errno 2] No such file or directory: 'rg'`. An interactive shell may still expose `rg` via a wrapper function.
* Why the assumption matters: These two steps are the plan's only automated check for prohibited patterns (React Query, axios, trusted headers) and semantic `Tag color` usage.
* Verification method: `command -v rg` in the actual execution shell.
* Impact if false: The guardrail steps silently no-op or error; substitute `grep -rn -E` with the same patterns.

---

## 6. Alternative Approaches Worth Comparing

### O-1. Client-side rule engine vs. reusing backend diagnostics for the headline and patterns

* Existing approach: `buildTestRunInsights` re-derives failure patterns, the primary problem, and next actions in the frontend from `API.TestRunResult[]`.
* Alternative approach: Use `diagnostics.issues` (already prioritized by `ISSUE_CODE_PRIORITY`) for the headline and the "다음 조치" list, and limit the client-side aggregation strictly to the `expected → actual` pattern counting that the backend does not provide.
* Why the alternative may be relevant: `src/intent_routing/diagnostics/test_runs.py` already computes `fallback_fail_count`, `intent_mismatch_count`, and a deterministic priority ordering. The plan re-implements overlapping logic in TypeScript with slightly different thresholds and ordering, creating two sources of truth for "what is the main problem" — F-7 and F-10 are both symptoms of that divergence. The plan's Task 3 rendering already prefers `primaryIssue` over `insights.primaryProblem`, showing the backend is treated as authoritative where both exist.
* Advantages of the existing approach: Fully frontend-scoped, no deploy coordination, no API change; `expected → actual` pair counting genuinely does not exist in the backend response; iteration on copy and thresholds is fast.
* Risks of the existing approach: Duplicated and potentially divergent diagnosis logic; two places to update when routing behavior changes; no server-side tests covering the new rules.
* Advantages of the alternative: Single source of truth for prioritization; the existing Python tests already cover it; the frontend shrinks to presentation plus one aggregation.
* Risks of the alternative: If a new field is needed on the API, the plan's frontend-only scope is broken and a deploy-ordering concern appears (console must tolerate an older API). It may also require backend work not justified by this UX task.
* Prefer the existing approach when: The `expected → actual` pattern table and next-action copy are the only additions, and no new backend field is required — which is the case for the current wireframe.
* Prefer the alternative when: The primary-problem headline and next-action list are expected to grow more rules over time, or when frontend/backend disagreement on the same screen (F-7) is judged unacceptable.
* Evidence needed to decide: Whether `insights.primaryProblem` is ever rendered (A-1). If it is effectively dead, the divergence risk largely evaporates and the existing approach is clearly right; scope `buildTestRunInsights` down to pattern counting and next actions only.

---

## 7. Excessive or Unrelated Scope

### S-1. `formatIntentLabel` as a dedicated exported helper

* Planned work: Export `formatIntentLabel(intent?: string | null): string` returning `intent || '인텐트 없음'`, with its own test case.
* Why it may be excessive or unrelated: `index.tsx:215` already inlines `row.expected_intent ?? '인텐트 없음'`, and `:226` inlines `row.actual_intent ?? row.actual_route_key ?? '없음'`. Note these two currently use *different* fallback strings; the plan's helper unifies them to `'인텐트 없음'`, which is an unstated behavior change for the 실제 결과 column.
* Evidence: `index.tsx:212–229`; plan Task 1 and Task 4 Step 4.
* Risk of keeping it: Very low — one function, one line. The real issue is the silent fallback-string change, not the helper's existence.
* Conditions that would justify keeping it: If unifying the two fallbacks is intentional (a reasonable readability improvement) and is stated as such in the plan.
* Suggested decision check: Confirm whether `'없음'` → `'인텐트 없음'` for the actual-result column is desired. Also note `||` vs `??`: the helper uses `||`, so an empty-string intent maps to `'인텐트 없음'` where `??` would render an empty cell — likely the better behavior, but worth being deliberate about.

### S-2. Guardrail searches over `global.less` and `adminServices.ts`

* Planned work: Task 6 Steps 3–4 search `frontend/intent-routing-console/src/services/adminServices.ts` and `src/global.less` for prohibited patterns.
* Why it may be excessive or unrelated: No task in the plan modifies either file, and both currently carry unrelated uncommitted changes (`git status --short` shows both as modified). A guardrail search across files the plan does not touch can surface pre-existing or unrelated-branch matches and stall the task on a false positive.
* Evidence: Plan File Structure lists only `pages/TestRuns/*` files; `git status --short` shows `M src/global.less` and `M src/services/adminServices.ts` from separate in-flight work.
* Risk of keeping it: Wasted investigation on matches that belong to another change; possible confusion about whether the Test Runs work introduced them.
* Conditions that would justify keeping it: If the repo convention is a whole-console guardrail sweep before review rather than a diff-scoped one.
* Suggested decision check: Scope the searches to `pages/TestRuns` (which the plan does modify), or run them against `git diff` output rather than whole files so only lines this work introduced are evaluated.

---

## 8. Verification Gaps

### T-1. Source-order assertions cannot verify rendered order

* Behavior to verify: The six sections appear top-to-bottom in the required order on the results step.
* Current verification gap: Task 3 Step 1 asserts `source.indexOf('실패 패턴 요약') > source.indexOf('가장 먼저 확인할 문제')` on the raw text of one file. This proves nothing about the rendered DOM, and it cannot see across the `index.tsx` / `TestRunDiagnosticsPanel.tsx` boundary — which is exactly where the F-3 ordering problem lives. `vitest.config.ts` sets `environment: 'node'`, so no rendering test is possible without adding jsdom and Testing Library.
* Why the current validation may be insufficient: The panel-internal source order can be perfectly correct while `Catalog / Vector 상태` still renders above 상세 결과, because the panel as a whole sits above the `ProTable` (`index.tsx:444–447`). The suite goes green on an unmet requirement.
* Suggested verification: At minimum, add a cross-file source assertion in `testRunsPageContract.test.ts` that pins the relative order of `<TestRunDiagnosticsPanel`, `<ProTable`, and whatever renders section 6 within `index.tsx` — that is the boundary the current tests do not cover. Treat Task 6 Step 5's manual check as the authoritative gate for full ordering, and record the observed order (a screenshot or a written list) rather than only asserting it passed.
* Expected observable result: In the browser at FHD, reading top to bottom: 테스트 요약 → 가장 먼저 확인할 문제 → 실패 패턴 요약 → 다음 조치 → 상세 결과 → Catalog / Vector 상태.

### T-2. No verification that the visible table is free of English reasons

* Behavior to verify: "No visible English result reason in the detailed table" (Task 6 Step 5 acceptance).
* Current verification gap: The only automated check is that `formatResultReason` is referenced in `index.tsx`. Given F-1, the helper can be correctly wired and still emit `해석되지 않은 사유: requires human inspection` for every REVIEW row. Manual verification would also miss it unless the test dataset happens to contain a REVIEW case.
* Why the current validation may be insufficient: The requirement is about *output*, but the test asserts *wiring*.
* Suggested verification: Enumerate the five backend reason literals in `testRunResultCopy.test.ts` and assert each maps to a Korean string with no `해석되지 않은` prefix (see M-1). For the manual pass, use a CSV whose cases produce at least one PASS, one FAIL-by-decision, one FAIL-by-intent, and one REVIEW — a clarify-expected case will produce the REVIEW path per `csv_runner.py:414–417`.
* Expected observable result: Every row's 사유 cell renders Korean; hovering shows the original English via the `title` attribute.

### T-3. The red step in each task may fail for the wrong reason

* Behavior to verify: Each "Step 2: Run the test to verify it fails" genuinely demonstrates the missing behavior.
* Current verification gap: Per F-4, `npm test` does not exist, so every red step fails with "Missing script: test" — indistinguishable, to an automated reader, from the intended module-not-found failure.
* Why the current validation may be insufficient: A TDD red step that fails for an environmental reason confirms nothing about the test's discriminating power.
* Suggested verification: Fix the commands first (F-4), then for each red step record the actual failure message and confirm it names the missing module or the missing assertion target.
* Expected observable result: Task 1 Step 2 fails with a resolution error for `./testRunResultCopy`; Task 3 Step 2 fails on the specific `indexOf` assertions, not on a runner error.

### T-4. No regression check on the previously-green Test Runs suite

* Behavior to verify: Tasks 3–5 do not break the 13 existing assertions in `testRunsPageContract.test.ts` or the 4 in `testRunDiagnosticsPanelContract.test.ts`.
* Current verification gap: Each task runs only its own file; the full suite runs first at Task 6, after all five commits. F-2 shows at least four existing assertions will break at Task 3.
* Why the current validation may be insufficient: Breakage is discovered several commits late, making it harder to attribute and tempting a bulk assertion deletion.
* Suggested verification: Capture a green baseline before Task 1 (`npm run test:unit` in `frontend/intent-routing-console`, recording pass counts), and run the full `TestRuns` file set at the end of each of Tasks 3, 4, and 5 rather than only the file being edited.
* Expected observable result: Pass count is monotonically non-decreasing across tasks, and any assertion removal is accompanied by a stated rationale in the commit message.

---

## 9. Questions for the Coding Agent

1. Question: What is the complete set of `reason` literals `_compare_result` can return, and does the plan's map cover all of them?
   * Why it matters: This is the core of the user's stated requirement. F-1 shows at least two of five are unhandled, which would leave English text in the visible column.
   * Where to verify: `src/intent_routing/testing/csv_runner.py:409–431`; cross-check `tests/unit/test_ops_reports.py:168,186,273`.

2. Question: Should `Catalog / Vector 상태` render below the detailed results table (wireframe position 6), and if so, which component owns it?
   * Why it matters: F-3 shows the current component boundary makes position 6 unreachable. This is a requirement-interpretation question that changes the shape of Task 3, so it should be settled before implementation — and may warrant asking the user directly.
   * Where to verify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx:368–464`; the user's stated order "진단/실패 패턴/다음 조치/상세 결과".

3. Question: Are `결과 집계` and `실제 결정 집계` intentionally being removed from the screen?
   * Why it matters: The plan's Task 3 replacement drops them without saying so, and an existing test requires them (F-2, M-2). `actual_decision_counts` has no replacement anywhere in the new wireframe.
   * Where to verify: `TestRunDiagnosticsPanel.tsx:134–143`; `testRunDiagnosticsPanelContract.test.ts:53–54`.

4. Question: What is the correct test invocation for this package?
   * Why it matters: All 12 command blocks in the plan use a script that does not exist plus a Jest-only flag (F-4). The red/green loop is the plan's primary control mechanism.
   * Where to verify: `frontend/intent-routing-console/package.json:7–14`; `vitest.config.ts`; the command conventions used by other plans in `docs/superpowers/plans/`.

5. Question: Is `insights.primaryProblem` ever rendered, given that `diagnostics.primary_issue` takes precedence and is non-null whenever any issue exists?
   * Why it matters: Determines whether the three-way ternary and its supporting tests are worth keeping at all, and whether F-7's slicing bug has any user-visible effect (A-1, O-1).
   * Where to verify: `src/intent_routing/diagnostics/test_runs.py:47–176`; plan Task 3 Step 3 rendering.

---

## 10. Recommended Review Order

1. **F-1** — verify the backend reason literals first. It is the cheapest check and it directly determines whether the plan meets its headline requirement.
2. **F-3 and Question 2** — settle where `Catalog / Vector 상태` renders. This changes Task 3's structure, so resolve it before writing any panel code; consider confirming the interpretation with the user.
3. **F-2 and M-2** — decide, per existing assertion, whether the behavior is being relocated or removed. Capture the green baseline (T-4) at the same time.
4. **F-4 and A-4/A-5** — fix the command blocks before starting the TDD loop, so the red steps carry real signal (T-3).
5. **F-5, M-1** — close the decision-enum and reason-enum coverage gaps together; one test can cover both.
6. **A-1 / O-1** — decide how much diagnosis logic belongs in the frontend. This subsumes F-7 and may simplify Task 2 substantially.
7. **F-8, F-11** — confirm the classification precedence and the empty-`results` behavior; both may be acceptable as-is if stated deliberately.
8. **F-6, F-9, F-10, S-1, S-2, M-3, M-4** — Minor items; adopt selectively.
9. **T-1, T-2** — strengthen the verification story once the structure is settled.

---

## 11. Coding Agent Decision Record Template

Copy this block once per Finding (F-1 … F-11) and, where useful, for Missing-work (M-*), Assumption (A-*), Alternative (O-*), Scope (S-*), and Verification-gap (T-*) items.

### Decision for F-{번호}

* Decision: Accepted | Partially accepted | Rejected | Deferred
* Verification performed:
* Evidence found:
* Comparison with the original plan:
* Reason for the decision:
* Changes to the plan:
* Remaining uncertainty:

---

*This document is an independent review, not an approval or rejection. Each finding should be verified against the repository before the plan is changed; where the original plan's reasoning proves stronger, record that reasoning and keep the plan as written.*
