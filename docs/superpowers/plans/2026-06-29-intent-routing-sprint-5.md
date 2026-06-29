# Sprint 5: 파일럿 운영 리허설과 폐쇄망 증적 패키지 구현 계획

> **에이전트 작업자 필수 지침:** 이 계획을 실행할 때는 필수 하위 스킬로 `superpowers:subagent-driven-development`(권장) 또는 `superpowers:executing-plans`를 사용한다. 각 단계는 체크박스(`- [ ]`)로 진행 상태를 추적한다.

**목표:** Sprint 0-4에서 준비한 API-only Intent Routing Service를 실제 파일럿 운영 리허설 수준으로 끌어올려, 폐쇄망 배포 검증, Dify HTTP Request node dry-run, CSV 기준선 회귀 비교, BGE-M3 package/benchmark 증적, 보안 운영 증적, branch protection 절차를 하나의 반복 가능한 증적 패키지로 제출할 수 있게 한다.

**아키텍처:** 라우팅 엔진, threshold preset, API 계약, 보안 lifecycle 동작은 변경하지 않는다. 기존 operator script를 orchestration layer로 묶고, 결과를 `pilot-rehearsal-manifest.json/md`로 집계한다. GitHub CI와 로컬 개발 환경은 fake embedding 기반으로 deterministic하게 검증하고, 실제 BGE-M3 모델 package preflight와 benchmark는 폐쇄망 host에서 blocking 증적으로 캡처한다.

**기술 스택:** Python 3.12, FastAPI TestClient/httpx, 기존 pilot/evidence scripts, PostgreSQL 16 + pgvector, Docker Compose, Markdown/JSON evidence report, pytest, ruff, mypy, GitHub branch protection 운영 문서.

---

## 검토한 컨텍스트

요청된 문서와 현재 구현 파일을 확인한 뒤 Sprint 5 범위를 정했다.

- `docs/superpowers/plans/2026-06-25-intent-routing-sprint-0.md`
- `docs/superpowers/plans/2026-06-26-intent-routing-sprint-1.md`
- `docs/superpowers/plans/2026-06-28-intent-routing-sprint-2.md`
- `docs/superpowers/plans/2026-06-28-intent-routing-sprint-3.md`
- `docs/superpowers/plans/2026-06-29-intent-routing-sprint-4.md`
- `docs/ops/ci-verification.md`
- `docs/ops/pilot-e2e-smoke.md`
- `docs/ops/closed-network-deployment.md`
- `docs/ops/security-operations.md`
- `docs/ops/security-lifecycle.md`
- `docs/ops/pilot-readiness-evidence.md`
- `docs/ops/bge-m3-closed-network.md`
- `docs/integrations/dify-branching-playbook.md`
- `docs/integrations/dify-handoff-checklist.md`
- `docs/integrations/dify-http-request-node.md`
- `docs/pilot/README.md`
- `README.md`

구현 상태 확인에 사용한 주요 파일:

- `.github/workflows/ci.yml`
- `compose.yaml`
- `scripts/run_pilot_e2e_smoke.py`
- `scripts/run_pilot_readiness.py`
- `scripts/run_dify_smoke_matrix.py`
- `scripts/run_csv_gate.py`
- `scripts/verify_bge_m3_package.py`
- `scripts/benchmark_bge_m3.py`
- `scripts/export_ops_evidence.py`
- `src/intent_routing/ops/quality_gate.py`
- `src/intent_routing/ops/smoke_matrix.py`
- `src/intent_routing/ops/readiness_report.py`
- `src/intent_routing/ops/evidence.py`
- `src/intent_routing/embedding/model_package.py`
- `src/intent_routing/testing/csv_runner.py`
- `src/intent_routing/testing/gate.py`

## 현재 구현 상태 관찰

- 현재 `main`은 Sprint 4 merge 후 `3dfc747649aebf2734410649b47074624de94d29`이며 worktree는 clean 상태다.
- Sprint 0은 API-only vertical slice를 구현했다. 핵심은 `/v1/intent-route`, admin API, release activation, pgvector exact search, threshold preset, CSV gate, PII masking, AES-256-GCM envelope encryption, trace/audit log다.
- Sprint 1은 deterministic pilot fixture, seed/smoke script, threshold comparison report, Dify HTTP mapping, trace/audit drill을 추가했다.
- Sprint 2는 closed-network Compose profile, `/readyz`, API key rotation, readiness evidence, Dify template/playbook, BGE-M3 benchmark, 30/50/100 CSV tier를 추가했다.
- Sprint 3은 raw-text KEK rewrap, raw-query retention, audit/metrics APIs, operations evidence export를 추가했다.
- Sprint 4는 GitHub Actions CI, locked install, pilot e2e smoke wrapper, Dify smoke matrix, BGE-M3 package preflight, Dify handoff checklist, CI artifact policy를 추가했다.
- 지금 남은 병목은 개별 도구의 부재가 아니라, 실제 파일럿 전날 운영자가 어떤 순서로 실행하고 어떤 파일을 묶어 승인 증적으로 제출해야 하는지 한 번에 검증하는 rehearsal layer가 없다는 점이다.
- CSV threshold report는 현재 실행 결과 비교에는 강하지만, 승인된 pilot baseline 대비 “새 FAIL/REVIEW가 생겼는지”를 별도 회귀 gate로 판단하지는 않는다.
- BGE-M3 package preflight와 benchmark는 각각 존재하지만, closed-network pilot rehearsal의 blocking 단계로 한 번에 묶이지 않았다.
- Dify smoke matrix는 API branch 검증을 자동화한다. 실제 Dify UI dry-run의 workflow version, secret masking, no-retry branch 확인은 checklist 수준에 머문다.
- Branch protection은 `docs/ops/ci-verification.md`에 한 줄로 언급되어 있지만, GitHub UI/CLI 적용 절차와 required check 이름을 운영 문서로 고정하지 않았다.

## Sprint 5 권장 방향

Sprint 5 목표는 **파일럿 운영 리허설과 폐쇄망 증적 패키지**로 잡는다. 새 routing feature, Admin UI, production IAM 확장보다 운영 리허설의 반복성과 증적 완결성이 더 급하다. Sprint 4가 CI와 개별 smoke를 만들었다면, Sprint 5는 그것들을 운영자가 실행할 하나의 rehearsal workflow로 묶고, CSV 기준선 회귀 비교와 Dify UI dry-run 절차, BGE package/benchmark blocking 증적, 보안 runbook rehearsal, branch protection 적용 절차를 확정한다.

## Sprint 5 범위

산출물:

- Pilot rehearsal wrapper: e2e smoke, Dify smoke matrix, CSV baseline comparison, ops evidence export, secret scan, optional Dify UI evidence metadata, BGE package/benchmark evidence를 하나의 manifest로 집계한다.
- Closed-network mode: 실제 BGE-M3 package preflight와 benchmark evidence가 없으면 pilot handoff를 PASS로 보지 않는다.
- CSV baseline regression: `docs/pilot/it-helpdesk-pilot-baseline.json`을 만들고, current threshold comparison report가 baseline 대비 새 FAIL/REVIEW 또는 risk regression을 만들면 non-zero로 종료한다.
- Dify HTTP Request node dry-run 절차: API smoke matrix와 실제 Dify UI workflow version/evidence를 연결하는 문서를 추가한다.
- Security and incident rehearsal: raw query decrypt exception, retention dry-run, KEK rewrap dry-run, API key rotation overlap 절차를 파일럿 리허설에서 어떤 증적으로 남길지 문서화한다. Sprint 5 wrapper는 destructive 보안 작업을 자동 실행하지 않는다.
- GitHub branch protection 문서화: `CI / verify` required check 적용 절차, artifact 검수, 예외 처리, rollback을 명확히 한다.
- README와 ops/integration 문서 링크 정리.

범위 제외:

- Admin UI 개발 없음.
- 라우팅 점수식, threshold preset 값, risk/off_topic 정책 변경 없음.
- HNSW, sparse retrieval, multi-vector retrieval, LLM judge 추가 없음.
- Dify plugin packaging 없음. HTTP Request node 연동만 강화한다.
- production IAM, OIDC, mTLS, HMAC signing, Kubernetes/OpenShift 구현 없음.
- GitHub-hosted CI에서 실제 BGE-M3 모델 다운로드/실행 없음.
- KEK rewrap execute, log retention execute, API key revoke 같은 destructive 운영 작업을 rehearsal wrapper가 자동 실행하지 않음.

## 계획 파일 구조

새로 만들 파일:

```text
docs/ops/pilot-rehearsal.md
docs/ops/branch-protection.md
docs/integrations/dify-dry-run-rehearsal.md
docs/pilot/it-helpdesk-pilot-baseline.json
src/intent_routing/ops/rehearsal.py
src/intent_routing/ops/csv_baseline.py
scripts/run_pilot_rehearsal.py
scripts/compare_csv_baseline.py
tests/unit/test_pilot_rehearsal.py
tests/unit/test_csv_baseline.py
tests/unit/test_pilot_rehearsal_docs_contract.py
tests/unit/test_branch_protection_docs_contract.py
tests/unit/test_dify_dry_run_docs_contract.py
tests/integration/test_pilot_rehearsal_flow.py
tests/integration/test_csv_baseline_flow.py
```

수정할 파일:

```text
README.md
docs/ops/ci-verification.md
docs/ops/pilot-e2e-smoke.md
docs/ops/closed-network-deployment.md
docs/ops/security-operations.md
docs/ops/security-lifecycle.md
docs/ops/pilot-readiness-evidence.md
docs/ops/bge-m3-closed-network.md
docs/ops/intent-routing-pilot-runbook.md
docs/integrations/dify-handoff-checklist.md
docs/integrations/dify-http-request-node.md
docs/integrations/dify-branching-playbook.md
docs/pilot/README.md
```

파일별 책임:

- `src/intent_routing/ops/rehearsal.py`: rehearsal step/result dataclass, manifest aggregation, JSON/Markdown rendering, evidence file allowlist, recursive secret scan policy.
- `scripts/run_pilot_rehearsal.py`: 기존 Sprint 4 script를 순서대로 호출하고 `pilot-rehearsal-manifest.json/md`를 생성한다.
- `src/intent_routing/ops/csv_baseline.py`: threshold comparison report와 baseline JSON의 case-level regression을 비교한다.
- `scripts/compare_csv_baseline.py`: baseline freeze/compare CLI를 제공한다.
- `docs/pilot/it-helpdesk-pilot-baseline.json`: standard 50-row pilot dataset의 승인 기준선이다. raw query를 저장하지 않고 `case_id`, preset, expected result/decision/intent/route_key, CSV sha256, gate policy만 저장한다.
- `docs/ops/pilot-rehearsal.md`: local rehearsal와 closed-network rehearsal의 실행 순서, output 해석, failure triage, secret scan 기준을 설명한다.
- `docs/integrations/dify-dry-run-rehearsal.md`: 실제 Dify UI dry-run 절차, workflow version 기록, screenshot/export evidence 보관, no-retry 확인을 설명한다.
- `docs/ops/branch-protection.md`: GitHub branch protection에서 `CI / verify` required check를 적용하고 예외를 처리하는 절차를 설명한다.

