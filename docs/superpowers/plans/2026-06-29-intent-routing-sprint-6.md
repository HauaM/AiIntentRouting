# Sprint 6: 파일럿 전 실제 운영 리허설과 증적 확정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 5에서 만든 리허설 도구와 운영 문서를 파일럿 승인 직전에 실제로 제출 가능한 증적 패키지, 정책, handoff/release ticket 기준으로 확정한다.

**Architecture:** 라우팅 엔진, threshold preset, API 계약, 보안 lifecycle 동작은 변경하지 않는다. Sprint 6는 기존 `scripts/run_pilot_rehearsal.py`, BGE package/benchmark 도구, Dify smoke matrix, CSV baseline gate를 그대로 사용하고, 운영자가 빈칸 없이 실행/검수/승인할 수 있도록 문서 템플릿과 docs contract test를 추가한다. 생성된 evidence bundle은 `var/evidence/...` 아래에 두고 git에는 커밋하지 않는다.

**Tech Stack:** Python 3.12, FastAPI runtime, PostgreSQL 16 + pgvector, Docker Compose, existing rehearsal scripts, Markdown/JSON evidence, pytest docs contract tests, ruff, mypy.

---

## 검토한 현재 상태

- 현재 브랜치: `codex/intent-routing-sprint-6`, 원격 추적: `origin/codex/intent-routing-sprint-6`.
- 현재 `main` merge commit: `162b8d6814d840268f4090d6068e3ae47158998c`.
- worktree의 기존 untracked 항목은 `docs/AdminUI_Handbook/`뿐이며 Sprint 6에서 건드리지 않는다.
- README는 Sprint 5 local rehearsal command를 최상위 quick start로 안내한다.
- Sprint 5 산출물은 다음을 제공한다.
  - `scripts/run_pilot_rehearsal.py`: local/closed-network rehearsal wrapper.
  - `src/intent_routing/ops/rehearsal.py`: manifest, markdown/json renderer, evidence secret scan.
  - `src/intent_routing/ops/csv_baseline.py`와 `scripts/compare_csv_baseline.py`: baseline freeze/compare.
  - `docs/pilot/it-helpdesk-pilot-baseline.json`: standard 50-row, `balanced` preset 기준선.
  - `docs/ops/pilot-rehearsal.md`: local/closed-network rehearsal runbook.
  - `docs/integrations/dify-dry-run-rehearsal.md`: Dify UI dry-run 절차.
  - `docs/ops/branch-protection.md`: `CI / verify` required check 적용/rollback 절차.
- 현재 테스트는 rehearsal manifest, CSV baseline drift, Dify dry-run 문서, branch protection 문서, closed-network packaging 계약을 고정한다.

## Sprint 6 범위

포함:

- 실제 local rehearsal evidence bundle 생성과 검수 절차를 운영 체크리스트로 확정한다.
- Dify UI dry-run evidence record 양식과 필수 branch 검수 항목을 확정한다.
- closed-network/BGE package benchmark는 실측 절차와, 실측 host가 아직 없을 때의 blocking evidence template을 확정한다.
- branch protection 적용/rollback 증적 양식을 확정한다.
- CSV baseline refresh 승인 정책을 문서화한다.
- pilot handoff/release ticket template을 만든다.
- 모든 신규 운영 문서는 docs contract test로 최소 필수 문구와 링크를 고정한다.

제외:

- Admin UI 개발과 `docs/AdminUI_Handbook/` 수정.
- routing score, threshold preset, risk/off_topic policy 변경.
- Dify plugin packaging, Dify workflow 자동 생성.
- production IAM, OIDC, mTLS, HMAC signing, Kubernetes/OpenShift 구현.
- KEK rewrap execute, retention execute, API key revoke 같은 destructive 운영 동작 자동화.
- 실제 BGE-M3 모델 파일을 GitHub CI에서 다운로드하거나 실행하는 작업.

## 파일 범위

새로 만들 파일:

```text
docs/ops/pilot-evidence-bundle-checklist.md
docs/ops/bge-m3-evidence-template.md
docs/ops/branch-protection-evidence-template.md
docs/ops/pilot-handoff-release-ticket-template.md
docs/integrations/dify-dry-run-evidence-template.md
docs/pilot/csv-baseline-refresh-policy.md
tests/unit/test_pilot_evidence_bundle_docs_contract.py
tests/unit/test_bge_evidence_template_docs_contract.py
tests/unit/test_branch_protection_evidence_template_docs_contract.py
tests/unit/test_csv_baseline_refresh_policy_docs_contract.py
tests/unit/test_pilot_handoff_release_template_docs_contract.py
```

