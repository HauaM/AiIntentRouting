# Intent Routing Sprint 9 Go Reassessment Gate Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 8 `No Go` 사유였던 Dify, BGE, branch protection, CSV freeze approval gate를 실제 증적으로 닫고 pilot launch `Go / Conditional Go / No Go`를 재판정한다.

**Architecture:** Sprint 9는 신규 제품 기능 개발이 아니라 gate closure와 go reassessment 스프린트다. Runtime evidence는 `var/evidence/${SERVICE_ID}` 아래에 local-only로 생성하고, repo에는 secret-safe 공식 closure 문서와 필요한 docs contract test만 커밋한다. Admin UI 구현은 계속 제외한다.

**Tech Stack:** Markdown evidence, pytest docs contract tests, GitHub CLI/API branch protection capture, Dify UI manual dry-run, BGE-M3 closed-network verification scripts, existing pilot rehearsal scripts, ruff, mypy, Docker Compose, PostgreSQL + pgvector.

---

## Sprint 9 정책 결정

- Primary target: `Go`.
- `Conditional Go` 허용 범위: BGE closed-network host access가 Sprint 9 안에 확보되지 않을 때만, closed-network pilot traffic을 차단하는 bounded exception이 승인된 경우.
- `Conditional Go` 불허 범위:
  - Dify UI dry-run evidence 미승인.
  - Branch protection authorized capture 미확보.
  - CSV freeze approval ID 또는 reviewer 미확보.
  - Local rehearsal 실패 또는 secret scan 실패.
- `No Go` 조건:
  - required gate 중 하나라도 missing, blocked, failed, unsafe, or unapproved 상태.
- Admin UI implementation: excluded.

## Sprint 8에서 넘어온 No Go 사유

- Local rehearsal: `PASS`.
- `secret_scan.passed`: `true`.
- Dify UI dry-run: UI access, workflow version identifier, reviewer, sanitized screenshot/export path 미확보.
- BGE closed-network: host/model path, model SHA, measured-pass, exception approval owner/date 미확보.
- Branch protection: `HTTP 403/operator-not-permitted`, valid `main-protection.json` snapshot과 structured verification output 미확보.
- CSV baseline: comparison `PASS`, freeze approval ID, release owner, QA/security reviewer 미확보.

## 파일 범위

커밋 가능한 파일:

```text
docs/superpowers/plans/2026-06-30-intent-routing-sprint-9.md
docs/ops/pilot-sprint-9-execution-closure.md
docs/ops/pilot-sprint-9-release-ticket.md
docs/ops/pilot-sprint-9-go-no-go-decision.md
tests/unit/test_pilot_sprint9_closure_docs_contract.py
```

문서 계약 gap이 발견될 때만 수정 가능한 파일:

```text
docs/ops/pilot-launch-readiness-checklist.md
docs/ops/pilot-handoff-release-ticket-template.md
docs/ops/pilot-go-no-go-decision-template.md
docs/ops/branch-protection.md
docs/ops/branch-protection-evidence-template.md
docs/ops/bge-m3-evidence-template.md
docs/integrations/dify-dry-run-evidence-template.md
docs/integrations/dify-dry-run-rehearsal.md
docs/integrations/dify-handoff-checklist.md
docs/pilot/csv-baseline-freeze-approval-template.md
docs/pilot/csv-baseline-refresh-policy.md
tests/unit/test_pilot_launch_readiness_docs_contract.py
tests/unit/test_pilot_handoff_release_template_docs_contract.py
tests/unit/test_pilot_go_no_go_decision_docs_contract.py
tests/unit/test_dify_dry_run_docs_contract.py
tests/unit/test_bge_evidence_template_docs_contract.py
tests/unit/test_branch_protection_docs_contract.py
tests/unit/test_branch_protection_evidence_template_docs_contract.py
tests/unit/test_csv_baseline_freeze_approval_docs_contract.py
```

커밋 금지 파일:

```text
var/evidence/${SERVICE_ID}
var/pilot/${SERVICE_ID}.state.secret.json
*.secret.json
main-protection.json
screenshots
workflow exports
raw Dify exports
runtime logs
```

## 작업 1: Sprint 9 evidence root와 재판정 index 생성

**Files:**

- Create local-only: `var/evidence/${SERVICE_ID}/sprint-9-go-reassessment-index.md`
- Read: `docs/ops/pilot-sprint-8-execution-closure.md`
- Read: `docs/ops/pilot-sprint-8-go-no-go-decision.md`
- Read: `docs/ops/pilot-sprint-8-release-ticket.md`

- [ ] **Step 1: 실행 전 git 상태 확인**

Run:

```bash
git status --short --branch
git rev-parse HEAD
```

Expected:

```text
branch is codex/intent-routing-sprint-9-go-reassessment
no unexpected tracked changes before evidence execution
```

- [ ] **Step 2: SERVICE_ID 설정**

Run:

```bash
export SERVICE_ID="it-helpdesk-pilot-sprint9-go-reassessment"
export EVIDENCE_ROOT="var/evidence/${SERVICE_ID}"
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
mkdir -p "${EVIDENCE_ROOT}"
```

Expected:

```text
var/evidence/it-helpdesk-pilot-sprint9-go-reassessment exists
STATE_PATH points under var/pilot and ends with .secret.json
```

- [ ] **Step 3: index 작성**

Create `var/evidence/${SERVICE_ID}/sprint-9-go-reassessment-index.md` with:

```markdown
# Sprint 9 Go Reassessment Index

- SERVICE_ID: it-helpdesk-pilot-sprint9-go-reassessment
- Repository commit:
- Evidence root: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment
- Admin UI implementation: excluded
- Primary target: Go
- Conditional Go scope: BGE bounded exception only

## Gate Status

| gate | required for Go | conditional allowed | status | evidence path | owner | approval ID | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| local rehearsal | yes | no | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/rehearsal/pilot-rehearsal-manifest.md |  |  |  |
| Dify UI dry-run | yes | no | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/dify-ui/dify-dry-run-evidence.md |  |  |  |
| BGE closed-network | yes for closed-network traffic | yes, traffic blocked only | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/bge/bge-m3-evidence.md |  |  |  |
| branch protection | yes | no | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/branch-protection/branch-protection-evidence.md |  |  |  |
| CSV freeze approval | yes | no | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/csv-baseline-freeze-approval.md |  |  |  |
| release ticket | yes | no | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/release-ticket.md |  |  |  |
| go reassessment | yes | no | not-started | var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/pilot-go-no-go-decision.md |  |  |  |

## Decision Rules

- Go requires every required gate to be pass or approved.
- Conditional Go is allowed only when BGE is pending-host-access with approved bounded exception and closed-network traffic remains blocked.
- No Go is required when Dify, branch protection, CSV approval, local rehearsal, or release ticket evidence is missing or unapproved.
```

- [ ] **Step 4: index secret scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "${EVIDENCE_ROOT}/sprint-9-go-reassessment-index.md"
```

Expected:

```text
no matches
```

## 작업 2: CSV freeze approval gate 닫기

**Files:**

- Create local-only: `var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md`
- Read: `docs/pilot/csv-baseline-freeze-approval-template.md`
- Read: `docs/pilot/csv-baseline-refresh-policy.md`
- Read: `docs/pilot/it-helpdesk-pilot-baseline.json`
- Read: `docs/ops/pilot-sprint-8-release-ticket.md`

- [ ] **Step 1: baseline secret marker check**

Run:

```bash
rg -n 'query|authorization|api_key|Bearer |encrypted_dek|ciphertext|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON' docs/pilot/it-helpdesk-pilot-baseline.json
```

Expected:

```text
no matches
```

- [ ] **Step 2: latest comparison evidence 확인**

Run:

```bash
rg -n 'CSV baseline: comparison PASS|Manifest JSON SHA256|Local rehearsal status: PASS' docs/ops/pilot-sprint-8-release-ticket.md
```

Expected:

```text
Sprint 8 official release ticket confirms comparison PASS and local rehearsal PASS
```

- [ ] **Step 3: freeze approval evidence 작성**

Create `var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md` with:

```markdown
# Sprint 9 CSV Baseline Freeze Approval