## 작업 1: Rehearsal Manifest와 Secret Scan 기반

**파일:**

- 생성: `src/intent_routing/ops/rehearsal.py`
- 생성: `tests/unit/test_pilot_rehearsal.py`

- [ ] **Step 1: 실패하는 unit test 작성**

`tests/unit/test_pilot_rehearsal.py`에 아래 동작을 검증한다.

```text
test_manifest_fails_when_required_step_fails
test_manifest_passes_when_required_steps_pass_and_optional_step_skips
test_manifest_json_and_markdown_are_secret_safe
test_secret_scan_blocks_secret_state_and_raw_token_markers
test_secret_scan_allows_redacted_evidence_fields
```

기대 실패:

- `ModuleNotFoundError: No module named 'intent_routing.ops.rehearsal'`

- [ ] **Step 2: test 실행으로 실패 확인**

```bash
uv run pytest tests/unit/test_pilot_rehearsal.py -q
```

Expected: 위 import 실패 또는 정의되지 않은 symbol 실패.

- [ ] **Step 3: 최소 구현 작성**

`src/intent_routing/ops/rehearsal.py`에 아래 public contract를 만든다.

```text
EvidenceFile(path, kind, required, secret_safe)
RehearsalStep(name, status, required, summary, evidence_files, error_message)
SecretScanFinding(path, marker, line_number)
SecretScanResult(passed, findings)
RehearsalManifest(service_id, environment, mode, required_preset, started_at, completed_at, steps, secret_scan)
render_rehearsal_json(manifest) -> str
render_rehearsal_markdown(manifest) -> str
scan_evidence_directory(root: Path) -> SecretScanResult
manifest_passed(manifest) -> bool
```

Status 값은 `pass`, `fail`, `skip`만 허용한다. Required step이 `fail`이면 manifest는 FAIL이다. Optional step의 `skip`은 manifest 실패가 아니다. Secret scan은 아래 marker를 차단한다.

```text
.secret.json
Authorization: Bearer
Bearer 
RAW_TEXT_KEK_BASE64
RAW_TEXT_LEGACY_KEKS_JSON
api_key=
intent_routing_api_key
query_raw
text_raw
encrypted_dek
ciphertext
irt_live_
irt_secret
```

단, 값이 정확히 `REDACTED`인 JSON/Markdown 필드는 허용한다.

- [ ] **Step 4: unit test 통과 확인**

```bash
uv run pytest tests/unit/test_pilot_rehearsal.py -q
```

Expected: PASS.

- [ ] **Step 5: commit**

```bash
git add src/intent_routing/ops/rehearsal.py tests/unit/test_pilot_rehearsal.py
git commit -m "feat: add pilot rehearsal manifest primitives"
```

## 작업 2: Pilot Rehearsal Wrapper

**파일:**

- 생성: `scripts/run_pilot_rehearsal.py`
- 생성: `tests/integration/test_pilot_rehearsal_flow.py`
- 수정: `README.md`
- 수정: `docs/ops/pilot-e2e-smoke.md`
- 수정: `docs/ops/pilot-readiness-evidence.md`

- [ ] **Step 1: 실패하는 integration test 작성**

`tests/integration/test_pilot_rehearsal_flow.py`에서 FastAPI `TestClient`와 fake embedding을 사용한다. 기존 `test_pilot_e2e_smoke_flow.py`와 같은 dependency override pattern을 재사용한다.

검증 항목:

- local mode에서 `run_pilot_rehearsal()`은 pilot e2e smoke, Dify smoke matrix, ops evidence export, secret scan을 실행한다.
- CSV baseline step은 Task 3에서 regression module이 추가되기 전까지 `skip`으로 기록된다.
- `pilot-rehearsal-manifest.json`과 `pilot-rehearsal-manifest.md`가 생성된다.
- manifest의 required step이 모두 PASS이고 local-only BGE step은 `skip`으로 기록된다.
- evidence text에 `.secret.json`, raw API key, `Bearer `, `query_raw`, `encrypted_dek`, `ciphertext`, 대표 raw query 문구가 없다.

기대 실패:

- `ModuleNotFoundError: No module named 'scripts.run_pilot_rehearsal'`

- [ ] **Step 2: test 실행으로 실패 확인**

```bash
uv run pytest tests/integration/test_pilot_rehearsal_flow.py -q
```

Expected: import 실패.

- [ ] **Step 3: CLI와 orchestration 구현**

`scripts/run_pilot_rehearsal.py`에 `run_pilot_rehearsal()`와 CLI `main()`을 만든다.

필수 CLI:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --environment "${INTENT_ROUTING_ENVIRONMENT}" \
  --state-path "${STATE_PATH}" \
  --csv-tier standard \
  --required-preset balanced \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Closed-network CLI:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8000 \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --environment pilot \
  --state-path "${STATE_PATH}" \
  --csv-tier standard \
  --required-preset balanced \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 "${BGE_M3_MODEL_SHA256}" \
  --run-bge-benchmark \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Step order:

1. `closed-network` mode에서는 `scripts.verify_bge_m3_package.verify_bge_m3_package()`를 먼저 실행한다.
2. `closed-network --run-bge-benchmark`가 있으면 `scripts.benchmark_bge_m3.benchmark_bge_m3()`를 실행한다.
3. `scripts.run_pilot_e2e_smoke.run_pilot_e2e_smoke()`를 실행한다.
4. 생성된 `STATE_PATH`를 읽고 `scripts.run_dify_smoke_matrix.run_dify_smoke_matrix()`를 실행한다.
5. CSV baseline step은 `skip`으로 기록한다. Task 3에서 `scripts.compare_csv_baseline.compare_csv_baseline()` 호출로 교체한다.
6. `scripts.export_ops_evidence.run_ops_evidence_export()`를 실행한다.
7. rehearsal evidence directory 전체를 secret scan한다.
8. `pilot-rehearsal-manifest.json`과 `pilot-rehearsal-manifest.md`를 쓴다.

Exit code 규칙:

- required step 실패 또는 secret scan 실패: `SystemExit(1)`.
- local mode에서 BGE step skip: `0`.
- closed-network mode에서 `--bge-model-path` 누락: `SystemExit(2)`.
- closed-network mode에서 benchmark 누락: `SystemExit(2)`.

- [ ] **Step 4: integration test 통과 확인**

```bash
uv run pytest tests/integration/test_pilot_rehearsal_flow.py -q
```

Expected: PASS.

- [ ] **Step 5: README와 기존 smoke 문서에 rehearsal 진입점 추가**

`README.md`, `docs/ops/pilot-e2e-smoke.md`, `docs/ops/pilot-readiness-evidence.md`에 Sprint 5 기본 실행 경로를 추가한다. 기존 Sprint 4 e2e smoke는 lower-level diagnostic으로 남긴다.

- [ ] **Step 6: 관련 test 실행**

```bash
uv run pytest tests/integration/test_pilot_rehearsal_flow.py tests/unit/test_pilot_rehearsal.py -q
```

Expected: PASS.

- [ ] **Step 7: commit**

```bash
git add scripts/run_pilot_rehearsal.py tests/integration/test_pilot_rehearsal_flow.py README.md docs/ops/pilot-e2e-smoke.md docs/ops/pilot-readiness-evidence.md
git commit -m "feat: add pilot rehearsal wrapper"
```

## 작업 3: CSV Baseline Regression Gate

**파일:**

- 생성: `src/intent_routing/ops/csv_baseline.py`
- 생성: `scripts/compare_csv_baseline.py`
- 생성: `docs/pilot/it-helpdesk-pilot-baseline.json`
- 생성: `tests/unit/test_csv_baseline.py`
- 생성: `tests/integration/test_csv_baseline_flow.py`
- 수정: `scripts/run_pilot_rehearsal.py`
- 수정: `tests/integration/test_pilot_rehearsal_flow.py`
- 수정: `docs/pilot/README.md`

- [ ] **Step 1: 실패하는 unit test 작성**

`tests/unit/test_csv_baseline.py`에 아래 동작을 검증한다.

```text
test_baseline_compare_passes_when_case_results_match
test_baseline_compare_fails_on_new_fail_case
test_baseline_compare_fails_on_new_review_case_when_disallowed
test_baseline_compare_fails_on_risk_pass_rate_regression
test_baseline_renderer_excludes_query_text_and_secret_fields
```

기대 실패:

- `ModuleNotFoundError: No module named 'intent_routing.ops.csv_baseline'`

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/unit/test_csv_baseline.py -q
```

Expected: import 실패.

- [ ] **Step 3: baseline module 구현**

`src/intent_routing/ops/csv_baseline.py` public contract:

```text
CsvBaselinePolicy(baseline_id, csv_path, csv_sha256, required_preset, minimum_pass_rate, required_risk_pass_rate, allowed_new_failures, allowed_new_reviews)
CsvCaseExpectation(case_id, preset, expected_result, expected_decision, expected_intent, expected_route_key)
CsvBaselineComparison(passed, block_reasons, new_failures, new_reviews, changed_decisions, changed_intents, changed_route_keys)
freeze_baseline(threshold_report, csv_path, preset) -> dict
compare_baseline(threshold_report, baseline) -> CsvBaselineComparison
render_baseline_comparison_json(result) -> str
render_baseline_comparison_markdown(result) -> str
```

Comparison rule:

- `required_preset`의 current `pass_rate`가 `minimum_pass_rate` 미만이면 FAIL.
- current `risk_pass_rate`가 `required_risk_pass_rate` 미만이면 FAIL.
- baseline에서 PASS였던 case가 FAIL이면 new failure다.
- baseline에서 PASS였던 case가 REVIEW가 되고 `allowed_new_reviews=0`이면 FAIL.
- expected decision, intent, route_key가 baseline과 달라지면 regression table에 기록한다.
- raw query, API key, bearer header, encrypted field는 baseline과 comparison report에 저장하지 않는다.

- [ ] **Step 4: CLI 구현**

`scripts/compare_csv_baseline.py`는 두 subcommand를 제공한다.

Freeze command:

```bash
uv run python scripts/compare_csv_baseline.py freeze \
  --threshold-report "var/evidence/${SERVICE_ID}/e2e/${SERVICE_ID}-threshold-comparison.json" \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --preset balanced \
  --baseline-id it-helpdesk-pilot-standard-20260629 \
  --out docs/pilot/it-helpdesk-pilot-baseline.json
```

Compare command:

```bash
uv run python scripts/compare_csv_baseline.py compare \
  --threshold-report "var/evidence/${SERVICE_ID}/e2e/${SERVICE_ID}-threshold-comparison.json" \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal/csv-baseline"
```

Compare가 실패하면 JSON/Markdown report를 쓴 뒤 non-zero로 종료한다.

- [ ] **Step 5: 초기 baseline 파일 생성**

Sprint 5 구현 중 한 번 fresh DB local rehearsal을 통과시킨 뒤 freeze command로 `docs/pilot/it-helpdesk-pilot-baseline.json`을 생성한다. baseline에는 `query` 필드를 넣지 않는다. `csv_sha256`은 `docs/pilot/it-helpdesk-pilot-cases.csv` 내용으로 계산한다.

- [ ] **Step 6: integration flow 작성**

`tests/integration/test_csv_baseline_flow.py`에서 seed, threshold comparison, baseline freeze, compare PASS를 검증한다. 별도 synthetic report로 compare FAIL도 검증한다.

- [ ] **Step 7: rehearsal wrapper에 baseline 연동 추가**

`scripts/run_pilot_rehearsal.py`에 아래 optional argument를 추가한다.

```text
--baseline <path>
```

`--baseline`이 주어지면 `scripts.compare_csv_baseline.compare_csv_baseline()`을 실행하고, 결과를 `var/evidence/${SERVICE_ID}/rehearsal/csv-baseline` 아래에 기록한다. Baseline compare가 실패하면 manifest에는 `csv-baseline` step을 FAIL로 남기고 CLI는 non-zero로 종료한다. `--baseline`이 없으면 local diagnostic run을 위해 `csv-baseline` step은 optional `skip`으로 남긴다.

`tests/integration/test_pilot_rehearsal_flow.py`를 업데이트해 `--baseline docs/pilot/it-helpdesk-pilot-baseline.json` 또는 생성된 임시 baseline을 넘겼을 때 `csv-baseline` step이 PASS인지 검증한다.

- [ ] **Step 8: test 실행**

```bash
uv run pytest tests/unit/test_csv_baseline.py tests/integration/test_csv_baseline_flow.py tests/integration/test_pilot_rehearsal_flow.py -q
```

Expected: PASS.

- [ ] **Step 9: docs 업데이트**

`docs/pilot/README.md`에 baseline 파일의 의미, refresh 조건, PR review 원칙을 추가한다.

- [ ] **Step 10: commit**

```bash
git add src/intent_routing/ops/csv_baseline.py scripts/compare_csv_baseline.py docs/pilot/it-helpdesk-pilot-baseline.json tests/unit/test_csv_baseline.py tests/integration/test_csv_baseline_flow.py scripts/run_pilot_rehearsal.py tests/integration/test_pilot_rehearsal_flow.py docs/pilot/README.md
git commit -m "feat: add pilot CSV baseline regression gate"
```

## 작업 4: Dify Dry-Run Rehearsal 문서와 Metadata 연결

**파일:**

- 생성: `docs/integrations/dify-dry-run-rehearsal.md`
- 생성: `tests/unit/test_dify_dry_run_docs_contract.py`
- 수정: `scripts/run_pilot_rehearsal.py`
- 수정: `src/intent_routing/ops/rehearsal.py`
- 수정: `docs/integrations/dify-handoff-checklist.md`
- 수정: `docs/integrations/dify-http-request-node.md`
- 수정: `docs/integrations/dify-branching-playbook.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_dify_dry_run_docs_contract.py`가 아래 문자열과 절차를 검증하게 한다.

```text
Dify workflow version identifier
intent_routing_api_key secret variable
workflow_run_id
Timeout: 8 seconds
no automatic retry loop
dify-smoke-matrix.json
dify-smoke-matrix.md
pilot-rehearsal-manifest.md
confident
clarify
fallback
off_topic
risk
unauthorized
401
403
422
408
5xx
timeout
trace_id
request_id
release_version
```

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py -q
```

Expected: missing document 실패.

- [ ] **Step 3: Dify dry-run 문서 작성**

`docs/integrations/dify-dry-run-rehearsal.md`에 아래 실행 절차를 쓴다.

1. Sprint 5 rehearsal wrapper 실행 전 `SERVICE_ID`, `STATE_PATH`, target URL을 확정한다.
2. Dify HTTP Request node에 `docs/integrations/dify-http-request-node-template.json` 값을 반영한다.
3. Secret variable `intent_routing_api_key`와 `intent_routing_key_id`가 UI에서 마스킹되는지 확인한다.
4. `X-Request-Id`가 `workflow_run_id`에 매핑되는지 확인한다.
5. API smoke matrix 결과 `dify-smoke-matrix.md`를 확인한다.
6. 실제 Dify UI에서 representative query 5개를 dry-run한다: confident, clarify, fallback, off_topic, risk.
7. `401`, `403`, `422`, `408`, `5xx`, timeout branch는 API matrix와 UI branch 설정으로 검수한다.
8. workflow version identifier 또는 export identifier를 기록한다.
9. screenshot/export 파일을 남긴 경우 secret value가 보이지 않는지 확인한다.
10. evidence bundle에 `dify-smoke-matrix.md`, workflow version identifier, `pilot-rehearsal-manifest.md`를 첨부한다.

- [ ] **Step 4: rehearsal manifest metadata 확장**

`scripts/run_pilot_rehearsal.py`에 아래 optional argument를 추가한다.

```text
--dify-workflow-version <string>
--dify-ui-evidence-path <path>
```

`--dify-ui-evidence-path`가 주어지면 파일이 존재해야 하고, secret scan 대상에 포함한다. manifest에는 path와 workflow version identifier만 기록한다. raw screenshot 내용을 Markdown에 inline하지 않는다.

- [ ] **Step 5: integration/docs test 실행**

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py tests/integration/test_pilot_rehearsal_flow.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/integrations/dify-dry-run-rehearsal.md tests/unit/test_dify_dry_run_docs_contract.py scripts/run_pilot_rehearsal.py src/intent_routing/ops/rehearsal.py docs/integrations/dify-handoff-checklist.md docs/integrations/dify-http-request-node.md docs/integrations/dify-branching-playbook.md
git commit -m "docs: add Dify dry-run rehearsal workflow"
```

## 작업 5: 보안 운영과 장애 대응 Rehearsal Runbook

**파일:**

- 생성: `docs/ops/pilot-rehearsal.md`
- 생성: `tests/unit/test_pilot_rehearsal_docs_contract.py`
- 수정: `docs/ops/security-operations.md`
- 수정: `docs/ops/security-lifecycle.md`
- 수정: `docs/ops/closed-network-deployment.md`
- 수정: `docs/ops/bge-m3-closed-network.md`
- 수정: `docs/ops/intent-routing-pilot-runbook.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_pilot_rehearsal_docs_contract.py`에서 아래 내용이 문서에 있는지 검증한다.

```text
run_pilot_rehearsal.py
pilot-rehearsal-manifest.json
pilot-rehearsal-manifest.md
local mode
closed-network mode
verify_bge_m3_package.py
benchmark_bge_m3.py
run_pilot_e2e_smoke.py
run_dify_smoke_matrix.py
compare_csv_baseline.py
export_ops_evidence.py
secret scan
raw query decrypt exception
KEK rewrap dry-run
runtime raw-query retention dry-run
API key rotation overlap
incident fallback
no destructive security operation is executed by the wrapper
```

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/unit/test_pilot_rehearsal_docs_contract.py -q
```

Expected: missing document 실패.

- [ ] **Step 3: `docs/ops/pilot-rehearsal.md` 작성**

문서에 아래 섹션을 포함한다.

- 목적과 범위: 파일럿 전 rehearsal evidence bundle 생성.
- Local rehearsal command: fake embedding, `--mode local`, baseline compare 포함.
- Closed-network rehearsal command: `--mode closed-network`, BGE package preflight, BGE benchmark 필수.
- Evidence bundle layout:

```text
var/evidence/${SERVICE_ID}/rehearsal/
  pilot-rehearsal-manifest.json
  pilot-rehearsal-manifest.md
  e2e/
  dify/
  csv-baseline/
  ops/
  bge/
```

- Secret scan policy: `.secret.json`, raw API key, bearer token, KEK, raw query, encrypted DEK/ciphertext는 evidence bundle에 없어야 한다.
- Security rehearsal:
  - API key rotation overlap은 `scripts/rotate_api_key.py`를 별도 승인으로 실행한다.
  - raw query decrypt exception은 approval ID와 reason을 요구하고 raw text를 출력하지 않는다.
  - KEK rewrap은 Sprint 5 rehearsal에서 dry-run만 수행한다.
  - runtime raw-query retention은 Sprint 5 rehearsal에서 dry-run만 수행한다.
- Incident rehearsal:
  - wrong key, wrong service, invalid body, 5xx/timeout fallback path를 Dify handoff evidence로 남긴다.
  - 장애 ticket에는 `trace_id`, `request_id`, `service_id`, `release_version`, Dify workflow version을 기록한다.
- Failure triage table: BGE checksum mismatch, benchmark memory/latency failure, balanced gate failure, baseline regression, Dify branch mismatch, ops evidence export failure, secret scan failure.

- [ ] **Step 4: 기존 runbook 링크 정리**

`closed-network-deployment`, `security-operations`, `security-lifecycle`, `bge-m3-closed-network`, `intent-routing-pilot-runbook`에서 Sprint 5 rehearsal 문서를 상위 실행 경로로 링크한다. 기존 low-level command는 장애 진단용으로 유지한다.

- [ ] **Step 5: docs contract test 통과**

```bash
uv run pytest tests/unit/test_pilot_rehearsal_docs_contract.py tests/unit/test_security_lifecycle_docs_contract.py tests/unit/test_security_ops_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/ops/pilot-rehearsal.md tests/unit/test_pilot_rehearsal_docs_contract.py docs/ops/security-operations.md docs/ops/security-lifecycle.md docs/ops/closed-network-deployment.md docs/ops/bge-m3-closed-network.md docs/ops/intent-routing-pilot-runbook.md
git commit -m "docs: define pilot rehearsal operations runbook"
```

## 작업 6: Branch Protection과 Required Check 운영 문서

**파일:**

- 생성: `docs/ops/branch-protection.md`
- 생성: `tests/unit/test_branch_protection_docs_contract.py`
- 수정: `docs/ops/ci-verification.md`
- 수정: `README.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_branch_protection_docs_contract.py`에서 아래 내용을 검증한다.

```text
CI / verify
Require status checks to pass before merging
Require branches to be up to date before merging
main
pull_request
workflow_dispatch
pilot-e2e-evidence
14 days
branch protection rollback
temporary bypass approval
no .secret.json
```

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/unit/test_branch_protection_docs_contract.py -q
```

Expected: missing document 실패.

- [ ] **Step 3: branch protection 문서 작성**

`docs/ops/branch-protection.md`에 두 경로를 모두 기록한다.

GitHub UI:

1. Repository Settings로 이동한다.
2. Branches에서 `main` protection rule을 만든다.
3. `Require status checks to pass before merging`를 켠다.
4. required check에 `CI / verify`를 선택한다.
5. `Require branches to be up to date before merging`를 켠다.
6. 저장 후 테스트 PR에서 required check가 merge를 막는지 확인한다.

GitHub CLI/API 참고 절차:

```bash
gh api \
  --method PUT \
  repos/HauaM/AiIntentRouting/branches/main/protection \
  --input branch-protection-payload.json
```

문서에는 실제 token이나 secret을 넣지 않는다. CLI payload는 예시로 두되 required status check context는 `CI / verify`로 고정한다.

Rollback:

- CI가 infrastructure issue로 막히면 temporary bypass approval ID를 기록한다.
- bypass 후에는 `workflow_dispatch`로 같은 commit의 `CI / verify`를 재실행한다.
- failure artifact에서 `.secret.json`이 없는지 확인한다.

- [ ] **Step 4: CI 문서 링크**

`docs/ops/ci-verification.md`와 `README.md`에서 branch protection 문서를 링크한다.

- [ ] **Step 5: docs test 통과**

```bash
uv run pytest tests/unit/test_branch_protection_docs_contract.py tests/unit/test_ci_workflow_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/ops/branch-protection.md tests/unit/test_branch_protection_docs_contract.py docs/ops/ci-verification.md README.md
git commit -m "docs: document required CI branch protection"
```

## 작업 7: 최종 통합 검증과 문서 링크 정리

**파일:**

- 수정: `README.md`
- 수정: `docs/ops/closed-network-deployment.md`
- 수정: `docs/ops/pilot-readiness-evidence.md`
- 수정: `docs/ops/pilot-e2e-smoke.md`
- 수정: `docs/ops/bge-m3-closed-network.md`
- 수정: `docs/integrations/dify-handoff-checklist.md`
- 수정: `docs/pilot/README.md`

- [ ] **Step 1: 문서 링크 audit**

아래 문서에서 Sprint 5 rehearsal을 상위 경로로 안내하고, 기존 script는 lower-level diagnostic으로 설명한다.

```text
README.md
docs/ops/closed-network-deployment.md
docs/ops/pilot-readiness-evidence.md
docs/ops/pilot-e2e-smoke.md
docs/ops/bge-m3-closed-network.md
docs/integrations/dify-handoff-checklist.md
docs/pilot/README.md
```

- [ ] **Step 2: 전체 unit/docs contract test 실행**

```bash
uv run pytest tests/unit/test_pilot_rehearsal.py tests/unit/test_csv_baseline.py tests/unit/test_pilot_rehearsal_docs_contract.py tests/unit/test_branch_protection_docs_contract.py tests/unit/test_dify_dry_run_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 3: 전체 integration rehearsal test 실행**

```bash
uv run pytest tests/integration/test_pilot_rehearsal_flow.py tests/integration/test_csv_baseline_flow.py -q
```

Expected: PASS.

- [ ] **Step 4: 품질 검증**

```bash
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
uv run pytest -q
```

Expected: ruff PASS, mypy PASS, Compose config PASS, pytest 전체 PASS.

- [ ] **Step 5: fresh DB manual smoke**

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

다른 shell에서:

```bash
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --environment "${INTENT_ROUTING_ENVIRONMENT}" \
  --state-path "${STATE_PATH}" \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Expected:

- `pilot-rehearsal-manifest.md` final status가 PASS.
- `pilot-e2e-smoke-index.md` quality gate가 PASS.
- `dify-smoke-matrix.md` final status가 PASS.
- `csv-baseline` report가 PASS.
- `ops-evidence.md`가 생성됨.
- secret scan 결과가 PASS.

- [ ] **Step 6: final commit**

```bash
git add README.md docs/ops/closed-network-deployment.md docs/ops/pilot-readiness-evidence.md docs/ops/pilot-e2e-smoke.md docs/ops/bge-m3-closed-network.md docs/integrations/dify-handoff-checklist.md docs/pilot/README.md
git commit -m "docs: link Sprint 5 rehearsal workflow"
```

## 테스트 전략

Unit tests:

- Rehearsal manifest PASS/FAIL/SKIP aggregation.
- Secret scan policy와 false positive 허용 규칙.
- CSV baseline freeze/compare, new FAIL/REVIEW/risk regression 판정.
- JSON/Markdown renderer가 secret-looking substring을 제거하는지 확인.
- Dify dry-run, branch protection, pilot rehearsal docs contract.

Integration tests:

- FastAPI `TestClient` 기반 local rehearsal flow.
- Seed, threshold comparison, baseline freeze/compare 통합 flow.
- Existing Sprint 4 e2e smoke와 Dify smoke matrix flow 회귀.
- Ops evidence export secret redaction 회귀.

Manual tests:

- Fresh DB local rehearsal.
- Closed-network host에서 BGE package preflight와 benchmark를 포함한 rehearsal.
- 실제 Dify UI dry-run과 workflow version evidence 기록.
- Evidence bundle secret scan.
- GitHub branch protection required check 적용 검수.

최종 필수 명령:

```bash
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
uv run pytest -q
```

## 인수 기준

- `scripts/run_pilot_rehearsal.py`가 local mode에서 fresh service를 seed하고 e2e smoke, Dify matrix, CSV baseline comparison, ops evidence export, secret scan을 하나의 manifest로 묶는다.
- `closed-network` mode는 BGE-M3 package preflight와 benchmark evidence가 없으면 PASS가 될 수 없다.
- `pilot-rehearsal-manifest.json`과 `pilot-rehearsal-manifest.md`가 각 step의 status, evidence file path, required 여부, failure reason을 보여준다.
- Manifest와 모든 rehearsal evidence에는 `.secret.json`, raw API key, bearer token, KEK material, raw query, encrypted DEK, ciphertext가 없다.
- `docs/pilot/it-helpdesk-pilot-baseline.json`은 raw query 없이 case-level 기준선을 저장한다.
- CSV baseline comparison은 새 FAIL, 허용되지 않은 새 REVIEW, risk pass rate regression, decision/intent/route_key drift를 blocking 또는 review evidence로 기록한다.
- Dify dry-run 문서는 API smoke matrix와 실제 Dify UI workflow version/evidence를 연결한다.
- 보안 runbook은 raw query decrypt exception, KEK rewrap dry-run, retention dry-run, API key rotation overlap, incident fallback evidence를 설명한다.
- Branch protection 문서는 `CI / verify` required check 적용, artifact 검수, temporary bypass, rollback 절차를 포함한다.
- README와 ops/integration docs에서 Sprint 5 rehearsal 문서가 상위 실행 경로로 링크된다.
- `uv run ruff check .`, `uv run mypy src tests`, `docker compose --profile runtime config`, `uv run pytest -q`가 통과한다.

## 수동 검수 절차

1. GitHub branch protection에서 `main`에 `CI / verify` required check가 설정되어 있는지 확인한다.
2. Fresh DB local run에서 `run_pilot_rehearsal.py --mode local`을 실행한다.
3. `pilot-rehearsal-manifest.md` final status가 PASS인지 확인한다.
4. Evidence bundle에서 아래 명령을 실행한다.

   ```bash
   grep -R -n -E 'Bearer[[:space:]]+|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|\\.secret\\.json' \
     var/evidence/${SERVICE_ID}/rehearsal
   ```

   Expected: `REDACTED`로 명시된 안전 필드를 제외하고 공유 가능한 evidence에 match가 없어야 한다.

5. `csv-baseline` Markdown에서 new failure와 risk regression이 없는지 확인한다.
6. `dify-smoke-matrix.md`에서 confident, clarify, fallback, off_topic, risk, 401, 403, 422 case가 PASS인지 확인한다.
7. 실제 Dify UI에서 workflow version identifier를 기록하고 `docs/integrations/dify-dry-run-rehearsal.md` checklist를 완료한다.
8. 폐쇄망 host에서 `run_pilot_rehearsal.py --mode closed-network --bge-model-path /models/bge-m3 --run-bge-benchmark`를 실행한다.
9. BGE package SHA-256, benchmark `dimension=1024`, `max_tokens=256`, p50/p95 latency, max RSS를 evidence bundle에 첨부한다.
10. `ops-evidence.md`에서 readyz, active release, runtime metrics, raw-text key summary, audit evidence가 포함되어 있고 secret redaction statement가 있는지 확인한다.
11. Security dry-run 절차를 별도 승인 ID로 리허설한다. KEK rewrap과 retention은 dry-run report만 생성하고 execute하지 않는다.
12. Pilot handoff ticket 또는 release folder에 `pilot-rehearsal-manifest.md`, `dify-smoke-matrix.md`, threshold comparison Markdown, CSV baseline Markdown, `ops-evidence.md`, BGE package/benchmark report, Dify workflow version identifier를 첨부한다.

## 제품 책임자 정책/범위 결정사항

- **Closed-network BGE gate:** closed-network rehearsal에서 BGE package preflight와 benchmark를 둘 다 blocking gate로 둘지 결정해야 한다. 추천은 둘 다 blocking이다.
- **CSV baseline refresh 권한:** `docs/pilot/it-helpdesk-pilot-baseline.json` 변경을 일반 개발 PR로 허용할지, 제품 책임자 또는 pilot owner 승인 필수로 둘지 결정해야 한다. 추천은 pilot owner 승인 필수다.
- **Dify UI evidence 형식:** workflow version identifier만 필수로 할지, screenshot/export file도 필수로 할지 결정해야 한다. 추천은 workflow version identifier 필수, screenshot/export file은 조직 보안 정책이 허용할 때만 첨부다.
- **보안 rehearsal 범위:** Sprint 5에서 KEK rewrap execute, retention execute, API key revoke까지 포함할지 결정해야 한다. 추천은 destructive 작업은 제외하고 dry-run과 overlap smoke만 포함한다.
- **Evidence 보관 기간:** GitHub artifact는 Sprint 4 기준 14일이다. 파일럿 승인 evidence는 내부 release folder에서 30일 이상 보관할지 결정해야 한다. 추천은 내부 감사 요구가 없으면 30일이다.
- **Branch protection 적용 시점:** Sprint 4에서 이미 `CI / verify`를 required로 걸기로 한 흐름이므로 Sprint 5에서는 적용 절차 문서화와 검수만 수행한다. 아직 적용하지 않았다면 Sprint 5 시작 전에 적용하는 것을 추천한다.

## 권장 실행 방식

추천 실행 방식은 **Subagent-Driven**이다. 작업 1/2는 rehearsal wrapper와 manifest, 작업 3은 CSV baseline, 작업 4는 Dify dry-run, 작업 5는 보안/운영 문서, 작업 6은 branch protection 문서로 파일 범위가 비교적 독립적이다. 각 작업을 fresh subagent가 구현하고 main agent가 통합 검증하면, 긴 문서와 CLI 변경이 섞일 때 발생하는 회귀를 더 빨리 잡을 수 있다. Inline Execution도 가능하지만 Sprint 5는 증적 orchestration, baseline, 문서 contract가 동시에 움직이므로 Subagent-Driven이 더 적합하다.