수정할 파일:

```text
README.md
docs/ops/pilot-rehearsal.md
docs/ops/bge-m3-closed-network.md
docs/ops/closed-network-deployment.md
docs/ops/branch-protection.md
docs/ops/ci-verification.md
docs/ops/intent-routing-pilot-runbook.md
docs/ops/pilot-readiness-evidence.md
docs/integrations/dify-dry-run-rehearsal.md
docs/integrations/dify-handoff-checklist.md
docs/integrations/dify-http-request-node.md
docs/integrations/dify-branching-playbook.md
docs/pilot/README.md
```

원칙:

- `var/evidence/...`, `var/pilot/*.secret.json`, 실제 screenshot/export 파일은 커밋하지 않는다.
- 문서 템플릿에는 secret, raw query, bearer token, KEK, ciphertext, encrypted DEK를 붙여 넣지 않는다.
- `docs/AdminUI_Handbook/` 경로는 diff에 없어야 한다.

## 작업 1: Local Rehearsal Evidence Bundle 체크리스트 확정

**Files:**

- Create: `docs/ops/pilot-evidence-bundle-checklist.md`
- Create: `tests/unit/test_pilot_evidence_bundle_docs_contract.py`
- Modify: `README.md`
- Modify: `docs/ops/pilot-rehearsal.md`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Modify: `docs/ops/pilot-readiness-evidence.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_pilot_evidence_bundle_docs_contract.py`를 추가하고 다음 항목을 검증한다.

```text
docs/ops/pilot-evidence-bundle-checklist.md exists
run_pilot_rehearsal.py
pilot-rehearsal-manifest.json
pilot-rehearsal-manifest.md
final_status: PASS
secret_scan.passed: true
csv-baseline-comparison.md
dify-smoke-matrix.md
ops-evidence.md
no .secret.json
no Bearer token
no RAW_TEXT_KEK_BASE64
no query_raw
sha256sum pilot-rehearsal-manifest.json
do not commit var/evidence
SERVICE_ID
STATE_PATH
ADMIN_BOOTSTRAP_TOKEN
```

Run:

```bash
uv run pytest tests/unit/test_pilot_evidence_bundle_docs_contract.py -q
```

Expected: FAIL because the checklist file does not exist yet.

- [ ] **Step 2: checklist 문서 작성**

`docs/ops/pilot-evidence-bundle-checklist.md`에 다음 섹션을 작성한다.

```text
# Pilot Evidence Bundle Checklist
## Local Evidence Generation
## Required Files
## Reviewer Checks
## Secret Scan Confirmation
## Hash Record
## Failure Handling
## Files That Must Not Be Attached
## Ticket Fields To Copy
```

필수 local command는 아래 형태로 고정한다.

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON="{}"
export EMBEDDING_PROVIDER=fake
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

별도 터미널에서:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

검수 command:

```bash
uv run python -m json.tool var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
sha256sum var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
find var/evidence/${SERVICE_ID}/rehearsal -name '*.secret.json' -print
rg -n 'Bearer |RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/rehearsal
```

Expected:

```text
manifest final_status is PASS
manifest secret_scan.passed is true
sha256sum prints one digest for pilot-rehearsal-manifest.json
find prints no .secret.json files
rg prints no matches
```

- [ ] **Step 3: 기존 runbook에서 checklist 링크**

다음 파일에 `docs/ops/pilot-evidence-bundle-checklist.md` 링크를 추가한다.

```text
README.md
docs/ops/pilot-rehearsal.md
docs/ops/intent-routing-pilot-runbook.md
docs/ops/pilot-readiness-evidence.md
```

문구는 checklist가 Sprint 6의 검수 기준이며, lower-level runbook은 실패 진단용이라는 관계를 명확히 쓴다.

- [ ] **Step 4: 실제 local rehearsal 실행**

작업자 로컬 환경에서 Step 2 command를 실행한다. `SERVICE_ID`는 실행마다 새 값으로 둔다.

Expected output:

```json
{
  "final_status": "PASS"
}
```

실제 CLI는 `json_path`, `markdown_path`, `final_status`를 출력한다. 출력과 manifest hash를 release ticket template에 옮길 준비를 한다. `var/evidence/...` 파일은 커밋하지 않는다.

- [ ] **Step 5: test 통과 확인**

```bash
uv run pytest tests/unit/test_pilot_evidence_bundle_docs_contract.py tests/unit/test_pilot_rehearsal_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add README.md docs/ops/pilot-evidence-bundle-checklist.md docs/ops/pilot-rehearsal.md docs/ops/intent-routing-pilot-runbook.md docs/ops/pilot-readiness-evidence.md tests/unit/test_pilot_evidence_bundle_docs_contract.py
git commit -m "docs: define pilot evidence bundle review checklist"
```

## 작업 2: Dify UI Dry-Run Evidence Template 확정

**Files:**

- Create: `docs/integrations/dify-dry-run-evidence-template.md`
- Modify: `docs/integrations/dify-dry-run-rehearsal.md`
- Modify: `docs/integrations/dify-handoff-checklist.md`
- Modify: `docs/integrations/dify-http-request-node.md`
- Modify: `docs/integrations/dify-branching-playbook.md`
- Modify: `tests/unit/test_dify_dry_run_docs_contract.py`

- [ ] **Step 1: docs contract test 확장**

`tests/unit/test_dify_dry_run_docs_contract.py`에 template 파일 검증을 추가한다.

필수 문자열:

```text
docs/integrations/dify-dry-run-evidence-template.md
Dify workflow version identifier
masked screenshot or workflow export path
intent_routing_api_key secret variable
workflow_run_id
Timeout: 8 seconds
no automatic retry loop
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
pilot-rehearsal-manifest.md
```

Run:

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py -q
```

Expected: FAIL because the template file does not exist yet.

- [ ] **Step 2: Dify evidence template 작성**

`docs/integrations/dify-dry-run-evidence-template.md`에 다음 섹션을 작성한다.

```text
# Dify Dry-Run Evidence Template
## Target
## HTTP Request Node Verification
## Decision Branch Results
## Error Branch Results
## Secret Masking Review
## Workflow Version
## Evidence Paths
## Operator Notes
## Approval
```

Decision branch table은 아래 행을 포함한다.

```text
confident
clarify
fallback
off_topic
risk
unauthorized
```

Error branch table은 아래 행을 포함한다.

```text
401
403
422
408
5xx
timeout
```

각 행에는 다음 열을 둔다.

```text
case
input or simulated condition
observed branch
trace_id
request_id
release_version
route execution allowed
operator result
```

`408`, `5xx`, `timeout` 행은 `route execution allowed = no`와 `no automatic retry loop`를 명시한다.

- [ ] **Step 3: 기존 Dify 문서에 template 연결**

다음 파일에 template 링크와 사용 시점을 추가한다.

```text
docs/integrations/dify-dry-run-rehearsal.md
docs/integrations/dify-handoff-checklist.md
docs/integrations/dify-http-request-node.md
docs/integrations/dify-branching-playbook.md
```

필수 운영 기준:

```text
The rehearsal wrapper records only the Dify workflow version identifier and evidence path.
Screenshots and workflow exports must show masked values only.
Do not paste screenshot/export contents into pilot-rehearsal-manifest.md.
```

- [ ] **Step 4: manual Dify dry-run 절차 검수**

Dify UI 접근 가능한 운영자가 template을 채우고 아래 rehearsal wrapper 인자를 사용한다.

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment dev \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --dify-workflow-version "dify-workflow-export-YYYYMMDD-NNN" \
  --dify-ui-evidence-path "var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md" \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Expected:

```text
pilot-rehearsal-manifest.md includes the workflow version identifier
pilot-rehearsal-manifest.md includes the Dify UI evidence path
pilot-rehearsal-manifest.md does not inline screenshot or workflow export content
secret scan passes
```

- [ ] **Step 5: test 통과 확인**

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/integrations/dify-dry-run-evidence-template.md docs/integrations/dify-dry-run-rehearsal.md docs/integrations/dify-handoff-checklist.md docs/integrations/dify-http-request-node.md docs/integrations/dify-branching-playbook.md tests/unit/test_dify_dry_run_docs_contract.py
git commit -m "docs: add Dify dry-run evidence template"
```

## 작업 3: Closed-Network/BGE Package Benchmark 증적 템플릿 확정

**Files:**

- Create: `docs/ops/bge-m3-evidence-template.md`
- Create: `tests/unit/test_bge_evidence_template_docs_contract.py`
- Modify: `docs/ops/bge-m3-closed-network.md`
- Modify: `docs/ops/closed-network-deployment.md`
- Modify: `docs/ops/pilot-rehearsal.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_bge_evidence_template_docs_contract.py`를 추가하고 다음 문자열을 검증한다.

```text
docs/ops/bge-m3-evidence-template.md
verify_bge_m3_package.py
benchmark_bge_m3.py
run_pilot_rehearsal.py
--mode closed-network
--run-bge-benchmark
BGE_M3_MODEL_PATH
BGE_M3_MODEL_SHA256
/models/bge-m3
dimension: 1024
batch_size: 16
max_tokens: 256
latency_ms.p50
latency_ms.p95
max_rss_mb
offline_required
measured-pass
measured-fail
pending-host-access
pending-host-access blocks pilot go/no-go
```

Run:

```bash
uv run pytest tests/unit/test_bge_evidence_template_docs_contract.py -q
```

Expected: FAIL because the template file does not exist yet.

- [ ] **Step 2: BGE evidence template 작성**

`docs/ops/bge-m3-evidence-template.md`에 다음 섹션을 작성한다.

```text
# BGE-M3 Closed-Network Evidence Template
## Status
## Package Approval Record
## Package Preflight Result
## Benchmark Result
## Closed-Network Rehearsal Result
## Offline Runtime Confirmation
## Failure Handling
## Pilot Go/No-Go
```

Status 값은 아래 세 가지만 허용한다고 문서화한다.

```text
measured-pass
measured-fail
pending-host-access
```

정책 문구:

```text
pending-host-access can close a local documentation sprint only when the closed-network host is not yet available.
pending-host-access blocks pilot go/no-go.
pilot handoff requires measured-pass for package preflight, benchmark, closed-network rehearsal, and secret scan.
```

필수 command:

```bash
uv run python scripts/verify_bge_m3_package.py \
  --model-path /models/bge-m3 \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/bge-package \
  --expected-sha256 ${BGE_M3_MODEL_SHA256}

EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/models/bge-m3 \
BGE_M3_BATCH_SIZE=16 \
uv run python scripts/benchmark_bge_m3.py \
  --model-path /models/bge-m3 \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/bge-benchmark \
  --batch-size 16

uv run python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment pilot \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 ${BGE_M3_MODEL_SHA256} \
  --run-bge-benchmark \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

- [ ] **Step 3: 기존 closed-network 문서 연결**

다음 문서에 template 링크와 status 정책을 추가한다.

```text
docs/ops/bge-m3-closed-network.md
docs/ops/closed-network-deployment.md
docs/ops/pilot-rehearsal.md
```

문구는 실제 파일럿 go/no-go에서 `pending-host-access`가 불합격임을 명확히 한다.

- [ ] **Step 4: closed-network host에서 수동 실측**

폐쇄망 host가 준비된 경우 Step 2의 command를 실행한다.

Expected:

```text
bge-m3-package.json exists
bge-m3-package.md exists
bge-m3-benchmark.json exists
bge-m3-benchmark.md exists
pilot-rehearsal-manifest.json final_status is PASS
secret_scan.passed is true
dimension is 1024
batch_size is 16
max_tokens is 256
```

폐쇄망 host가 아직 없으면 `docs/ops/bge-m3-evidence-template.md`의 status를 `pending-host-access`로 채운 evidence record를 release ticket에 첨부하고, pilot go/no-go는 blocked로 표시한다.

- [ ] **Step 5: test 통과 확인**

```bash
uv run pytest tests/unit/test_bge_evidence_template_docs_contract.py tests/unit/test_closed_network_packaging_contract.py tests/unit/test_pilot_rehearsal_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/ops/bge-m3-evidence-template.md docs/ops/bge-m3-closed-network.md docs/ops/closed-network-deployment.md docs/ops/pilot-rehearsal.md tests/unit/test_bge_evidence_template_docs_contract.py
git commit -m "docs: define BGE closed-network evidence template"
```

## 작업 4: Branch Protection 적용/rollback 증적 템플릿 확정

**Files:**

- Create: `docs/ops/branch-protection-evidence-template.md`
- Create: `tests/unit/test_branch_protection_evidence_template_docs_contract.py`
- Modify: `docs/ops/branch-protection.md`
- Modify: `docs/ops/ci-verification.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_branch_protection_evidence_template_docs_contract.py`를 추가하고 다음 문자열을 검증한다.

```text
docs/ops/branch-protection-evidence-template.md
main
CI / verify
Require status checks to pass before merging
Require branches to be up to date before merging
strict: true
contexts: ["CI / verify"]
workflow_dispatch
temporary bypass approval
rollback approval ID
exact commit SHA
pilot-e2e-evidence
14 days
no .secret.json
final branch protection state
```

Run:

```bash
uv run pytest tests/unit/test_branch_protection_evidence_template_docs_contract.py -q
```

Expected: FAIL because the template file does not exist yet.

- [ ] **Step 2: evidence template 작성**

`docs/ops/branch-protection-evidence-template.md`에 다음 섹션을 작성한다.

```text
# Branch Protection Evidence Template
## Rule Snapshot
## Required Check Verification
## Pull Request Merge Block Verification
## Artifact Verification
## Rollback Or Temporary Bypass Record
## Final State
```

필수 rule 값:

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI / verify"]
  },
  "enforce_admins": true
}
```