- Baseline file: docs/pilot/it-helpdesk-pilot-baseline.json
- Pilot CSV tier: standard
- Preset: balanced
- Comparison result: PASS, carried forward from Sprint 8 official release ticket
- Refresh status: refresh not approved
- Freeze decision: checked-in baseline remains frozen for pilot go reassessment
- Freeze approval ID:
- Release owner:
- QA or security reviewer:
- Review timestamp:
- Gate status:

## Decision Rule

This gate is pass only when Freeze approval ID, Release owner, QA or security reviewer, and Review timestamp are filled with concrete values. If any field is blank, gate status is blocked and final go reassessment cannot be Go or Conditional Go.
```

- [ ] **Step 4: approval 값 입력 또는 blocked 기록**

If approval values are available, fill all fields and set:

```text
Gate status: pass
```

If any approval value is unavailable, set:

```text
Freeze approval ID: not provided
Release owner: not assigned
QA or security reviewer: not assigned
Review timestamp: not provided
Gate status: blocked
```

- [ ] **Step 5: CSV gate secret scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "${EVIDENCE_ROOT}/csv-baseline-freeze-approval.md"
```

Expected:

```text
no matches
```

## 작업 3: branch protection authorized capture gate 닫기

**Files:**

- Create local-only: `var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md`
- Create local-only only when authorized: `var/evidence/${SERVICE_ID}/branch-protection/main-protection.json`
- Read: `docs/ops/branch-protection.md`
- Read: `docs/ops/branch-protection-evidence-template.md`

- [ ] **Step 1: branch protection directory 생성**

Run:

```bash
mkdir -p "${EVIDENCE_ROOT}/branch-protection"
```

Expected:

```text
branch-protection evidence directory exists
```

- [ ] **Step 2: authorized capture 시도**

Run:

```bash
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  > "${EVIDENCE_ROOT}/branch-protection/main-protection.json"
```

Expected when authorized:

```text
main-protection.json exists and contains branch protection JSON
```

If GitHub returns permission or plan errors, remove invalid JSON and continue with blocked evidence:

```bash
rm -f "${EVIDENCE_ROOT}/branch-protection/main-protection.json"
```

- [ ] **Step 3: structured verification 실행**

Run only when `main-protection.json` exists:

```bash
uv run python - "${EVIDENCE_ROOT}/branch-protection/main-protection.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    protection = json.load(fh)

required_status_checks = protection.get("required_status_checks") or {}
if required_status_checks.get("strict") is not True:
    raise SystemExit("required_status_checks.strict is not true")

contexts = set(required_status_checks.get("contexts") or [])
for check in required_status_checks.get("checks") or []:
    contexts.update(
        value
        for value in (check.get("context"), check.get("name"))
        if isinstance(value, str)
    )
if "CI / verify" not in contexts and "verify" not in contexts:
    raise SystemExit("CI / verify is not a required status check")

enforce_admins = protection.get("enforce_admins")
admins_enabled = enforce_admins is True or (
    isinstance(enforce_admins, dict) and enforce_admins.get("enabled") is True
)
if not admins_enabled:
    raise SystemExit("enforce_admins is not enabled")

print("branch protection capture verified")
PY
```

Expected:

```text
branch protection capture verified
```

- [ ] **Step 4: branch protection evidence 작성**

Create `var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md` with:

```markdown
# Sprint 9 Branch Protection Evidence

- Protected branch: main
- Evidence type:
- Authorized operator:
- Operator permission result:
- Rule snapshot path:
- Verification output:
- Required status check evidence:
- Final branch protection state:
- Gate status:

## Decision Rule

This gate is pass only when an authorized operator captures a valid branch protection snapshot and structured verification prints `branch protection capture verified`. `operator-not-permitted` remains blocked and cannot support Go or Conditional Go.
```

If authorized capture succeeds, fill:

```text
Evidence type: verify
Operator permission result: authorized
Rule snapshot path: var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
Verification output: branch protection capture verified
Required status check evidence: CI / verify
Final branch protection state: verified
Gate status: pass
```

If capture fails, fill:

```text
Evidence type: operator-not-permitted
Authorized operator: not available in this session
Operator permission result: operator-not-permitted
Rule snapshot path: not attached
Verification output: not available
Required status check evidence: not captured
Final branch protection state: not verified from authorized snapshot
Gate status: blocked
```

- [ ] **Step 5: branch protection secret scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "${EVIDENCE_ROOT}/branch-protection"
```

Expected:

```text
no matches
```

## 작업 4: Dify UI dry-run gate 닫기

**Files:**

- Create local-only: `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`
- Create local-only: `var/evidence/${SERVICE_ID}/dify-ui/masked-screenshot-or-export-reference.md`
- Read: `docs/integrations/dify-dry-run-evidence-template.md`
- Read: `docs/integrations/dify-dry-run-rehearsal.md`
- Read: `docs/integrations/dify-handoff-checklist.md`

- [ ] **Step 1: Dify evidence directory 생성**

Run:

```bash
mkdir -p "${EVIDENCE_ROOT}/dify-ui"
```

Expected:

```text
Dify evidence directory exists
```

- [ ] **Step 2: Dify manual verification matrix 수행**

In Dify UI, verify and record:

```text
workflow version identifier
HTTP method POST
URL /v1/intent-route
timeout 8 seconds
approved secret variable is used without exposing raw value
X-Key-Id, X-App-Id, X-Service-Id, X-Request-Id mappings
body query and user_context.workflow_run_id mappings
confident branch trace/request/release fields
clarify branch question and candidates
fallback/off_topic/risk/unauthorized branches
401, 403, 422, 408, 5xx, timeout handling
no automatic retry loop for timeout and 5xx branches
reviewer approval
sanitized screenshot or workflow export reference path
```

- [ ] **Step 3: Dify evidence 작성**

Create `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md` with:

```markdown
# Sprint 9 Dify UI Dry-Run Evidence

- Operator result:
- Workflow version identifier:
- Evidence reviewer:
- Sanitized screenshot/export reference:
- Release ticket path: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/release-ticket.md
- Go/no-go decision path: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/pilot-go-no-go-decision.md
- Gate status:

## Decision Rule

This gate is pass only when the workflow version identifier, reviewer, sanitized evidence reference, and required branch checks are complete. Missing UI access, missing workflow version, missing reviewer, or missing sanitized evidence keeps this gate blocked.
```

If Dify UI evidence is unavailable, fill:

```text
Operator result: blocked
Workflow version identifier: not provided
Evidence reviewer: not assigned
Sanitized screenshot/export reference: not attached
Gate status: blocked
```

- [ ] **Step 4: Dify reference 작성**

Create `var/evidence/${SERVICE_ID}/dify-ui/masked-screenshot-or-export-reference.md` with:

```markdown
# Sprint 9 Dify Sanitized Evidence Reference

- Screenshot path:
- Workflow export path:
- Sanitization reviewer:
- Contains raw secrets: no
- Contains raw query text: no
- Contains workflow export contents inline: no
```

If no screenshot/export exists, record all paths as `not attached`.

- [ ] **Step 5: Dify secret scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "${EVIDENCE_ROOT}/dify-ui"
```

Expected:

```text
no matches
```

## 작업 5: BGE measured-pass 또는 bounded exception gate 닫기

**Files:**

