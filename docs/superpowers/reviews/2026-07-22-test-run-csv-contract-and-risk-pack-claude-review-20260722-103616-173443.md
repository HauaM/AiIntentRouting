# Implementation Plan Review

> Scope of this review: I read the actual repository files the plan touches
> (`src/intent_routing/testing/csv_runner.py`, `testing/gate.py`,
> `versions/releases.py`, `policy/risk.py`, `domain/enums.py`,
> `routing/engine.py`, `routing/scoring.py`, `routing/release_context.py`,
> `api/admin.py` release-candidate + `TestRunCreateRequest` sections,
> `ops/csv_baseline.py`, `tests/unit/test_pilot_fixtures.py`, and the
> `frontend/.../TestRuns` file list). Findings below are grounded in those
> reads. Where I could not confirm runtime behavior without executing the
> engine, I mark the item `Needs verification`.

## 1. Review Summary

### Overall Assessment

Review findings require consideration

### Summary

The plan correctly targets the two behaviors the user actually asked for:
(a) a simplified four-column user CSV (`case_id,query,expected_intent,memo`)
mapped internally to `positive/confident`, and (b) a release gate that requires
real risk cases in addition to `risk_pass_rate == 1.0`. Both are supported by
the current code:

* The zero-risk release loophole is real and matches the requirement's intent —
  `gate.py:28-30` sets `risk_pass_rate = 1.0` when `risk_total == 0`, and
  `releases.py:79` only checks `risk_pass_rate == 1.0`, so a run with no risk
  rows passes today. The plan's `risk_total > 0` check addresses this.
* `RoutingDecisionResult.route_key` (`scoring.py:82`) and per-intent `route_key`
  in the catalog snapshot (`release_context.py:40-55`) exist, so route-key
  hydration/comparison is technically feasible.
* DB columns `case_type`/`expected_decision` are already carried on
  `ParsedTestCase`, so a "hide externally, keep internally" split needs no
  migration, consistent with the plan.

The most important risks to re-check before implementing:

1. **The core premise that `off_topic_other_subject` routes as
   `Decision.confident` is not established.** `engine.py:118-135` short-circuits
   to `Decision.off_topic` on an off-topic policy keyword match *before*
   semantic scoring. If a query intended for `off_topic_other_subject` trips the
   service off-topic policy, the case FAILs (expected `confident`, actual
   `off_topic`). The plan's own manual scenario (Task 9) uses exactly such
   phrasing (`업무 밖 …`). This is the single most important thing to verify.
2. **Scope creep in the gate**: Task 6 promotes `review_rate > 0.15` from a
   non-blocking `recommendation` (`gate.py:39-40`) to a blocking `block_reason`.
   The user requirements never mention review rate; this changes release
   eligibility for unrelated runs.
3. **Legacy-CSV run semantics change** because route-key hydration is applied to
   all cases with an `expected_intent`, not only new four-column cases.
4. **Pilot fixture migration (Task 8)** may invalidate existing
   `csv_baseline`/threshold-report artifacts and may strip risk coverage from
   the pilot release path if that path does not go through `run_csv_tests()`
   (which is the only place the common risk pack is injected).

This is an independent review, not an approval or rejection. Priorities for the
Coding Agent: verify F-1 first, then decide on the F-3/F-2 scope questions, then
the F-4 baseline/fixture interaction.

---

## 2. Validated Parts of the Plan

### V-1. Route-key data is actually available

* Plan section: Task 3 (route-key derivation and comparison).
* Assessment: Feasible as designed.
* Evidence: `RoutingDecisionResult.route_key: str | None` (`scoring.py:82`);
  `_run_case` already reads `decision.route_key` (`csv_runner.py:400`);
  `candidates_from_snapshot` reads `item.get("route_key")` and requires it to be
  present (`release_context.py:40-55`), confirming the snapshot carries
  `route_key` per intent, which `_expected_route_keys_by_intent` depends on.
* Why this appears appropriate: The plan does not assume a data shape that is
  absent; deriving `route_key` from the snapshot is consistent with how
  candidates are already built.

### V-2. The zero-risk release loophole is real and correctly diagnosed