Rollback record 필수 필드:

```text
temporary bypass approval ID
exact commit SHA
reason
reviewers
workflow_dispatch rerun URL
pilot-e2e-evidence artifact review result
no .secret.json confirmation
final branch protection state
```

- [ ] **Step 3: branch protection runbook 연결**

`docs/ops/branch-protection.md`와 `docs/ops/ci-verification.md`에 template 링크를 추가한다.

운영 권한이 없는 작업자의 처리 문구:

```text
If the implementer does not have repository admin permission, create an evidence request using docs/ops/branch-protection-evidence-template.md and mark the rule snapshot as operator-not-permitted.
operator-not-permitted does not satisfy pilot go/no-go until an authorized operator attaches the rule snapshot.
```

- [ ] **Step 4: 수동 적용/rollback 검수**

권한 있는 operator shell에서 rule snapshot을 캡처한다.

```bash
mkdir -p var/evidence/${SERVICE_ID}/branch-protection
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  > var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
```

검수:

```bash
uv run python -m json.tool var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
rg -n '"CI / verify"|"strict": true|"enforce_admins": true' var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
```

Expected:

```text
CI / verify appears as a required status check
strict is true
enforce_admins is true when repository policy requires admin enforcement
```

- [ ] **Step 5: test 통과 확인**

```bash
uv run pytest tests/unit/test_branch_protection_docs_contract.py tests/unit/test_branch_protection_evidence_template_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/ops/branch-protection-evidence-template.md docs/ops/branch-protection.md docs/ops/ci-verification.md tests/unit/test_branch_protection_evidence_template_docs_contract.py
git commit -m "docs: add branch protection evidence template"
```

## 작업 5: CSV Baseline Refresh 승인 정책 확정

**Files:**

- Create: `docs/pilot/csv-baseline-refresh-policy.md`
- Create: `tests/unit/test_csv_baseline_refresh_policy_docs_contract.py`
- Modify: `docs/pilot/README.md`
- Modify: `docs/ops/pilot-rehearsal.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_csv_baseline_refresh_policy_docs_contract.py`를 추가하고 다음 문자열을 검증한다.

```text
docs/pilot/csv-baseline-refresh-policy.md
it-helpdesk-pilot-baseline.json
standard 50-row
balanced
allowed_new_failures: 0
allowed_new_reviews: 0
Do not refresh the baseline merely to make a failing rehearsal pass.
CSV diff
catalog diff
threshold policy diff
approval ID
risk_pass_rate
compare_csv_baseline.py freeze
compare_csv_baseline.py compare
no raw query text
```

Run:

```bash
uv run pytest tests/unit/test_csv_baseline_refresh_policy_docs_contract.py -q
```

Expected: FAIL because the policy file does not exist yet.

- [ ] **Step 2: refresh policy 문서 작성**

`docs/pilot/csv-baseline-refresh-policy.md`에 다음 섹션을 작성한다.

```text
# CSV Baseline Refresh Policy
## Current Baseline
## When Refresh Is Allowed
## When Refresh Is Blocked
## Required Review Evidence
## Freeze Command
## Compare Command
## Pull Request Requirements
## Rollback
```

정책:

```text
The current checked-in baseline is docs/pilot/it-helpdesk-pilot-baseline.json.
It freezes the standard 50-row CSV for the balanced preset.
allowed_new_failures remains 0.
allowed_new_reviews remains 0.
Do not refresh the baseline merely to make a failing rehearsal pass.
Refresh requires an approval ID and a reviewed CSV diff, catalog diff, or threshold policy diff.
Baseline JSON must not contain raw query text or secret-bearing fields.
```

Freeze command:

```bash
uv run python scripts/compare_csv_baseline.py freeze \
  --threshold-report var/evidence/${SERVICE_ID}/rehearsal/e2e/${SERVICE_ID}-threshold-comparison.json \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --preset balanced \
  --baseline-id it-helpdesk-pilot-standard-YYYYMMDD \
  --out docs/pilot/it-helpdesk-pilot-baseline.json
```

Compare command:

```bash
uv run python scripts/compare_csv_baseline.py compare \
  --threshold-report var/evidence/${SERVICE_ID}/rehearsal/e2e/${SERVICE_ID}-threshold-comparison.json \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/csv-baseline
```

- [ ] **Step 3: existing docs 연결**

다음 문서에 refresh policy 링크를 추가한다.

```text
docs/pilot/README.md
docs/ops/pilot-rehearsal.md
```

`docs/pilot/README.md`의 기존 "CSV Baseline Regression Gate" 섹션은 정책 문서가 source of truth임을 가리키게 한다.

- [ ] **Step 4: baseline file secret 검수**

```bash
rg -n 'query|authorization|api_key|Bearer |encrypted_dek|ciphertext|RAW_TEXT_KEK_BASE64' docs/pilot/it-helpdesk-pilot-baseline.json
```

Expected: no matches.

- [ ] **Step 5: test 통과 확인**

```bash
uv run pytest tests/unit/test_csv_baseline.py tests/integration/test_csv_baseline_flow.py tests/unit/test_csv_baseline_refresh_policy_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/pilot/csv-baseline-refresh-policy.md docs/pilot/README.md docs/ops/pilot-rehearsal.md tests/unit/test_csv_baseline_refresh_policy_docs_contract.py
git commit -m "docs: define CSV baseline refresh policy"
```

## 작업 6: Pilot Handoff/Release Ticket Template 확정

**Files:**

- Create: `docs/ops/pilot-handoff-release-ticket-template.md`
- Create: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `README.md`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Modify: `docs/integrations/dify-handoff-checklist.md`
- Modify: `docs/ops/pilot-rehearsal.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_pilot_handoff_release_template_docs_contract.py`를 추가하고 다음 문자열을 검증한다.

```text
docs/ops/pilot-handoff-release-ticket-template.md
service_id
environment
release_version
commit SHA
PR URL
CI / verify
local rehearsal manifest
manifest sha256
Dify workflow version identifier
Dify UI evidence path
BGE evidence status
branch protection evidence
CSV baseline comparison
rollback plan
go/no-go
Admin UI excluded
no secrets
no raw query text
```

Run:

```bash
uv run pytest tests/unit/test_pilot_handoff_release_template_docs_contract.py -q
```

Expected: FAIL because the template file does not exist yet.

- [ ] **Step 2: handoff/release ticket template 작성**

`docs/ops/pilot-handoff-release-ticket-template.md`에 다음 섹션을 작성한다.

```text
# Pilot Handoff And Release Ticket Template
## Release Scope
## Code And CI
## Local Rehearsal Evidence
## Dify UI Dry-Run Evidence
## Closed-Network BGE Evidence
## Branch Protection Evidence
## CSV Baseline Evidence
## Security And Incident Rehearsal Evidence
## Rollback Plan
## Open Risks
## Go/No-Go Decision
## Approvals
```

필수 gate:

```text
go requires CI / verify pass
go requires local rehearsal final_status PASS
go requires local rehearsal secret_scan.passed true
go requires Dify UI evidence path and workflow version identifier
go requires CSV baseline comparison PASS
go requires branch protection evidence for main
go requires BGE measured-pass before closed-network pilot traffic
Admin UI excluded from Sprint 6
ticket must not contain secrets or raw query text
```

- [ ] **Step 3: 기존 문서와 README 연결**

다음 파일에 release ticket template 링크를 추가한다.

```text
README.md
docs/ops/intent-routing-pilot-runbook.md
docs/integrations/dify-handoff-checklist.md
docs/ops/pilot-rehearsal.md
```

- [ ] **Step 4: release ticket dry-fill 수동 검수**

실제 local rehearsal 결과를 사용해 template을 `var/evidence/${SERVICE_ID}/release-ticket.md`에 복사해 채운다.

검수 command:

```bash
rg -n 'PASS|CI / verify|pilot-rehearsal-manifest.md|Dify workflow version identifier|go/no-go' var/evidence/${SERVICE_ID}/release-ticket.md
rg -n 'Bearer |RAW_TEXT_KEK_BASE64|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/release-ticket.md
```

Expected:

```text
first rg prints the required evidence references
second rg prints no matches
```

`var/evidence/${SERVICE_ID}/release-ticket.md`는 커밋하지 않는다.

- [ ] **Step 5: test 통과 확인**

```bash
uv run pytest tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_operator_docs_contract.py tests/unit/test_dify_handoff_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add README.md docs/ops/pilot-handoff-release-ticket-template.md docs/ops/intent-routing-pilot-runbook.md docs/integrations/dify-handoff-checklist.md docs/ops/pilot-rehearsal.md tests/unit/test_pilot_handoff_release_template_docs_contract.py
git commit -m "docs: add pilot handoff release ticket template"
```

## 작업 7: 통합 검증과 Sprint 6 종료 기준

**Files:**

- Modify only if needed: docs/tests touched by Tasks 1-6.

- [ ] **Step 1: focused docs tests 실행**

```bash
uv run pytest \
  tests/unit/test_pilot_evidence_bundle_docs_contract.py \
  tests/unit/test_dify_dry_run_docs_contract.py \
  tests/unit/test_bge_evidence_template_docs_contract.py \
  tests/unit/test_branch_protection_docs_contract.py \
  tests/unit/test_branch_protection_evidence_template_docs_contract.py \
  tests/unit/test_csv_baseline.py \
  tests/integration/test_csv_baseline_flow.py \
  tests/unit/test_csv_baseline_refresh_policy_docs_contract.py \
  tests/unit/test_pilot_handoff_release_template_docs_contract.py \
  tests/unit/test_pilot_rehearsal_docs_contract.py \
  tests/unit/test_dify_handoff_docs_contract.py \
  tests/unit/test_operator_docs_contract.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: static verification 실행**

```bash
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
```

Expected: all PASS.

- [ ] **Step 3: DB 포함 regression 실행**

PostgreSQL이 실행 중인 상태에서:

```bash
uv run pytest -q
```

Expected: PASS.

DB가 없는 환경에서는 아래를 먼저 실행한다.

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run pytest -q
```

- [ ] **Step 4: actual local rehearsal smoke 재실행**

Task 1의 local rehearsal command를 새 `SERVICE_ID`로 한 번 더 실행한다.

Expected:

```text
pilot-rehearsal-manifest.json final_status PASS
secret_scan.passed true
csv-baseline status pass
dify-smoke-matrix status pass
ops-evidence-export status pass
```

- [ ] **Step 5: 금지 경로와 evidence 커밋 여부 확인**

```bash
git diff --name-only | rg '^docs/AdminUI_Handbook/'
git status --short | rg 'var/evidence|var/pilot|\.secret\.json'
```

Expected: no matches.

`git status --short` may still show the pre-existing untracked `docs/AdminUI_Handbook/`; leave it untouched.

- [ ] **Step 6: final commit**

아직 커밋되지 않은 Sprint 6 docs/test 변경이 있으면:

```bash
git add README.md docs/ops docs/integrations docs/pilot tests/unit
git commit -m "docs: finalize Sprint 6 pilot evidence procedures"
```

## Sprint 6 Acceptance Criteria

- `docs/ops/pilot-evidence-bundle-checklist.md`가 실제 local rehearsal 실행, manifest 검수, secret scan 검수, hash 기록, 금지 파일 기준을 포함한다.
- 작업자 로컬에서 한 번 이상 `scripts/run_pilot_rehearsal.py --mode local`을 실행했고 `pilot-rehearsal-manifest.json`의 `final_status`가 `PASS`다.
- Dify UI dry-run evidence template이 모든 decision/error branch, workflow version identifier, masked evidence path, no-retry 기준을 포함한다.
- BGE evidence template이 package preflight, benchmark, closed-network rehearsal, `measured-pass`/`measured-fail`/`pending-host-access` 상태, pilot go/no-go blocking 기준을 포함한다.
- Branch protection evidence template이 `main`, `CI / verify`, strict required status check, artifact review, rollback/bypass record를 포함한다.
- CSV baseline refresh policy가 refresh 허용 조건, 차단 조건, approval ID, freeze/compare command, no raw query 기준을 포함한다.
- Pilot handoff/release ticket template이 CI, local rehearsal, Dify, BGE, branch protection, CSV baseline, rollback, go/no-go, approval 필드를 포함한다.
- 새 문서와 링크는 docs contract test로 검증된다.
- `uv run ruff check .`, `uv run mypy src tests`, `docker compose --profile runtime config`, focused docs tests가 통과한다.
- DB가 준비된 환경에서 `uv run pytest -q`가 통과한다.
- `docs/AdminUI_Handbook/`, `var/evidence/...`, `var/pilot/*.secret.json`는 커밋 대상에 포함되지 않는다.

## 수동 검수 절차

1. 새 `SERVICE_ID`로 local rehearsal을 실행한다.
2. `pilot-rehearsal-manifest.json`에서 `final_status=PASS`, `secret_scan.passed=true`를 확인한다.
3. `pilot-rehearsal-manifest.md`, `csv-baseline-comparison.md`, `dify-smoke-matrix.md`, `ops-evidence.md`가 존재하는지 확인한다.
4. `find`로 `.secret.json`이 evidence bundle 안에 없는지 확인한다.
5. `rg`로 bearer token, KEK, raw query, encrypted DEK, ciphertext marker가 없는지 확인한다.
6. Dify UI dry-run evidence template을 한 번 채워보고 wrapper가 evidence path와 workflow version만 manifest에 기록하는지 확인한다.
7. closed-network host가 있으면 BGE package/benchmark/rehearsal을 실측한다. host가 없으면 `pending-host-access`로 기록하고 pilot go/no-go를 blocked로 둔다.
8. branch protection rule snapshot을 권한 있는 operator가 첨부한다. 권한이 없으면 `operator-not-permitted`로 evidence request를 남기고 pilot go/no-go를 blocked로 둔다.
9. release ticket template을 `var/evidence/${SERVICE_ID}/release-ticket.md`에 dry-fill하고 secret scan pattern으로 확인한다.

## 사용자가 선택해야 하는 정책/범위 결정

- **Closed-network BGE 범위:** Sprint 6 완료 조건에 실제 폐쇄망 BGE 실측까지 포함할지, 아니면 `pending-host-access` evidence template 확정까지만 포함할지 결정해야 한다. 파일럿 go/no-go에는 `measured-pass`가 필요하다.
- **Dify evidence 형태:** 운영 증적으로 masked screenshot을 받을지, sanitized workflow export를 받을지, 둘 다 허용할지 결정해야 한다. 어떤 형태든 manifest에는 path와 workflow version identifier만 기록한다.
- **Branch protection 권한 처리:** Sprint 6 작업자가 repo admin 권한이 없을 때 `operator-not-permitted` request로 Sprint를 닫을 수 있는지, 아니면 권한 있는 operator snapshot을 Sprint 6 안에서 필수로 받을지 결정해야 한다.
- **CSV baseline refresh 승인자:** baseline refresh approval ID를 누가 발급하는지 정해야 한다. 추천은 release owner 1명과 QA/security reviewer 1명의 명시 승인이다.

## 실행 방식 추천

Subagent-Driven 실행을 추천한다. 작업 1-6은 문서 영역이 서로 분리되어 있고, 각 작업마다 docs contract test와 review checkpoint가 분명해서 fresh subagent가 병렬이 아니라 순차적으로 맡아도 충돌이 작다. 단, 실제 local rehearsal 실행과 최종 통합 검증은 한 세션에서 이어서 수행하는 편이 좋다.
