# BGE Catalog Scope Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep BGE-M3 from turning catalog-unregistered business requests into single-intent `clarify` results; such requests must remain `fallback`.

**Architecture:** Add a small internal decision guard in `DecisionComposer` after candidate ranking but before the single-candidate below-threshold clarify path. The guard remains invisible to developers: developer-facing docs describe it as "미등록 업무 fallback 보호" and keep the existing template, preset, example, and CSV workflow.

**Tech Stack:** Python 3.12, FastAPI runtime domain code, pytest, uv, BGE-M3 optional embedding extra, existing pilot rehearsal scripts.

---

## Scope

In scope:

- Preserve policy A: catalog-unregistered internal business requests such as meeting rooms, toner, business trips, name cards, and document cabinet permissions must return `fallback`.
- Keep real ambiguity as `clarify`, especially when multiple viable candidates compete.
- Keep keyword-supported in-catalog requests on the existing path.
- Keep developer experience simple: no new developer-facing numeric tuning fields, no new CSV columns, no Admin UI implementation.
- Re-run BGE package/benchmark evidence and closed-network rehearsal against the clean runtime model path.

Out of scope:

- Admin UI implementation.
- Changing BGE model files.
- Refreshing the checked-in CSV baseline without a separate approval record.
- Broad threshold retuning unless the rehearsal shows a separate positive-case calibration issue.

## File Structure

- Modify `src/intent_routing/routing/scoring.py`
  - Owns `DecisionComposer` and the internal confidence/margin decision path.
  - Add the catalog-scope fallback guard here because it is a decision policy, not a model or API concern.
- Modify `tests/unit/test_scoring_decision.py`
  - Add unit coverage for the guard and regression coverage for valid clarify behavior.
  - Add a `RoutingEngine` regression proving real query keyword evidence flows into the guard through `include_keyword_match_count`.
- Modify `docs/pilot/README.md`
  - Document the developer-facing behavior using product language: `미등록 업무 fallback 보호`.
  - Keep developer instructions at the `case_type=fallback` level.
- Modify `tests/unit/test_pilot_fixtures.py`
  - Add a docs contract test that the pilot README explains the fallback protection in developer-friendly terms and does not call it `scoring guard`.
- Local evidence only under `var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/`
  - Ignored runtime evidence; do not commit model files, secret state, or evidence bundles unless a separate closure task asks for official docs.

---

### Task 1: Set Up Isolated Work And Baseline

**Files:**
- No source changes in this task.

- [ ] **Step 1: Create an isolated worktree branch**

Run:

```bash
git status --short --branch
git worktree add .worktrees/codex-bge-catalog-scope-protection -b codex/bge-catalog-scope-protection
cd .worktrees/codex-bge-catalog-scope-protection
```

Expected:

```text
## main...origin/main
Preparing worktree (new branch 'codex/bge-catalog-scope-protection')
```

- [ ] **Step 2: Confirm the workspace starts clean**

Run:

```bash
git status --short --branch
```

Expected:

```text
## codex/bge-catalog-scope-protection
```

- [ ] **Step 3: Run focused baseline tests**

Run:

```bash
uv run pytest tests/unit/test_scoring_decision.py tests/unit/test_pilot_fixtures.py -q
```

Expected:

```text
passed
```

If this baseline fails before edits, stop and investigate before changing behavior.

---

### Task 2: Add Failing Catalog Scope Protection Tests

**Files:**
- Modify: `tests/unit/test_scoring_decision.py`

- [ ] **Step 1: Add the unit tests**

Insert these tests after `test_below_threshold_returns_clarify_with_max_three_candidates`:

```python
def test_single_keywordless_below_threshold_candidate_falls_back_as_outside_catalog_scope() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_password_reset",
                "Password reset",
                "IT",
                "it.password_reset.self_service",
                0.59,
                include_keyword_match_count=0,
            ),
        ]
    )

    assert result.decision == Decision.fallback
    assert result.intent_id is None
    assert result.route_key is None
    assert result.decision_state is not None
    assert result.decision_state["decision_reason"] == "outside_catalog_scope"


def test_keyword_supported_single_candidate_still_clarifies_below_threshold() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.79,
                include_keyword_match_count=1,
            ),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert result.clarify.reason == "below_threshold"
    assert result.intent_id is None
    assert result.route_key is None


def test_two_viable_keywordless_candidates_still_clarify_when_close() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.78,
                include_keyword_match_count=0,
            ),
            CandidateScore(
                "it_password_reset",
                "Password reset",
                "IT",
                "it.password_reset.self_service",
                0.76,
                include_keyword_match_count=0,
            ),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert result.clarify.reason == "top_candidates_close"
    assert [candidate.intent_id for candidate in result.clarify.candidates] == [
        "it_api_timeout",
        "it_password_reset",
    ]
```

- [ ] **Step 2: Add the routing engine regression test**

Insert this test before `test_routing_engine_treats_empty_scope_as_unrestricted`:

```python
def test_routing_engine_falls_back_when_single_semantic_candidate_lacks_catalog_keyword_signal() -> None:
    engine = RoutingEngine(
        risk_policy=_AllowAllRiskPolicy(),
        candidate_loader=lambda _service_id, _release: [
            IntentCandidate(
                intent_id="it_password_reset",
                display_name="Password reset",
                domain="IT",
                route_key="it.password_reset.self_service",
                include_keywords=("비밀번호", "계정 잠금", "password"),
            )
        ],
        semantic_search=lambda _query, _candidates, _release: {
            "it_password_reset": SemanticMatch(positive_scores=[0.59], negative_scores=[]),
        },
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="회의실 예약 변경 방법을 알려주세요",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(
                release_version="rel-1",
                off_topic_policy=ServiceOffTopicPolicy(enabled=False, keywords=[], message=""),
            ),
        )
    )

    assert result.decision == Decision.fallback
    assert result.decision_state is not None
    assert result.decision_state["decision_reason"] == "outside_catalog_scope"
    assert result.decision_state["ranking"][0]["score_breakdown"][
        "include_keyword_match_count"
    ] == 0
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
uv run pytest \
  tests/unit/test_scoring_decision.py::test_single_keywordless_below_threshold_candidate_falls_back_as_outside_catalog_scope \
  tests/unit/test_scoring_decision.py::test_routing_engine_falls_back_when_single_semantic_candidate_lacks_catalog_keyword_signal \
  -q
```

Expected:

```text
FAILED ... assert <Decision.clarify: 'clarify'> == <Decision.fallback: 'fallback'>
```

The failure must be an actual `clarify` versus `fallback` mismatch. If it fails for import, syntax, or fixture reasons, fix the test before implementing production code.

---

### Task 3: Implement Minimal Internal Guard

**Files:**
- Modify: `src/intent_routing/routing/scoring.py`

- [ ] **Step 1: Add the guard after close-candidate clarify and before single-candidate below-threshold clarify**

In `DecisionComposer.compose`, keep the existing `viable_candidates` block and add only this new branch immediately before the existing block that returns `_clarify(reason="below_threshold", ...)`:

```python
        if (
            len(viable_candidates) == 1
            and top_candidate.confidence < self.threshold_config.resolved_threshold
            and top_candidate.include_keyword_match_count == 0
        ):
            return self._fallback(
                top_candidate=top_candidate,
                margin=margin,
                ranked=ranked,
                reason="outside_catalog_scope",
            )
```

The surrounding shape should be:

```python
        viable_candidates = [
            candidate
            for candidate in ranked
            if candidate.confidence >= self.threshold_config.min_candidate_score
        ]
        if len(viable_candidates) >= 2 and margin < self.threshold_config.clarify_margin:
            return self._clarify(
                reason="top_candidates_close",
                top_candidate=top_candidate,
                margin=margin,
                candidates=viable_candidates,
                ranked=ranked,
            )

        if (
            len(viable_candidates) == 1
            and top_candidate.confidence < self.threshold_config.resolved_threshold
            and top_candidate.include_keyword_match_count == 0
        ):
            return self._fallback(
                top_candidate=top_candidate,
                margin=margin,
                ranked=ranked,
                reason="outside_catalog_scope",
            )

        if (
            top_candidate.confidence >= self.threshold_config.min_candidate_score
            and top_candidate.confidence < self.threshold_config.resolved_threshold
        ):
            return self._clarify(
                reason="below_threshold",
                top_candidate=top_candidate,
                margin=margin,
                candidates=viable_candidates or [top_candidate],
                ranked=ranked,
            )
```

- [ ] **Step 2: Run the focused tests and verify GREEN**

Run:

```bash
uv run pytest tests/unit/test_scoring_decision.py -q
```

Expected:

```text
passed
```

- [ ] **Step 3: Commit the scoring behavior**

Run:

```bash
git add src/intent_routing/routing/scoring.py tests/unit/test_scoring_decision.py
git commit -m "fix: protect catalog fallback decisions under bge"
```

Expected:

```text
[codex/bge-catalog-scope-protection ...] fix: protect catalog fallback decisions under bge
```

---

### Task 4: Document Developer-Friendly Behavior

**Files:**
- Modify: `docs/pilot/README.md`
- Modify: `tests/unit/test_pilot_fixtures.py`

- [ ] **Step 1: Add a failing docs contract test**

Append this test to `tests/unit/test_pilot_fixtures.py`:

```python
def test_pilot_readme_documents_unregistered_work_fallback_protection() -> None:
    readme = (ROOT / "docs/pilot/README.md").read_text(encoding="utf-8")

    assert "## 미등록 업무 Fallback 보호" in readme
    assert "case_type=fallback" in readme
    assert "scoring guard" not in readme
```

- [ ] **Step 2: Run the docs test and verify RED**

Run:

```bash
uv run pytest tests/unit/test_pilot_fixtures.py::test_pilot_readme_documents_unregistered_work_fallback_protection -q
```

Expected:

```text
FAILED ... assert '## 미등록 업무 Fallback 보호' in ...
```

- [ ] **Step 3: Add developer-facing README text**

Insert this section in `docs/pilot/README.md` immediately after the paragraph that starts `Supported case types are`:

```markdown
## 미등록 업무 Fallback 보호

`case_type=fallback`은 등록된 Intent에 없는 질문입니다. 파일럿에서는
회의실 예약, 프린터 토너, 출장 정산, 명함 제작처럼 현재 카탈로그에 없는
사내 업무를 기존 Intent로 억지 분류하지 않습니다.

개발자는 숫자 기준을 조정하지 않고 CSV와 예시로 판단합니다.

- 처리해야 하는 새 업무라면 새 Intent와 positive example을 추가합니다.
- 기존 Intent로 가면 안 되는 헷갈리는 질문이면 negative example을 추가합니다.
- 현재 파일럿 범위 밖이면 `case_type=fallback`으로 유지합니다.
```

- [ ] **Step 4: Run docs tests and verify GREEN**

Run:

```bash
uv run pytest tests/unit/test_pilot_fixtures.py -q
```

Expected:

```text
passed
```

- [ ] **Step 5: Commit documentation**

Run:

```bash
git add docs/pilot/README.md tests/unit/test_pilot_fixtures.py
git commit -m "docs: describe catalog fallback protection"
```

Expected:

```text
[codex/bge-catalog-scope-protection ...] docs: describe catalog fallback protection
```

---

### Task 5: Run Focused Verification

**Files:**
- No source changes in this task.

- [ ] **Step 1: Run routing and pilot fixture tests**

Run:

```bash
uv run pytest tests/unit/test_scoring_decision.py tests/unit/test_pilot_fixtures.py -q
```

Expected:

```text
passed
```

- [ ] **Step 2: Run docs and pilot contract tests likely affected by the decision semantics**

Run:

```bash
uv run pytest \
  tests/unit/test_csv_gate.py \
  tests/unit/test_pilot_rehearsal.py \
  tests/unit/test_pilot_rehearsal_docs_contract.py \
  tests/unit/test_dify_smoke.py \
  tests/integration/test_pilot_rehearsal_flow.py \
  -q
```

Expected:

```text
passed
```

- [ ] **Step 3: Run static checks**

Run:

```bash
uv run ruff check src scripts tests
uv run mypy src tests
```

Expected:

```text
All checks passed!
Success: no issues found
```

- [ ] **Step 4: Commit any verification-only doc adjustments**

Run only if Step 2 or Step 3 required small doc/test expectation changes:

```bash
git add docs tests
git commit -m "test: align pilot contracts with catalog fallback protection"
```

Expected when there are changes:

```text
[codex/bge-catalog-scope-protection ...] test: align pilot contracts with catalog fallback protection
```

If there are no changes, skip this step.

---

### Task 6: Recreate BGE Measured Evidence

**Files:**
- Local-only evidence under `var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/`
- Local-only secret state under `var/pilot/it-helpdesk-pilot-bge-scope-protection-20260630.state.secret.json`

- [ ] **Step 1: Confirm the clean runtime model path and SHA**

Run:

```bash
test -d /home/haua/workspace/models/embedded/bge-m3-runtime
uv run python scripts/verify_bge_m3_package.py \
  --model-path /home/haua/workspace/models/embedded/bge-m3-runtime \
  --expected-sha256 f1ba7b98915784bda8424a5b15333fd4862c962449905be84e97921af7cf52ba \
  --out-dir var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-package
```

Expected:

```text
var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-package/bge-m3-package.json
var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-package/bge-m3-package.md
```

- [ ] **Step 2: Run the BGE benchmark**

Run:

```bash
uv run --extra embedding python scripts/benchmark_bge_m3.py \
  --model-path /home/haua/workspace/models/embedded/bge-m3-runtime \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --batch-size 16 \
  --out-dir var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-benchmark
```

Expected:

```text
var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-benchmark/bge-m3-benchmark.json
var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-benchmark/bge-m3-benchmark.md
```

Then inspect:

```bash
jq '{model_version, dimension, batch_size, max_tokens, query_count, latency_ms, max_rss_mb}' \
  var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/bge-benchmark/bge-m3-benchmark.json
```

Expected values:

```json
{
  "dimension": 1024,
  "batch_size": 16,
  "max_tokens": 256,
  "query_count": 50
}
```

- [ ] **Step 3: Start isolated Postgres**

Run:

```bash
docker run --rm \
  --name intent-routing-bge-scope-postgres \
  -e POSTGRES_DB=intent_routing \
  -e POSTGRES_USER=intent \
  -e POSTGRES_PASSWORD=intent \
  -p 127.0.0.1:55437:5432 \
  -d pgvector/pgvector:pg16

for i in $(seq 1 30); do
  docker exec intent-routing-bge-scope-postgres pg_isready -U intent -d intent_routing && exit 0
  sleep 1
done
exit 1
```

Expected:

```text
/var/run/postgresql:5432 - accepting connections
```

- [ ] **Step 4: Migrate the isolated DB**

Run:

```bash
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55437/intent_routing \
INTENT_ROUTING_ENVIRONMENT=pilot \
ADMIN_BOOTSTRAP_TOKEN=local-admin-token \
RAW_TEXT_KEK_ID=local-kek-001 \
RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/home/haua/workspace/models/embedded/bge-m3-runtime \
BGE_M3_MODEL_SHA256=f1ba7b98915784bda8424a5b15333fd4862c962449905be84e97921af7cf52ba \
BGE_M3_BATCH_SIZE=16 \
BGE_M3_MAX_TOKENS=256 \
uv run --extra embedding alembic upgrade head
```

Expected:

```text
Running upgrade ... 0004_security_lifecycle_ops
```

- [ ] **Step 5: Start the API on port 8004**

Run:

```bash
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55437/intent_routing \
INTENT_ROUTING_ENVIRONMENT=pilot \
ADMIN_BOOTSTRAP_TOKEN=local-admin-token \
RAW_TEXT_KEK_ID=local-kek-001 \
RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/home/haua/workspace/models/embedded/bge-m3-runtime \
BGE_M3_MODEL_SHA256=f1ba7b98915784bda8424a5b15333fd4862c962449905be84e97921af7cf52ba \
BGE_M3_BATCH_SIZE=16 \
BGE_M3_MAX_TOKENS=256 \
uv run --extra embedding uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8004
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8004
```

Keep this process running while Step 6 executes.

- [ ] **Step 6: Run closed-network rehearsal**

Run in a second shell:

```bash
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55437/intent_routing \
INTENT_ROUTING_ENVIRONMENT=pilot \
ADMIN_BOOTSTRAP_TOKEN=local-admin-token \
RAW_TEXT_KEK_ID=local-kek-001 \
RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/home/haua/workspace/models/embedded/bge-m3-runtime \
BGE_M3_MODEL_SHA256=f1ba7b98915784bda8424a5b15333fd4862c962449905be84e97921af7cf52ba \
BGE_M3_BATCH_SIZE=16 \
BGE_M3_MAX_TOKENS=256 \
uv run --extra embedding python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8004 \
  --admin-token local-admin-token \
  --service-id it-helpdesk-pilot-bge-scope-protection-20260630 \
  --environment pilot \
  --state-path var/pilot/it-helpdesk-pilot-bge-scope-protection-20260630.state.secret.json \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /home/haua/workspace/models/embedded/bge-m3-runtime \
  --bge-expected-sha256 f1ba7b98915784bda8424a5b15333fd4862c962449905be84e97921af7cf52ba \
  --run-bge-benchmark \
  --out-dir var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/rehearsal
```

Expected for this task:

```text
var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/rehearsal/pilot-rehearsal-manifest.json
var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/rehearsal/pilot-rehearsal-manifest.md
```

Then inspect:

```bash
jq '{final_status, secret_scan, steps: [.steps[] | {name, status, error_message}]}' \
  var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/rehearsal/pilot-rehearsal-manifest.json
```

Acceptance for this feature:

```text
bge-package: pass
bge-benchmark: pass
pilot-e2e-smoke: pass
secret_scan.passed: true
```

If `csv-baseline` fails after e2e passes, do not refresh the baseline in this task. Record the exact block reasons and open a follow-up BGE positive-case calibration plan because that is a broader approval surface than policy A.

- [ ] **Step 7: Stop local services**

Run:

```bash
docker stop intent-routing-bge-scope-postgres
```

Stop the API process with `Ctrl-C`.

Expected:

```text
intent-routing-bge-scope-postgres
```

---

### Task 7: Final Verification And PR Prep

**Files:**
- Source/test/doc files changed by earlier tasks only.

- [ ] **Step 1: Run focused tests again**

Run:

```bash
uv run pytest tests/unit/test_scoring_decision.py tests/unit/test_pilot_fixtures.py -q
```

Expected:

```text
passed
```

- [ ] **Step 2: Run broader unit suite**

Run:

```bash
uv run pytest tests/unit -q
```

Expected:

```text
passed
```

- [ ] **Step 3: Run static verification**

Run:

```bash
uv run ruff check src scripts tests
uv run mypy src tests
docker compose --profile runtime config >/tmp/intent-routing-compose-config.txt
```

Expected:

```text
All checks passed!
Success: no issues found
```

- [ ] **Step 4: Review the git diff**

Run:

```bash
git status --short
git diff -- src/intent_routing/routing/scoring.py tests/unit/test_scoring_decision.py docs/pilot/README.md tests/unit/test_pilot_fixtures.py
```

Expected:

```text
Only scoring, scoring tests, pilot README, and pilot fixture docs tests changed.
```

- [ ] **Step 5: Commit remaining changes**

Run only if there are unstaged changes:

```bash
git add src/intent_routing/routing/scoring.py tests/unit/test_scoring_decision.py docs/pilot/README.md tests/unit/test_pilot_fixtures.py
git commit -m "test: verify catalog fallback protection"
```

Expected when there are changes:

```text
[codex/bge-catalog-scope-protection ...] test: verify catalog fallback protection
```

- [ ] **Step 6: Summarize residual launch gates**

Before opening the PR, report:

```text
BGE package SHA:
BGE benchmark dimension/batch/max_tokens/query_count:
Closed-network rehearsal final_status:
Secret scan passed:
Dify fallback smoke status:
CSV baseline status:
Remaining non-BGE gates: Dify UI dry-run, branch protection, CSV freeze approval, release/go-no-go owner approvals.
```

Do not claim Go unless every required launch gate is actually closed.

---

## Acceptance Criteria

- `DecisionComposer` returns `fallback` with decision reason `outside_catalog_scope` for one viable below-threshold candidate with no include keyword match.
- `DecisionComposer` still returns `clarify` for close competing candidates.
- `DecisionComposer` still returns `clarify` for one keyword-supported below-threshold in-catalog candidate.
- `RoutingEngine` preserves the same behavior through real keyword matching.
- Developer-facing docs say `미등록 업무 Fallback 보호`, not `scoring guard`.
- No new developer-facing numeric tuning or CSV columns are introduced.
- BGE clean runtime package preflight passes with SHA `f1ba7b98915784bda8424a5b15333fd4862c962449905be84e97921af7cf52ba`.
- BGE benchmark passes with dimension `1024`, batch size `16`, max tokens `256`, and query count `50`.
- Closed-network rehearsal no longer fails on the `회의실 예약 변경 방법을 알려주세요` Dify fallback smoke.
- If remaining rehearsal failure is CSV baseline drift from BGE positive-case calibration, it is documented as a follow-up approval/calibration task rather than hidden by a baseline refresh.

## Manual Review Notes

- Read `pilot-rehearsal-manifest.md` first.
- Confirm the fallback smoke case is `fallback`, not `clarify`.
- Confirm `secret_scan.passed` is true and findings are empty.
- Confirm no `.secret.json` file is attached to evidence.
- Confirm local evidence paths under `var/evidence/` remain untracked by git.
- Confirm no Admin UI files changed.

## Implementation Recommendation

Use **Subagent-Driven** execution. Task 2/3 can be handled by a scoring worker, Task 4 by a docs-contract worker, and Task 6 by a verification worker. The final review should stay inline so the same session checks the manifest, residual gates, and PR summary.