* Plan section: Task 6 (release eligibility requires actual risk rows).
* Assessment: Correct root-cause; the requirement is genuinely unmet today.
* Evidence: `gate.py:28-30` → `risk_pass_rate = 1.0 if risk_total == 0`;
  `releases.py:79-80` only rejects when `risk_pass_rate != 1.0`;
  `admin.py:6296-6306` computes `eligible` from `risk_pass_rate == 1.0` with no
  count check. A zero-risk run is therefore releasable now.
* Why this appears appropriate: Adding a `risk_total > 0` gate at both
  `validate_release_inputs` and the candidate listing closes exactly this hole.

### V-3. Candidate listing already loads the data the new check needs

* Plan section: Task 6 Step 4 (compute `risk_total` in candidate listing).
* Assessment: Low-cost, no new query.
* Evidence: `admin.py:6293` already calls
  `repository.list_test_results(test_run.test_run_id)` per row before building
  the response.
* Why this appears appropriate: The plan reuses the existing result set rather
  than adding a repository method, matching the plan's own "add helper only if
  duplication becomes noisy" stance.

### V-4. No-migration internal mapping is consistent with the model

* Plan section: Global Constraints + Task 2.
* Assessment: Consistent.
* Evidence: `ParsedTestCase` already carries `case_type` and
  `expected_decision` (`csv_runner.py:50-57`); `create_test_dataset` persists
  `case_type` per row (`csv_runner.py:181-190`). Deriving `positive/confident`
  from a four-column row needs no schema change.

### V-5. Risk-pack building blocks exist; the no-secrets guard is a good idea

* Plan section: Task 4 / Task 8.
* Assessment: Viable.
* Evidence: `RiskPolicy.default()` (`risk.py:79-81`) and the full `RiskType`
  enum (`enums.py:13-20`) exist; `mask_pii` already masks stored queries
  (`csv_runner.py:394`). The plan's assertion that fixtures contain no real
  secrets (`"010-"`, `"4111"`, `"sk-"`) is a sound safeguard.

---

## 3. Review Findings

### F-1. `off_topic_other_subject` may not route as `Decision.confident`

* Severity: Blocker
* Category: Requirement correctness / core assumption
* Plan section: Global Constraints; ADR "Decision"; Task 9 manual scenario.
* Evidence type: Needs verification (based on confirmed engine code path)
* Current plan: Rows with `expected_intent=off_topic_other_subject` are stored
  as `case_type=positive`, `expected_decision=confident`, and are expected to
  PASS by matching decision + intent + route_key.
* Review finding: The routing engine evaluates an off-topic *policy* layer
  before semantic intent scoring and returns `Decision.off_topic` on a keyword
  match. A query whose intended target is the `off_topic_other_subject` catalog
  intent may instead be classified `off_topic` by that policy, producing
  `actual_decision=off_topic` vs `expected_decision=confident` → FAIL.
* Evidence: `engine.py:118-135` — `if off_topic_policy is not None:` →
  `off_topic_evaluation = off_topic_policy.evaluate(query)` → on match returns
  `decision=Decision.off_topic`. This precedes the semantic scoring path
  (`scoring.py:193+`). The plan's Task 9 sample queries (`업무 밖 상담으로 보내줘`,
  `업무 밖 주제는 별도 안내로 보내줘`) are the kind of phrasing an off-topic policy
  would likely match.