- Create local-only: `var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md`
- Create local-only when measured: `var/evidence/${SERVICE_ID}/rehearsal/bge-package/bge-m3-package.json`
- Create local-only when measured: `var/evidence/${SERVICE_ID}/rehearsal/bge-benchmark/bge-m3-benchmark.json`
- Read: `docs/ops/bge-m3-evidence-template.md`
- Read: `docs/ops/bge-m3-closed-network.md`
- Read: `docs/ops/closed-network-deployment.md`

- [ ] **Step 1: BGE evidence directory 생성**

Run:

```bash
mkdir -p "${EVIDENCE_ROOT}/bge"
```

Expected:

```text
BGE evidence directory exists
```

- [ ] **Step 2: host access decision**

Choose one path:

```text
measured-pass: approved closed-network host, /models/bge-m3, and expected model SHA are available
bounded-exception: approved host is unavailable but release/security owner approves blocked closed-network traffic boundary
blocked: neither measured-pass nor bounded exception approval is available
```

- [ ] **Step 3A: measured package preflight**

Run only when host/model path/SHA are available:

```bash
export INTENT_ROUTING_ENVIRONMENT=pilot
export EMBEDDING_PROVIDER=bge-m3
export BGE_M3_MODEL_PATH=/models/bge-m3
uv run python scripts/verify_bge_m3_package.py \
  --model-path /models/bge-m3 \
  --out-dir "${EVIDENCE_ROOT}/rehearsal/bge-package" \
  --expected-sha256 "${BGE_M3_MODEL_SHA256}"
```

Expected:

```text
package JSON and Markdown exist
computed SHA matches expected SHA
offline_required is true
```

- [ ] **Step 3B: measured benchmark**

Run only after package preflight passes:

```bash
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/models/bge-m3 \
BGE_M3_BATCH_SIZE=16 \
uv run python scripts/benchmark_bge_m3.py \
  --model-path /models/bge-m3 \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --out-dir "${EVIDENCE_ROOT}/rehearsal/bge-benchmark" \
  --batch-size 16
```

Expected:

```text
dimension is 1024
latency p50 and p95 are recorded
max RSS is recorded
```

- [ ] **Step 4: BGE evidence 작성**

Create `var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md` with:

```markdown
# Sprint 9 BGE Closed-Network Evidence

- Evidence status:
- Host access decision:
- Model path:
- Model SHA status:
- Package preflight:
- Benchmark:
- Closed-network rehearsal:
- Exception approval ID:
- Exception owner:
- Approved by:
- Approval timestamp:
- Expires before pilot traffic:
- Next measurement date:
- Decision impact:
- Gate status:

## Decision Rule

`measured-pass` can support Go. `bounded-exception` can support Conditional Go only when closed-network traffic remains blocked until measured-pass evidence is attached. Missing measurement and missing exception approval keeps this gate blocked.
```

If no host and no approval are available, fill:

```text
Evidence status: pending-host-access
Host access decision: host unavailable in this session
Model path: not available
Model SHA status: not provided
Package preflight: not run
Benchmark: not run
Closed-network rehearsal: not run
Exception approval ID: not provided
Exception owner: not assigned
Approved by: not assigned
Approval timestamp: not provided
Expires before pilot traffic: yes, traffic remains blocked
Next measurement date: not scheduled
Decision impact: No Go unless bounded exception is approved
Gate status: blocked
```

- [ ] **Step 5: BGE secret scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "${EVIDENCE_ROOT}/bge"
```

Expected:

```text
no matches
```

## 작업 6: current launch candidate local rehearsal 재생성

**Files:**

- Create local-only: `var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json`
- Create local-only: `var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.md`
- Read: `docs/ops/pilot-rehearsal.md`
- Read: `scripts/run_pilot_rehearsal.py`

- [ ] **Step 1: isolated database 준비**

Run:

```bash
docker rm -f intent-routing-sprint9-postgres >/dev/null 2>&1 || true
docker run -d --name intent-routing-sprint9-postgres \
  -e POSTGRES_USER=intent \
  -e POSTGRES_PASSWORD=intent \
  -e POSTGRES_DB=intent_routing \
  -p 127.0.0.1:55434:5432 \
  pgvector/pgvector:pg16
until docker exec intent-routing-sprint9-postgres pg_isready -U intent -d intent_routing >/dev/null 2>&1; do sleep 1; done
```

Expected:

```text
Postgres is ready on 127.0.0.1:55434
```

- [ ] **Step 2: migration 적용**

Run:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55434/intent_routing
export TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55434/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON="{}"
export EMBEDDING_PROVIDER=fake
uv run alembic upgrade head
```

Expected:

```text
alembic upgrade head succeeds
```

- [ ] **Step 3: API 서버 실행**

Run in a dedicated terminal:

```bash
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55434/intent_routing \
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55434/intent_routing \
INTENT_ROUTING_ENVIRONMENT=dev \
ADMIN_BOOTSTRAP_TOKEN=local-admin-token \
RAW_TEXT_KEK_ID=local-kek-001 \
RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
RAW_TEXT_LEGACY_KEKS_JSON='{}' \
EMBEDDING_PROVIDER=fake \
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8001
```

Expected:

```text
GET http://127.0.0.1:8001/readyz succeeds
```

- [ ] **Step 4: rehearsal 실행**

Run:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8001 \
  --admin-token local-admin-token \
  --service-id "${SERVICE_ID}" \
  --environment dev \
  --state-path "${STATE_PATH}" \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --out-dir "${EVIDENCE_ROOT}/rehearsal"
```

Expected:

```text
final_status is PASS
secret_scan.passed is true
```

- [ ] **Step 5: reviewer checks**

Run:

```bash
uv run python -m json.tool "${EVIDENCE_ROOT}/rehearsal/pilot-rehearsal-manifest.json"
sha256sum "${EVIDENCE_ROOT}/rehearsal/pilot-rehearsal-manifest.json"
find "${EVIDENCE_ROOT}/rehearsal" -name '*.secret.json' -print
rg -n 'Authorization: Bearer|Bearer |RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "${EVIDENCE_ROOT}/rehearsal"
```

Expected:

```text
json.tool succeeds
sha256sum prints one digest
find prints no .secret.json files
rg prints no matches
```

- [ ] **Step 6: cleanup**

Run after rehearsal:

```bash
docker rm -f intent-routing-sprint9-postgres
```

Expected:

```text
container removed
```

## 작업 7: Sprint 9 공식 closure docs와 contract test 작성

**Files:**

- Create: `tests/unit/test_pilot_sprint9_closure_docs_contract.py`
- Create: `docs/ops/pilot-sprint-9-execution-closure.md`
- Create: `docs/ops/pilot-sprint-9-release-ticket.md`
- Create: `docs/ops/pilot-sprint-9-go-no-go-decision.md`

- [ ] **Step 1: failing docs contract test 작성**

Create `tests/unit/test_pilot_sprint9_closure_docs_contract.py` with tests that require:

```text
the three Sprint 9 docs exist
closure doc links release ticket and decision doc
release ticket records each gate status
decision doc contains exactly one Decision value
Decision value is Go, Conditional Go, or No Go
if Dify, branch protection, CSV, or local rehearsal is blocked then Decision value is No Go
if BGE is bounded-exception then Decision value can be Conditional Go only when closed-network traffic is blocked
docs contain no forbidden secret markers
docs do not mention docs/AdminUI_Handbook/
```

- [ ] **Step 2: verify RED**

Run:

```bash
uv run pytest tests/unit/test_pilot_sprint9_closure_docs_contract.py -q
```

Expected:

```text
test fails because Sprint 9 docs do not exist yet
```

- [ ] **Step 3: 공식 closure docs 작성**

Write:

```text
docs/ops/pilot-sprint-9-execution-closure.md
docs/ops/pilot-sprint-9-release-ticket.md
docs/ops/pilot-sprint-9-go-no-go-decision.md
```

Each document must record:

```text
SERVICE_ID
current branch and commit
Admin UI implementation excluded
local rehearsal status and manifest hash
Dify gate status
BGE gate status
branch protection gate status
CSV freeze gate status
CI / verify status when PR exists
final Decision value
pilot traffic boundary
runtime evidence not committed
```

Decision value rules:

```text
Go only when local rehearsal, Dify, branch protection, CSV, release ticket, and BGE measured-pass are pass or approved.
Conditional Go only when every non-BGE required gate is pass and BGE has approved bounded exception with closed-network traffic blocked.
No Go otherwise.
```

- [ ] **Step 4: verify GREEN**

Run:

```bash
uv run pytest tests/unit/test_pilot_sprint9_closure_docs_contract.py -q
```

Expected:

```text
all Sprint 9 closure docs tests pass
```

## 작업 8: 최종 검증

**Files:**

- Read: all files changed in Sprint 9 branch

- [ ] **Step 1: focused docs tests**

Run:

```bash
uv run pytest \
  tests/unit/test_pilot_launch_readiness_docs_contract.py \
  tests/unit/test_pilot_handoff_release_template_docs_contract.py \
  tests/unit/test_pilot_go_no_go_decision_docs_contract.py \
  tests/unit/test_pilot_evidence_bundle_docs_contract.py \
  tests/unit/test_dify_dry_run_docs_contract.py \
  tests/unit/test_bge_evidence_template_docs_contract.py \
  tests/unit/test_branch_protection_docs_contract.py \
  tests/unit/test_branch_protection_evidence_template_docs_contract.py \
  tests/unit/test_csv_baseline_freeze_approval_docs_contract.py \
  tests/unit/test_operator_docs_contract.py \
  tests/unit/test_pilot_sprint9_closure_docs_contract.py \
  -q
```

Expected:

```text
all focused docs tests pass
```

- [ ] **Step 2: static checks**

Run:

```bash
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
```

Expected:

```text
ruff passes
mypy passes
docker compose runtime config renders successfully
```

- [ ] **Step 3: git exclusion checks**

Run:

```bash
git status --short
git status --short | rg 'var/evidence|var/pilot|\.secret\.json|main-protection\.json|dify-ui|screenshot|workflow'
git diff --name-only HEAD~1..HEAD | rg '^docs/AdminUI_Handbook/'
```

Expected:

```text
no runtime evidence, secret state, branch snapshot, screenshot, workflow export, or Admin UI files are tracked
```

- [ ] **Step 4: final forbidden marker scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' docs/ops/pilot-sprint-9-*.md
```

Expected:

```text
no matches
```

## Acceptance Criteria

- Sprint 9 evidence index exists locally and maps every reassessment gate.
- CSV freeze gate is pass with concrete approval fields or blocked with explicit missing fields.
- Branch protection gate is pass with authorized snapshot and structured verification, or blocked with operator-not-permitted evidence.
- Dify gate is pass with workflow version, reviewer, sanitized evidence reference, and branch checklist result, or blocked with explicit missing fields.
- BGE gate is measured-pass, approved bounded exception, or blocked with explicit reason.
- Current launch candidate local rehearsal is regenerated and reviewed, or failure is recorded.
- Official Sprint 9 closure docs are committed without runtime evidence.
- Final decision follows decision rules exactly.
- Focused docs tests, static checks, and secret marker scans pass.
- Admin UI implementation remains excluded.

## Subagent Execution Slices

- Worker 1: CSV freeze approval evidence.
- Worker 2: Branch protection authorized capture evidence.
- Worker 3: Dify UI dry-run evidence.
- Worker 4: BGE measured-pass or bounded exception evidence.
- Worker 5: Local rehearsal regeneration.
- Worker 6: Official Sprint 9 closure docs and docs contract test.
- Final reviewer: verify all gate outcomes, final decision, secret safety, and git exclusion.