* Potential impact: The headline user story ("off_topic_other_subject tested as
  a normal expected Intent") fails end-to-end; the manual acceptance check in
  Task 9 would fail; users see false FAILs.
* What the Coding Agent should verify: Whether, under a representative
  `off_topic_policy`, a query intended for `off_topic_other_subject` yields
  `Decision.confident` with `intent_id=off_topic_other_subject`, or is preempted
  to `Decision.off_topic`.
* How to verify: Construct an `ActiveReleaseContext` whose catalog registers
  `off_topic_other_subject` and whose `off_topic_policy` reflects a real pilot
  config, then call `RoutingEngine.route()` (or `run_csv_tests`) with a
  representative query and inspect `decision.decision` / `decision.intent_id`.
  Cross-check how `off_topic_policy_from_config` (`csv_runner.py:29,296`) builds
  keywords for such services.
* Decision criteria: If registered out-of-business intents are reliably routed
  as `confident`, keep the plan. If the off-topic policy layer preempts them,
  the plan needs either (a) a rule that registered intents bypass the off-topic
  policy, or (b) an explicit `expected_decision=off_topic` mapping for these
  rows — which conflicts with the "always confident" mapping.
* Possible response: Perform further investigation before deciding.

### F-2. Route-key hydration changes legacy five-column run semantics

* Severity: Major
* Category: Backward compatibility / regression
* Plan section: Task 3 Step 4 ("Call `_hydrate_expected_route_keys()` … after
  parsing normal cases and before `_run_case()`").
* Evidence type: Reasoned inference (from confirmed code)
* Current plan: `_hydrate_expected_route_keys` iterates all parsed cases with a
  non-null `expected_intent` and raises `CsvValidationError` if that intent is
  absent from the catalog; otherwise it attaches `expected_route_key` for
  comparison.
* Review finding: Because it runs on *all* parsed cases (the plan applies it
  after `parse_test_cases_csv`, which returns both new and legacy cases), legacy
  `positive`/`confusing` rows also (a) start being compared on `route_key` and
  (b) now abort the entire run if their `expected_intent` is not in the selected
  catalog — previously such a row produced an individual `FAIL` at comparison
  (`csv_runner.py:429-431`), not a whole-run error.
* Evidence: Global constraint promises legacy CSVs remain "parseable during
  migration," and Task 2's legacy test only asserts parsing
  (`test_legacy_csv_contract_still_parses`), not run semantics. Current
  `_compare_result` (`csv_runner.py:409-431`) has no route-key branch and no
  catalog-existence precondition.
* Potential impact: Existing legacy fixtures/tests that expect per-row FAILs, or
  that reference intents not present in a given catalog snapshot, may break the
  run entirely; legacy runs gain a stricter route-key check they were never
  validated against.
* What the Coding Agent should verify: Whether any legacy fixture or existing
  integration test exercises a `positive`/`confusing` row whose `expected_intent`
  is absent from the selected catalog, or relies on today's per-row FAIL.
* How to verify: Run the existing suite before/after wiring hydration; grep
  legacy fixtures for `case_type=positive`/`confusing` rows and cross-check the
  intents against the catalog snapshots those tests use.
* Decision criteria: If legacy compatibility must mean "same run outcome," gate
  hydration to only the four-column classification path. If "parseable" is
  sufficient and strict route-key checking of legacy rows is acceptable, keep the
  broad application.
* Possible response: Modify the current plan (scope hydration to classification
  cases) or Perform further investigation before deciding.

### F-3. Making `review_rate > 0.15` a blocking gate is outside the stated requirements

* Severity: Major
* Category: Scope / unrequested behavior change
* Plan section: Task 6 Step 3; "Concerns Covered … Unexpected `clarify`".
* Evidence type: Confirmed fact
* Current plan: Move `"review rate above 15%"` from `recommendations` into
  `block_reasons`, blocking release-quality runs.
* Review finding: The user requirements list only concerns `case_type` removal,
  mandatory `expected_intent`, off-topic-as-intent, common risk pack, and the
  risk-existence release gate. Review-rate blocking is not among them. Today it
  is explicitly non-blocking (`gate.py:38-40` appends to `recommendations`).
* Evidence: Requirement text (no mention of review/clarify thresholds);
  `gate.py:32-48` shows review rate is advisory. Any existing run with >15%
  clarify would newly become non-releasable, and `summarize_test_run`
  recomputes block reasons for display (`csv_runner.py:239-252`,
  `admin.py:2484-2486`).
* Potential impact: Unrelated existing/other services' release flows and their
  integration tests (`test_release_flow`, `test_admin_workflow_candidates_api`)
  may start failing; the change is hard to attribute to this feature.
* What the Coding Agent should verify: Whether the user actually wants clarify
  volume to block releases, and whether current tests assume review rate is
  advisory.
* How to verify: Re-read the requirement; grep tests for `review rate` /
  `review_rate` expectations; check whether any currently-green run has
  `review_rate > 0.15`.
* Decision criteria: Include only if the user confirms clarify volume should
  block releases; otherwise keep it as a `recommendation` and out of this
  change.
* Possible response: Remove the planned step (or split it into a separate,
  explicitly-requested change).

### F-4. Pilot fixture conversion may invalidate baseline artifacts and strip risk coverage from the pilot release path

* Severity: Major
* Category: Completeness / data & tooling compatibility
* Plan section: Task 8 (convert pilot CSVs to four columns, remove non-positive
  rows).
* Evidence type: Reasoned inference (confirmed baseline hashing + injection
  point)
* Current plan: Convert `it-helpdesk-pilot-cases*.csv` to four columns and drop
  `risk/off_topic/clarify/fallback` rows from the normal file; rely on the
  common risk pack for risk coverage.
* Review finding: Two coupled risks. (1) `csv_baseline` pins a
  `csv_sha256 = _sha256_file(csv_path)` and `required_risk_pass_rate`
  (`ops/csv_baseline.py:53-58, 119-124`); rewriting the pilot CSV changes the
  file hash and the risk composition, so existing baseline/threshold-report
  artifacts and `test_csv_baseline*` expectations may mismatch and need
  regeneration — the plan does not list regenerating those artifacts. (2) The
  common risk pack is injected only inside `run_csv_tests()` (Task 5). If the
  pilot/baseline release path parses CSVs via `parse_test_cases_csv` without
  going through `run_csv_tests`, the pilot loses its risk rows entirely and its
  release gate now fails the new `risk_total > 0` check.
* Evidence: `ops/csv_baseline.py` hashes files, not the DB `content_sha256`;
  `test_pilot_fixtures.py:88-95` currently asserts the CSV contains
  `{positive, clarify, risk, off_topic, fallback}` and `risk >= 1`; the plan
  injects risk only in `run_csv_tests`.
* Potential impact: `test_csv_baseline*` failures; a pilot that can no longer
  pass its own release gate; silent loss of risk coverage in non-console flows.
* What the Coding Agent should verify: (a) whether any baseline/threshold-report
  JSON is generated from the pilot CSVs and must be regenerated; (b) whether the
  pilot release path runs through `run_csv_tests` (and thus gets the common
  pack).
* How to verify: Trace who consumes `it-helpdesk-pilot-cases*.csv` (grep for the
  filenames and for `run_csv_tests` vs `parse_test_cases_csv` call sites); run
  `test_csv_baseline.py` after conversion.
* Decision criteria: If the pilot path uses `run_csv_tests`, conversion is safe
  once baseline artifacts are regenerated. If not, keep risk rows in the pilot
  file, or route the pilot path through the merge helper, before converting.
* Possible response: Add an additional step (regenerate baselines / confirm
  injection point) or Perform further investigation before deciding.

### F-5. `require_risk_cases` wiring into the run-time gate is unspecified

* Severity: Major
* Category: Completeness / consistency
* Plan section: Task 6 Interfaces (`GateInput.require_risk_cases: bool = False`).
* Evidence type: Confirmed fact (of omission)
* Current plan: Adds the field and a gate branch, and separately enforces
  `risk_total > 0` in `releases.py`/candidate listing. It does not state that
  `run_csv_tests` / `_gate_from_results` should pass `require_risk_cases=True`.
* Review finding: `_gate_from_results` (`csv_runner.py:434-448`) constructs
  `GateInput` without the new flag, so with the default `False` a freshly
  created run's stored `gate_passed` never reflects "risk cases required." The
  requirement ("release gate requires actual risk case existence") is then
  enforced only at release time, not at run creation. That may be acceptable
  (new runs always include the common pack, so `risk_total > 0` normally holds),
  but it should be a conscious decision, not an omission.
* Evidence: `run_csv_tests` calls `_gate_from_results` with no risk-requirement
  signal; the new gate branch only fires when the flag is set.
* Potential impact: A run created via a path that does not include the common
  pack (legacy CSV, `include_common_risk_pack=False`) reports `gate_passed=True`
  yet is rejected at release — a confusing split between "gate passed" and
  "cannot release."
* What the Coding Agent should verify: Where the risk-existence requirement
  should live (run-creation gate vs release validation vs both) and whether the
  two should agree.
* How to verify: Decide the intended UX for a run with no risk rows; check that
  `gate_passed` and release eligibility are consistent for that case.
* Decision criteria: If the gate and release checks should agree, wire
  `require_risk_cases=True` into `run_csv_tests`. If release-time enforcement is
  intentionally the only gate, document that.
* Possible response: Add an additional step (explicitly wire or explicitly
  document the split).

### F-6. Common risk-pack row→risk-type mapping relies on fragile pattern precedence

* Severity: Minor
* Category: Test robustness
* Plan section: Task 4 (`COMMON_RISK_PACK_CSV`) + `test_common_risk_pack_covers_
  all_current_risk_types`.
* Evidence type: Reasoned inference (from confirmed matcher)
* Current plan: Seven rows, one per `RiskType`, asserted to produce a matched
  set exactly equal to all `RiskType` values.
* Review finding: `RiskPolicy.evaluate` returns the *first* matching type in
  `RiskType` enum order (`risk.py:87-96`). A row's phrasing that incidentally
  contains an earlier type's keyword would be attributed to that earlier type,
  making the exact-set-equality assertion brittle as patterns evolve.
* Evidence: `risk.py:88-96` iterates `for risk_type in RiskType:` and returns on
  first `pattern in normalized_query`.
* Potential impact: A future pattern edit silently breaks the fixture test; not
  a runtime defect.
* What the Coding Agent should verify: That each proposed row matches its
  intended type first (no earlier-type keyword substring).
* How to verify: Run the proposed pack through `RiskPolicy.default().evaluate`
  and print `(query, risk_type)`.
* Decision criteria: Keep the exact-set assertion only if rows are verified
  collision-free; otherwise assert `>=` coverage per type or pin each row's
  expected type individually.
* Possible response: Modify the test assertion or Keep the current plan after
  verification.

### F-7. Common risk pack becomes un-passable for services with risk policy disabled

* Severity: Question
* Category: Failure/edge behavior
* Plan section: Global Constraints ("Common risk pack included by default").
* Evidence type: Reasoned inference (from confirmed code)
* Current plan: Every new Admin Console run includes the common risk pack and
  release requires 100% risk pass.
* Review finding: `run_csv_tests` builds the engine with
  `RiskPolicy(enabled=_risk_enabled(policy_version.risk_policy))`
  (`csv_runner.py:162-163,307,319-320`). If a service's policy has risk disabled,
  `evaluate` returns `matched=False` (`risk.py:84-85`), the common risk queries
  are not blocked → `Decision != risk` → those cases FAIL → `risk case failed`
  blocks release. Such a service could never release.
* Evidence: `_risk_enabled` reads `config.get("enabled", True)`; disabled →
  guardrail off.
* Potential impact: Services intentionally running with risk disabled are locked
  out of releases once the common pack is mandatory.
* What the Coding Agent should verify: Whether risk-disabled services exist / are
  supported, and the intended behavior for them.
* How to verify: Check whether any policy config sets risk `enabled=False`;
  decide whether the common pack should be conditional on risk being enabled.
* Decision criteria: If risk is always enabled in practice, no action. If
  disabled services are valid, define behavior (skip pack, or require enabling
  risk before release).
* Possible response: Perform further investigation before deciding.

### F-8. Merged-dataset hashing change — confirm no consumer expects `sha256(csv_text)`

* Severity: Minor
* Category: Compatibility
* Plan section: Task 5 Step 5 (hash the canonical merged dataset instead of the
  uploaded CSV).
* Evidence type: Confirmed fact (partial) + Needs verification
* Current plan: Replace `content_sha256 = sha256(csv_text)` with a hash of an
  internal canonical `case_id,query,expected_intent,case_type,memo` string.
* Review finding: `csv_baseline` computes its hash from files
  (`_sha256_file`, `ops/csv_baseline.py`), so it is unaffected — good. But the
  DB `content_sha256` semantics change from "hash of what the user uploaded" to
  "hash of derived internal dataset," which changes dedup/idempotency behavior
  if any flow compares uploads by that hash.
* Evidence: `csv_runner.py:177` currently hashes `csv_text`; no test asserts
  `content_sha256 == sha256(csv_text)` (integration tests set literal fixture
  hashes), which lowers but does not eliminate risk.
* Potential impact: If any code treats `content_sha256` as an upload
  fingerprint (e.g., "same file already imported"), merged-hash changes that
  meaning.
* What the Coding Agent should verify: Whether `content_sha256` is used anywhere
  as an upload-identity/dedup key.
* How to verify: grep for `content_sha256` reads (not just writes) across
  `src/`.
* Decision criteria: If it is only informational, the change is safe. If it is a
  dedup key, keep the raw-upload hash and store the merged hash separately.
* Possible response: Keep the current plan after verification, or Add a step to
  store both hashes.

---

## 4. Potentially Missing Work

### M-1. Handling of already-created (pre-change) Test Runs that have no risk rows

* Related requirement: "release gate requires actual risk case existence."
* Why it may be needed: After adding the `risk_total > 0` release check, every
  Test Run created before this feature (which stored only user rows, no risk
  rows) becomes non-releasable.
* Evidence: Existing runs were created by today's `run_csv_tests`, which appends
  no risk pack; the new check reads persisted `TestResult` rows.
* What should be checked: Whether any in-flight/approved runs are expected to be
  released after deployment.
* Apply when: Environments already contain Test Runs intended for release.
* Do not apply when: This is greenfield or all runs will be recreated after
  deploy.
* Suggested verification: Query existing runs for `case_type=risk` presence;
  decide whether to communicate "re-run required" or backfill.

### M-2. Frontend `createTestRun` service + payload wiring for optional risk CSV

* Related requirement: Common/service-specific risk pack inclusion.
* Why it may be needed: The plan adds `risk_csv_text` / `risk_source_filename` /
  `include_common_risk_pack` to the backend request and to `types/api.d.ts`, but
  Task 7's interfaces only mention "Consumes: existing `createTestRun()`." The
  service function and the create payload in `index.tsx` must actually pass (or
  intentionally omit) these fields.
* Evidence: Plan Task 5 changes `TestRunCreateRequest`; Task 7 does not describe
  updating the `createTestRun` call payload beyond the four-column CSV.
* What should be checked: Whether the console needs to send a service-specific
  risk CSV in this iteration, or relies purely on the default common pack.
* Apply when: The UI must let users attach service-specific risk CSVs now.
* Do not apply when: MVP only needs the auto-included common pack (then just
  ensure the backend defaults `include_common_risk_pack` correctly when the
  field is omitted).
* Suggested verification: Trace `createTestRun` (service layer) and confirm the
  payload shape matches `TestRunCreateRequest` with `extra="forbid"`
  (`admin.py:888`) so unknown fields are not sent.

### M-3. Regenerating baseline / threshold-report artifacts after pilot CSV changes

* Related requirement: Pilot fixture migration (Task 8).
* Why it may be needed: See F-4; `csv_sha256` and risk-pass expectations are
  pinned in baseline artifacts.
* Evidence: `ops/csv_baseline.py:53-58`, `test_csv_baseline.py:107-110`.
* What should be checked: Which committed baseline/threshold JSON files
  reference the pilot CSVs.
* Apply when: Pilot CSV contents change and baseline artifacts exist.
* Do not apply when: No baseline artifact references the changed files.
* Suggested verification: grep for the pilot filenames and for `csv_sha256`
  across `docs/` and test fixtures; regenerate as needed.

---

## 5. Unverified Assumptions

### A-1. Registered out-of-business intents route as `confident`

* Assumption in the plan: `off_topic_other_subject` yields
  `Decision.confident` + matching intent/route_key.
* Available evidence: Contradicted-in-part by `engine.py:118-135` (off-topic
  policy preempts before scoring).
* Why the assumption matters: It underpins the entire "off-topic-as-intent"
  requirement and the Task 9 acceptance check.
* Verification target: `RoutingEngine.route()` output for such queries under a
  real off-topic policy.
* Verification method: See F-1 "How to verify."
* Impact if false: Core requirement unmet; false FAILs; manual scenario fails.

### A-2. The pilot/baseline release path routes through `run_csv_tests`

* Assumption in the plan: Removing risk rows from pilot CSVs is safe because the
  common pack is auto-included.
* Available evidence: Common pack is injected only in `run_csv_tests` (Task 5);
  baseline tooling reads files directly.
* Why the assumption matters: If the pilot path bypasses `run_csv_tests`, it
  loses risk coverage and fails the new gate.
* Verification target: The call graph from pilot/baseline generation to case
  execution.
* Verification method: grep for `run_csv_tests` vs `parse_test_cases_csv`
  callers in `src/intent_routing/ops/` and scripts.
* Impact if false: Pilot cannot pass its own release gate; silent risk-coverage
  loss.

### A-3. Every removed non-positive pilot row is either unregistered or safely relocated

* Assumption in the plan: Off-topic rows map to registered intents (convert) or
  become docs examples.
* Available evidence: `test_pilot_fixtures.py:136-146` currently tracks
  per-type counts and positive intents; the mapping of each existing row is not
  shown.
* Why the assumption matters: Misclassifying a row (e.g., a real risk phrase
  left in the normal file) would change gate math or produce a validation error.
* Verification target: The current contents of each pilot CSV vs the target
  catalog intents.
* Verification method: Diff each converted row against the catalog snapshot's
  intent list.
* Impact if false: Broken pilot runs or misleading coverage.

---

## 6. Alternative Approaches Worth Comparing

### O-1. Enforce risk-existence at the run-creation gate vs only at release time

* Existing approach: Enforce `risk_total > 0` in `releases.py` +
  candidate-listing; leave `GateInput.require_risk_cases` default `False`
  (unwired in `run_csv_tests`).
* Alternative approach: Also pass `require_risk_cases=True` from
  `_gate_from_results`/`run_csv_tests` so `gate_passed` itself reflects the
  requirement at creation time.
* Why the alternative may be relevant: It keeps `gate_passed` and release
  eligibility consistent, avoiding a "gate passed but not releasable" state
  (see F-5).
* Advantages of the existing approach: Minimal change to run creation; new runs
  normally include the pack so the difference rarely surfaces.
* Risks of the existing approach: Inconsistent signals for no-risk runs (legacy,
  `include_common_risk_pack=False`).
* Advantages of the alternative: Single source of truth; earlier, clearer
  feedback in the UI.
* Risks of the alternative: Could unexpectedly flip `gate_passed` for legacy
  runs that intentionally have no risk rows.
* Prefer the existing approach when: Only console v2 runs need the guarantee and
  legacy runs must keep today's `gate_passed`.
* Prefer the alternative when: The product wants "no risk coverage" surfaced at
  run time, not just at release.
* Evidence needed to decide: Whether any supported flow legitimately produces a
  no-risk run that should still show `gate_passed=True`.

---

## 7. Excessive or Unrelated Scope

### S-1. Review-rate blocking (Task 6 Step 3)

* Planned work: Convert `review_rate > 0.15` from recommendation to
  `block_reason`.
* Why it may be excessive or unrelated: No user requirement references review /
  clarify thresholds; it changes release behavior for runs unrelated to the CSV
  contract / risk pack.
* Evidence: Requirement text; `gate.py:38-40` (currently advisory).
* Risk of keeping it: Unrelated release-flow regressions and test churn;
  attribution confusion.
* Conditions that would justify keeping it: The user explicitly wants clarify
  volume to block releases.
* Suggested decision check: Confirm with the requirement owner; otherwise split
  into a separate change. (Cross-ref F-3.)

### S-2. Applying route-key comparison to legacy five-column runs

* Planned work: Hydrate + compare `route_key` for all cases including legacy
  positive/confusing.
* Why it may be excessive or unrelated: The requirement targets the *new* user
  contract; legacy is only meant to remain compatible during migration.
* Evidence: Global constraint scopes legacy to "remain parseable."
* Risk of keeping it: Legacy runs fail differently than before (cross-ref F-2).
* Conditions that would justify keeping it: A deliberate decision to strengthen
  legacy validation too.
* Suggested decision check: Decide whether hydration is gated to the
  classification path.

---

## 8. Verification Gaps

### T-1. No end-to-end test that `off_topic_other_subject` routes as confident

* Behavior to verify: A registered out-of-business intent is PASS with
  `expected_decision=confident`.
* Current verification gap: Plan tests assert parsing/mapping
  (`case_type=positive`), not the engine's actual decision for such a query.
* Why the current validation may be insufficient: The off-topic policy layer
  (F-1) can override the decision; parsing tests never exercise `route()`.
* Suggested verification: An integration test that runs a query for
  `off_topic_other_subject` through `run_csv_tests` (or the engine) with a
  realistic off-topic policy and asserts `result == "PASS"`.
* Expected observable result: `actual_decision=confident`,
  `actual_intent=off_topic_other_subject`, matching route_key.

### T-2. No regression test reproducing the exact zero-risk release bug

* Behavior to verify: A run with `risk_total == 0` is rejected at release even
  though `risk_pass_rate == 1.0`.
* Current verification gap: Plan's release tests focus on the new happy path;
  the specific "zero risk but risk_pass_rate 1.0" case is the bug being fixed.
* Why the current validation may be insufficient: Without a test hitting
  `risk_total == 0`, a future refactor could reopen the loophole.
* Suggested verification: A test asserting `validate_release_inputs` (and
  candidate listing `eligible=False`) rejects a run whose results contain no
  `case_type=risk` rows despite `risk_pass_rate == Decimal("1.0")`.
* Expected observable result: `ReleaseValidationError` / `eligible=False` with a
  risk-required block reason.

### T-3. No test for risk-policy-disabled services (F-7)

* Behavior to verify: Intended behavior when the common pack runs under a
  risk-disabled policy.
* Current verification gap: No scenario covers `risk_enabled=False` with a
  mandatory common pack.
* Why the current validation may be insufficient: The failure mode (all risk
  cases FAIL → never releasable) would only surface in production.
* Suggested verification: A unit/integration test defining the expected outcome
  for a risk-disabled service.
* Expected observable result: Whatever the team decides (skip pack, or explicit
  block with a clear reason).

---

## 9. Questions for the Coding Agent

1. Question: Under a representative service off-topic policy, does a query
   intended for `off_topic_other_subject` actually return `Decision.confident`,
   or is it preempted to `Decision.off_topic` by `engine.py:118-135`?
   * Why it matters: It determines whether the central "off-topic-as-intent"
     requirement is achievable with the current engine.
   * Where to verify: `routing/engine.py:118-135`,
     `routing/release_context.py` (`off_topic_policy_from_config`), and a live
     `RoutingEngine.route()` call.

2. Question: Does the pilot / baseline release path execute through
   `run_csv_tests` (which injects the common risk pack), or does it parse CSVs
   directly?
   * Why it matters: Decides whether Task 8's removal of risk rows from pilot
     CSVs silently drops risk coverage and breaks the pilot's own gate.
   * Where to verify: callers of `run_csv_tests` vs `parse_test_cases_csv` in
     `src/intent_routing/ops/` and any pilot scripts; `ops/csv_baseline.py`.

3. Question: Is turning `review_rate > 0.15` into a release blocker actually
   desired, or should it remain advisory?
   * Why it matters: It is not in the stated requirements and changes unrelated
     release flows/tests.
   * Where to verify: requirement text; `gate.py:38-40`; `test_release_flow`.

4. Question: Should legacy five-column runs receive the new route-key comparison
   and abort-on-unknown-intent behavior, or only the new four-column contract?
   * Why it matters: Determines whether hydration is gated to the classification
     path and whether legacy compatibility means "parseable" or "same outcome."
   * Where to verify: `csv_runner.py:409-431`, legacy fixtures/tests.

5. Question: Do any environments hold pre-existing Test Runs (no risk rows) that
   must remain releasable after this change?
   * Why it matters: The new `risk_total > 0` gate would block them (M-1).
   * Where to verify: existing `TestRun`/`TestResult` data.

---

## 10. Recommended Review Order

1. Verify F-1 / A-1 (off-topic routing) — it can invalidate the core premise.
2. Verify A-2 (pilot path injection) and F-4 (baseline artifacts) together.
3. Decide the F-3 / S-1 scope question (review-rate blocking) against the
   requirement.
4. Decide the F-2 / S-2 question (legacy route-key hydration scope).
5. Resolve F-5 / O-1 (where risk-existence is enforced) for gate/release
   consistency.
6. Add the missing verifications T-1, T-2 (and T-3 if F-7 is in scope).
7. Handle M-1/M-2/M-3 and the Minor items F-6/F-8 last.

---

## 11. Coding Agent Decision Record Template

> Copy this block once per Finding (F-1 … F-8), and reuse for M-/A-/O-/S-/T-
> items as needed.

### Decision for F-{번호}

* Decision: Accepted | Partially accepted | Rejected | Deferred
* Verification performed:
* Evidence found:
* Comparison with the original plan:
* Reason for the decision:
* Changes to the plan:
* Remaining uncertainty:
