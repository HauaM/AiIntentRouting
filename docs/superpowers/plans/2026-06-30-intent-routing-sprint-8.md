# Intent Routing Sprint 8 Pilot Execution & Evidence Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 7에서 정의한 launch readiness checklist와 evidence template을 실제 pilot execution evidence tree로 작성, 검수, 링크하여 최종 Go / Conditional Go / No Go 판정을 남긴다.

**Architecture:** Sprint 8은 API, routing policy, threshold, Admin UI를 변경하지 않는 운영 실행 스프린트다. Source of truth는 Sprint 7 문서와 계약 테스트이며, 실제 실행 산출물은 `var/evidence/${SERVICE_ID}/...` 아래에 만들고 git에는 커밋하지 않는다. 실행 중 문서 계약의 빈틈이 발견될 때만 focused docs contract test를 먼저 추가하고 최소 문서 보강을 커밋한다.

**Tech Stack:** Python 3.12, FastAPI runtime, PostgreSQL 16 + pgvector, Docker Compose, existing pilot rehearsal scripts, GitHub CLI/API branch protection capture, Dify UI manual dry-run, BGE-M3 closed-network scripts, Markdown/JSON evidence, pytest docs contract tests, ruff, mypy.

---

## 검토한 현재 상태

- 현재 브랜치: `main`.
- 현재 HEAD: `da33cf22392f531790010b086a43fed085cf11b2`.
- Sprint 7 PR #6 merge commit이 현재 HEAD다.
- Worktree는 계획 작성 전 기준 clean 상태였다.
- Sprint 7 완료 산출물:
  - `docs/superpowers/plans/2026-06-30-intent-routing-sprint-7.md`
  - `docs/ops/pilot-launch-readiness-checklist.md`
  - `docs/ops/pilot-go-no-go-decision-template.md`
  - `docs/ops/pilot-handoff-release-ticket-template.md`
  - `docs/pilot/csv-baseline-freeze-approval-template.md`
  - Dify, BGE, branch protection, CSV, release ticket, go/no-go docs contract tests
- Sprint 7 상태는 template과 runbook closure가 끝난 상태이며, Sprint 8은 그 template을 실제 evidence copy로 작성하는 단계다.
- Admin UI 구현과 `docs/AdminUI_Handbook/` 수정은 Sprint 8 범위에서 제외한다.

## Sprint 8 범위

포함:

- Sprint 7 launch checklist를 실제 pilot execution 순서로 실행한다.
- local rehearsal evidence를 재사용할지 새 `SERVICE_ID`로 재생성할지 판정하고, 필요하면 재생성한다.
- Dify UI dry-run completed evidence를 작성, 검수, workflow version identifier와 함께 rehearsal manifest와 release ticket에 연결한다.
- closed-network/BGE `measured-pass`를 수행하거나, host access가 없으면 `pending-host-access` 예외 승인 기록을 작성한다.
- branch protection apply/verify evidence를 authorized operator capture로 남긴다.
- rollback 또는 temporary bypass 증적은 승인된 change/incident ticket이 있을 때만 실제 실행하고, 없으면 실행하지 않았다는 final-state evidence를 남긴다.
- CSV baseline freeze approval completed copy를 작성하고 baseline comparison PASS와 release approval ID를 연결한다.
- `release-ticket.md`와 `pilot-go-no-go-decision.md` completed copy를 작성하고 reviewer command로 검수한다.
- 최종 `Go`, `Conditional Go`, `No Go` 중 하나를 evidence로 판정한다.
- 실행 중 문서/테스트 계약의 결함이 발견될 경우에만 focused docs contract test와 문서 보강을 추가한다.

제외:

- Admin UI 구현, handbook 수정, frontend 작업.
- routing scoring, threshold preset, risk/off-topic policy 변경.
- Dify workflow 자동 생성, plugin packaging, Dify API write automation.
- production IAM, OIDC, mTLS, HMAC signing, Kubernetes/OpenShift 구현.
- GitHub-hosted CI에서 실제 BGE-M3 모델 다운로드/실행.
- 승인 없는 branch protection rollback, bypass, destructive security operation.
- `var/evidence`, `var/pilot`, screenshot, workflow export, branch protection JSON snapshot, `.secret.json` 파일 커밋.

## 파일 범위

커밋 가능한 파일:

```text
docs/superpowers/plans/2026-06-30-intent-routing-sprint-8.md
```

실행 중 문서 계약 결함이 발견될 때만 수정 가능한 파일:

```text
README.md
docs/ops/pilot-launch-readiness-checklist.md
docs/ops/pilot-rehearsal.md
docs/ops/intent-routing-pilot-runbook.md
docs/ops/pilot-handoff-release-ticket-template.md
docs/ops/pilot-go-no-go-decision-template.md
docs/ops/bge-m3-evidence-template.md
docs/ops/branch-protection.md
docs/ops/branch-protection-evidence-template.md
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

커밋하지 않는 실행 산출물:

```text
var/evidence/${SERVICE_ID}/sprint-8-execution-index.md
var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.md
var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md
var/evidence/${SERVICE_ID}/dify-ui/masked-screenshot-or-export-reference.md
var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md
var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md
var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md
var/evidence/${SERVICE_ID}/release-ticket.md
var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
var/pilot/${SERVICE_ID}.state.secret.json
```

## 작업 1: Sprint 8 실행 기준과 evidence root 고정

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md`
- Read: `docs/ops/pilot-launch-readiness-checklist.md`
- Read: `docs/ops/pilot-evidence-bundle-checklist.md`
- Read: `docs/ops/pilot-handoff-release-ticket-template.md`
- Read: `docs/ops/pilot-go-no-go-decision-template.md`

- [ ] **Step 1: 실행 전 상태 확인**

Run:

```bash
git status --short --branch
git rev-parse HEAD
```

Expected:

```text
branch is main or a codex/intent-routing-sprint-8 branch
HEAD is da33cf22392f531790010b086a43fed085cf11b2 or a Sprint 8 branch descendant
no unexpected tracked file changes before evidence execution
```

- [ ] **Step 2: Sprint 8 SERVICE_ID 선택**

Use a new `SERVICE_ID` unless an existing Sprint 7 rehearsal bundle has already been reviewed and explicitly approved for reuse.

Run:

```bash
export SERVICE_ID="it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)"
export INTENT_ROUTING_ENVIRONMENT=dev
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
mkdir -p "var/evidence/${SERVICE_ID}"
```

Expected:

```text
var/evidence/${SERVICE_ID} exists
STATE_PATH points under var/pilot and ends with .secret.json
```

- [ ] **Step 3: Sprint 8 execution index 작성**

Create `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md` with this exact section structure:

```markdown
# Sprint 8 Execution Index

- SERVICE_ID:
- Repository commit:
- Execution owner:
- Evidence root: var/evidence/${SERVICE_ID}
- Admin UI implementation: excluded

## Evidence Status

| gate | status | evidence path | reviewer | approval ID | notes |
| --- | --- | --- | --- | --- | --- |
| local rehearsal | not-started | var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.md |  |  |  |
| Dify UI dry-run | not-started | var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md |  |  |  |
| BGE closed-network | not-started | var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md |  |  |  |
| branch protection | not-started | var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md |  |  |  |
| CSV baseline freeze | not-started | var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md |  |  |  |
| release ticket | not-started | var/evidence/${SERVICE_ID}/release-ticket.md |  |  |  |
| go/no-go decision | not-started | var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md |  |  |  |

## Decision Boundary

- Closed-network pilot traffic allowed before BGE measured-pass: no
- Dify pilot traffic allowed before Dify UI dry-run approval: no
- Conditional Go requires owner, approval ID, expiry, next review date, and launch boundary impact.
```

Do not put secrets, raw query text, tokens, screenshot contents, or workflow export contents in the index.

- [ ] **Step 4: execution index secret marker check**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}/sprint-8-execution-index.md"
```

Expected:

```text
no matches
```

`rg` exit code 1 with no output is expected.

## 작업 2: local rehearsal evidence 재사용 또는 재생성

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json`
- Create local only: `var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.md`
- Read: `docs/ops/pilot-evidence-bundle-checklist.md`
- Read: `docs/ops/pilot-rehearsal.md`
- Read: `scripts/run_pilot_rehearsal.py`

- [ ] **Step 1: 재사용 가능 여부 판정**

Reuse is allowed only when every item below is true:

```text
the existing manifest records final_status PASS
the existing manifest records secret_scan.passed true
the existing manifest uses csv-tier standard and required-preset balanced
the existing manifest was generated for the current launch candidate commit or an approved equivalent commit
the existing manifest has a recorded reviewer and reuse approval ID in sprint-8-execution-index.md
Dify evidence path and workflow version, if present, still match the current Dify workflow
```

If any item is false, regenerate local rehearsal evidence.

- [ ] **Step 2: local runtime environment 준비**

Run:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON="{}"
export EMBEDDING_PROVIDER=fake
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
docker compose up -d postgres
uv run alembic upgrade head
```

Expected:

```text
postgres container is running
alembic upgrade head completes successfully
```

- [ ] **Step 3: API 서버 시작**

Run in a dedicated terminal:

```bash
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

Readiness check from another terminal:

```bash
curl -fsS http://127.0.0.1:8000/readyz
```

Expected:

```text
/readyz returns a successful response
```

- [ ] **Step 4: local rehearsal 실행**

Run:

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
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Expected:

```json
{"final_status":"PASS","json_path":"var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json","markdown_path":"var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.md"}
```

Path values may be absolute or relative depending on shell invocation, but both manifest files must exist.

- [ ] **Step 5: reviewer checks 실행**

Run:

```bash
uv run python -m json.tool "var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json"
sha256sum "var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json"
find "var/evidence/${SERVICE_ID}/rehearsal" -name '*.secret.json' -print
rg -n 'Authorization: Bearer|Bearer |RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}/rehearsal"
```

Expected:

```text
json.tool prints formatted JSON
sha256sum prints one digest for pilot-rehearsal-manifest.json
find prints no .secret.json files
rg prints no matches
```

Record the manifest SHA-256 and review result in `sprint-8-execution-index.md`.

## 작업 3: Dify UI dry-run evidence 작성, 검수, rehearsal 연결

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`
- Create local only: `var/evidence/${SERVICE_ID}/dify-ui/masked-screenshot-or-export-reference.md`
- Modify local only: `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md`
- Read: `docs/integrations/dify-dry-run-evidence-template.md`
- Read: `docs/integrations/dify-dry-run-rehearsal.md`
- Read: `docs/integrations/dify-handoff-checklist.md`

- [ ] **Step 1: Dify evidence template 복사**

Run:

```bash
mkdir -p "var/evidence/${SERVICE_ID}/dify-ui"
cp docs/integrations/dify-dry-run-evidence-template.md \
  "var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md"
```

Expected:

```text
var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md exists
```

- [ ] **Step 2: Dify UI dry-run 수동 실행**

In the Dify UI, verify every row required by `docs/integrations/dify-handoff-checklist.md`:

```text
HTTP method is POST
URL points to /v1/intent-route
Timeout is 8 seconds
Authorization uses the masked intent_routing_api_key secret variable
X-Key-Id maps to approved key id variable
X-App-Id maps to approved Dify app id
X-Service-Id maps to ${SERVICE_ID}
X-Request-Id maps to workflow_run_id
Body query maps to user input
Body user_context.workflow_run_id maps to workflow_run_id
confident branch preserves trace_id, request_id, release_version
clarify branch shows clarify_question and candidates
fallback, off_topic, risk, unauthorized branches do not call disallowed business routes
401, 403, 422, 408, 5xx, timeout branches route to approved fallback or handoff
408, 5xx, timeout branches have no automatic retry loop
```

Record only masked screenshot paths, sanitized workflow export paths, observed statuses, trace IDs, request IDs, and workflow version identifier. Do not paste raw query text or secret values.

- [ ] **Step 3: Dify evidence reviewer 결과 기록**

In `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`, record:

```text
Operator result: pass, fail, or blocked
Dify UI evidence reviewer: named reviewer
Dify workflow version identifier: concrete version/export identifier
Release ticket path: var/evidence/${SERVICE_ID}/release-ticket.md
Go/no-go decision path: var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
Condition owner and follow-up approval ID when blocked
```

If Dify UI access is unavailable or any required branch is not verified, mark the result `blocked` or `fail`. Do not mark it `pass`.

- [ ] **Step 4: Dify evidence secret marker check**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}/dify-ui"
```

Expected:

```text
no matches
```

The approved phrase `intent_routing_api_key secret variable` may appear in the template, but no raw secret value may appear.

- [ ] **Step 5: Dify metadata를 포함해 rehearsal 재실행**

Run after the completed Dify evidence file exists:

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
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --dify-workflow-version "dify-workflow-export-20260630-001" \
  --dify-ui-evidence-path "var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md" \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Replace `dify-workflow-export-20260630-001` with the real workflow version identifier from the Dify UI.

Expected:

```text
pilot-rehearsal-manifest.md includes the Dify workflow version identifier
pilot-rehearsal-manifest.md includes var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md
pilot-rehearsal-manifest.md does not inline screenshot or workflow export content
secret_scan.passed is true
final_status is PASS
```

- [ ] **Step 6: execution index 업데이트**

Update `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md`:

```text
Dify UI dry-run status is pass, fail, or blocked
evidence path is var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md
reviewer is recorded
approval ID is recorded when blocked
notes include the Dify workflow version identifier
```

## 작업 4: closed-network/BGE measured-pass 또는 pending-host-access 예외 승인

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md`
- Create local only when measured: `var/evidence/${SERVICE_ID}/rehearsal/bge-package/bge-m3-package.json`
- Create local only when measured: `var/evidence/${SERVICE_ID}/rehearsal/bge-package/bge-m3-package.md`
- Create local only when measured: `var/evidence/${SERVICE_ID}/rehearsal/bge-benchmark/bge-m3-benchmark.json`
- Create local only when measured: `var/evidence/${SERVICE_ID}/rehearsal/bge-benchmark/bge-m3-benchmark.md`
- Read: `docs/ops/bge-m3-evidence-template.md`
- Read: `docs/ops/bge-m3-closed-network.md`
- Read: `docs/ops/closed-network-deployment.md`

- [ ] **Step 1: BGE evidence template 복사**

Run:

```bash
mkdir -p "var/evidence/${SERVICE_ID}/bge"
cp docs/ops/bge-m3-evidence-template.md \
  "var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md"
```

Expected:

```text
var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md exists
```

- [ ] **Step 2: host access decision 기록**

Choose exactly one path:

```text
measured-pass path: approved closed-network host, /models/bge-m3 mount, and BGE_M3_MODEL_SHA256 are available
pending-host-access path: approved closed-network host is not available before Sprint 8 closure
measured-fail path: host is available but package, benchmark, rehearsal, offline runtime, or secret scan fails
```

Record the chosen path in `sprint-8-execution-index.md` and `bge-m3-evidence.md`.

- [ ] **Step 3A: measured-pass package preflight 실행**

Run on the approved closed-network host:

```bash
export INTENT_ROUTING_ENVIRONMENT=pilot
export EMBEDDING_PROVIDER=bge-m3
export BGE_M3_MODEL_PATH=/models/bge-m3
uv run python scripts/verify_bge_m3_package.py \
  --model-path /models/bge-m3 \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal/bge-package" \
  --expected-sha256 "${BGE_M3_MODEL_SHA256}"
```

Expected:

```text
bge-m3-package.json exists
bge-m3-package.md exists
computed SHA-256 matches BGE_M3_MODEL_SHA256
offline_required is true
```

- [ ] **Step 3B: measured-pass benchmark 실행**

Run:

```bash
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/models/bge-m3 \
BGE_M3_BATCH_SIZE=16 \
uv run python scripts/benchmark_bge_m3.py \
  --model-path /models/bge-m3 \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal/bge-benchmark" \
  --batch-size 16
```

Expected:

```text
bge-m3-benchmark.json exists
bge-m3-benchmark.md exists
dimension is 1024
batch_size is 16
max_tokens is 256
latency_ms.p50 is recorded
latency_ms.p95 is recorded
max_rss_mb is recorded
```

- [ ] **Step 3C: measured-pass closed-network rehearsal 실행**

Run:

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
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 "${BGE_M3_MODEL_SHA256}" \
  --run-bge-benchmark \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Expected:

```text
pilot-rehearsal-manifest.json final_status is PASS
secret_scan.passed is true
bge-package step status is PASS
bge-benchmark step status is PASS
```

Set BGE evidence status to `measured-pass` only when package preflight, benchmark, closed-network rehearsal, offline runtime confirmation, and secret scan all pass.

- [ ] **Step 4: pending-host-access 예외 승인 기록**

Use this step only when the approved closed-network host is unavailable. In `var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md`, record real values for:

```text
Status: pending-host-access
Exception approval ID: release, operations, or security approval identifier
Exception owner: named owner
Approved by: release owner and operations or security reviewer
Approval timestamp: concrete timestamp
Expires before pilot traffic: yes
Next measurement date: concrete calendar date
Decision impact: closed-network pilot traffic blocked until measured-pass evidence is attached
```

Expected:

```text
release-ticket.md will link var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md
pilot-go-no-go-decision.md will record Conditional Go only if closed-network pilot traffic remains blocked
```

- [ ] **Step 5: BGE evidence secret marker check**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}/bge"
```

Expected:

```text
no matches
```

## 작업 5: branch protection apply/verify와 rollback evidence 작성

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md`
- Create local only: `var/evidence/${SERVICE_ID}/branch-protection/main-protection.json`
- Read: `docs/ops/branch-protection.md`
- Read: `docs/ops/branch-protection-evidence-template.md`
- Read: `docs/ops/ci-verification.md`

- [ ] **Step 1: branch protection evidence template 복사**

Run:

```bash
mkdir -p "var/evidence/${SERVICE_ID}/branch-protection"
cp docs/ops/branch-protection-evidence-template.md \
  "var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md"
```

Expected:

```text
var/evidence/${SERVICE_ID}/branch-protection/branch-protection-evidence.md exists
```

- [ ] **Step 2: authorized operator capture 실행**

Run from an authenticated operator shell with repository admin permission:

```bash
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  > "var/evidence/${SERVICE_ID}/branch-protection/main-protection.json"
```

Expected:

```text
main-protection.json exists
operator permission result is authorized
```

If GitHub returns a permission error, record `operator-not-permitted` as evidence request only. It does not satisfy pilot go/no-go.

- [ ] **Step 3: structured JSON verification 실행**

Run:

```bash
uv run python - "var/evidence/${SERVICE_ID}/branch-protection/main-protection.json" <<'PY'
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
if "CI / verify" not in contexts:
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

- [ ] **Step 4: apply/verify fields 기록**

In `branch-protection-evidence.md`, record:

```text
Evidence type: apply or verify
Authorized operator: named operator
Operator permission result: authorized
Rule snapshot path: var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
Verification output: branch protection capture verified
Required check evidence: CI / verify
Final branch protection state: CI / verify required, strict true, enforce admins enabled
```

- [ ] **Step 5: rollback 또는 temporary bypass evidence 범위 기록**

Do not change branch protection or bypass checks without an approved incident/change ticket. Choose one record:

```text
No rollback executed: final state was verified and no bypass was performed.
Rollback executed: approval ID, exact commit SHA, workflow_dispatch rerun URL, pilot-e2e-evidence artifact review result, no .secret.json confirmation, and final branch protection state are recorded.
```

If no rollback was executed, record the exact sentence below:

```text
Rollback or temporary bypass was not executed in Sprint 8; final branch protection state was verified from main-protection.json and structured JSON verification.
```

- [ ] **Step 6: branch protection evidence secret marker check**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}/branch-protection"
```

Expected:

```text
no matches
```

## 작업 6: CSV baseline freeze approval 확정

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md`
- Read: `docs/pilot/csv-baseline-freeze-approval-template.md`
- Read: `docs/pilot/csv-baseline-refresh-policy.md`
- Read: `docs/pilot/it-helpdesk-pilot-baseline.json`
- Read: `var/evidence/${SERVICE_ID}/rehearsal/csv-baseline/csv-baseline-comparison.md`

- [ ] **Step 1: CSV baseline comparison evidence 확인**

Run:

```bash
rg -n 'PASS|passed|allowed_new_failures|allowed_new_reviews|balanced' \
  "var/evidence/${SERVICE_ID}/rehearsal/csv-baseline/csv-baseline-comparison.md"
```

Expected:

```text
comparison report confirms PASS
allowed_new_failures remains 0
allowed_new_reviews remains 0
balanced preset evidence is present
```

- [ ] **Step 2: checked-in baseline secret marker check**

Run:

```bash
rg -n 'query|authorization|api_key|Bearer |encrypted_dek|ciphertext|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON' docs/pilot/it-helpdesk-pilot-baseline.json
```

Expected:

```text
no matches
```

- [ ] **Step 3: freeze approval template 복사**

Run:

```bash
cp docs/pilot/csv-baseline-freeze-approval-template.md \
  "var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md"
```

Expected:

```text
var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md exists
```

- [ ] **Step 4: freeze approval record 작성**

Record real values:

```text
Baseline file: docs/pilot/it-helpdesk-pilot-baseline.json
Pilot CSV: standard 50-row CSV
Preset: balanced
Comparison result: CSV baseline comparison PASS
Refresh status: refresh not approved
Freeze decision: checked-in baseline remains frozen for pilot launch
Accepted behavior change: none; if behavior changed, stop and attach a policy-approved refresh approval instead
Freeze approval ID: real release approval ID
Release owner: named owner
QA or security reviewer: named reviewer
Review timestamp: concrete timestamp
Linked from release-ticket.md: yes after Task 7
```

If behavior changed, stop this freeze path and use `docs/pilot/csv-baseline-refresh-policy.md` with a policy-approved refresh approval instead.

- [ ] **Step 5: freeze approval secret marker check**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}/csv-baseline-freeze-approval.md"
```

Expected:

```text
no matches
```

## 작업 7: release-ticket.md 실제 작성과 검수

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/release-ticket.md`
- Read: `docs/ops/pilot-handoff-release-ticket-template.md`
- Read: `docs/ops/pilot-launch-readiness-checklist.md`
- Read: `docs/ops/intent-routing-pilot-runbook.md`

- [ ] **Step 1: release ticket template 복사**

Run:

```bash
cp docs/ops/pilot-handoff-release-ticket-template.md \
  "var/evidence/${SERVICE_ID}/release-ticket.md"
```

Expected:

```text
var/evidence/${SERVICE_ID}/release-ticket.md exists
```

- [ ] **Step 2: release ticket에 evidence reference만 기록**

Record paths, hashes, statuses, reviewers, owners, approval IDs, and gate summary only:

```text
commit SHA: current release candidate commit
PR URL: Sprint 8 PR or release review URL when available
CI / verify result: pass with run URL
local rehearsal manifest path and sha256
local rehearsal final_status PASS
local rehearsal secret_scan.passed true
Dify workflow version identifier
Dify UI evidence path
Dify UI dry-run evidence reviewer
BGE evidence status: measured-pass, measured-fail, or pending-host-access
BGE exception approval ID when pending-host-access
branch protection evidence path
main-protection.json path
branch protection capture verified
CSV baseline comparison PASS
CSV baseline freeze approval path and approval ID
security and incident rehearsal evidence references when available
blocked gates and Conditional Go conditions when present
```

Do not paste screenshot contents, workflow export contents, raw query text, API keys, bearer tokens, KEK material, encrypted DEKs, or ciphertext.

- [ ] **Step 3: required evidence reference scan**

Run:

```bash
required_release_refs=$(
  printf '%s' \
    'PASS|CI / verify|pilot-rehearsal-manifest.md|' \
    'Dify workflow version identifier|BGE evidence status|' \
    'branch protection evidence|CSV baseline|go/no-go'
)
rg -n "${required_release_refs}" \
  "var/evidence/${SERVICE_ID}/release-ticket.md"
```

Expected:

```text
rg prints required evidence references
```

- [ ] **Step 4: forbidden marker scan**

Run:

```bash
forbidden_release_markers=$(
  printf '%s' \
    'Bearer |Authorization: Bearer|' \
    'RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|' \
    'api_key=|intent_routing_api_key|' \
    'query_raw|text_raw|encrypted_dek|ciphertext|' \
    'irt_live_|irt_secret'
)
rg -n "${forbidden_release_markers}" \
  "var/evidence/${SERVICE_ID}/release-ticket.md"
```

Expected:

```text
no matches
```

`rg` exit code 1 with no output is expected for the forbidden marker scan.

## 작업 8: pilot-go-no-go-decision.md 실제 작성과 최종 판정

**Files:**

- Create local only: `var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md`
- Read: `docs/ops/pilot-go-no-go-decision-template.md`
- Read: `var/evidence/${SERVICE_ID}/release-ticket.md`

- [ ] **Step 1: decision template 복사**

Run:

```bash
cp docs/ops/pilot-go-no-go-decision-template.md \
  "var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md"
```

Expected:

```text
var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md exists
```

- [ ] **Step 2: decision value 선택**

Use exactly one value:

```text
Go
Conditional Go
No Go
```

Decision rules:

```text
Go requires CI / verify pass, local rehearsal PASS, secret_scan.passed true, Dify UI dry-run reviewer approval, BGE measured-pass before closed-network pilot traffic, authorized branch protection evidence for main, CSV baseline comparison PASS, CSV freeze approval or policy-approved refresh approval, release ticket review pass, and required owner approvals.
Conditional Go is allowed only for approved bounded conditions with owner, approval ID, expiry, next review date, and launch boundary impact.
Conditional Go cannot allow traffic across a boundary blocked by missing, failed, unsafe, or unapproved evidence.
No Go is required when required evidence is missing, failed, unsafe, or unapproved.
measured-fail remains No Go until corrected evidence passes.
pending-host-access can support Conditional Go only when closed-network pilot traffic remains blocked until measured-pass evidence is attached.
```

- [ ] **Step 3: launch boundary 작성**

Record:

```text
Closed-network pilot traffic allowed: yes only when BGE measured-pass is attached
Dify pilot traffic allowed: yes only when Dify UI dry-run evidence is approved
Pilot traffic boundary: exact environment and traffic scope
Blocked gates: every blocked gate with owner and required unblock evidence
Approval record: Engineering, Operations, Security, Dify owner, Pilot owner
Admin UI excluded from Sprint 8 execution
```

- [ ] **Step 4: decision required reference scan**

Run:

```bash
rg -n 'Go|No Go|Conditional Go|release-ticket.md|Dify UI dry-run evidence|BGE evidence status|branch protection evidence|CSV baseline freeze approval|secret_scan.passed true' \
  "var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md"
```

Expected:

```text
rg prints required decision references
```

- [ ] **Step 5: decision forbidden marker scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' \
  "var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md"
```

Expected:

```text
no matches
```

## 작업 9: 문서 계약 gap 발견 시 최소 보강

**Files:**

- Modify only when a real gap is found: files listed in "실행 중 문서 계약 결함이 발견될 때만 수정 가능한 파일"

- [ ] **Step 1: gap 여부 판단**

Treat an item as a docs contract gap only when:

```text
the current Sprint 7 template lacks a field required to record actual Sprint 8 evidence
the current reviewer command cannot verify the evidence it claims to verify
the current runbook command does not match script --help output
the current docs allow unsafe evidence content that Sprint 8 must reject
```

Do not edit docs for wording preference only.

- [ ] **Step 2: failing focused docs contract test 작성**

If the gap is in Dify evidence, start with:

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py -q
```

If the gap is in BGE evidence, start with:

```bash
uv run pytest tests/unit/test_bge_evidence_template_docs_contract.py -q
```

If the gap is in branch protection, start with:

```bash
uv run pytest tests/unit/test_branch_protection_evidence_template_docs_contract.py tests/unit/test_branch_protection_docs_contract.py -q
```

If the gap is in CSV freeze, start with:

```bash
uv run pytest tests/unit/test_csv_baseline_freeze_approval_docs_contract.py -q
```

If the gap is in release or decision records, start with:

```bash
uv run pytest tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_go_no_go_decision_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected before the doc fix:

```text
at least one focused assertion fails for the missing contract
```

- [ ] **Step 3: minimal document fix 작성**

Patch only the source document required by the failing test. Keep the fix as:

```text
evidence path
required status field
reviewer or approval ID field
safe reviewer command
explicit go/no-go gate
```

Do not edit `docs/AdminUI_Handbook/`.

- [ ] **Step 4: focused test 통과**

Run the focused command from Step 2 again.

Expected:

```text
focused docs contract test passes
```

- [ ] **Step 5: gap fix commit**

If docs/tests changed, commit them separately:

```bash
git add README.md docs/ops docs/integrations docs/pilot tests/unit
git commit -m "docs: tighten Sprint 8 evidence execution contract"
```

Expected:

```text
commit includes only docs/tests
no var/evidence, var/pilot, .secret.json, screenshot, workflow export, or branch snapshot files are staged
```

## 작업 10: 최종 검증과 evidence handoff

**Files:**

- Read local only: `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md`
- Read local only: `var/evidence/${SERVICE_ID}/release-ticket.md`
- Read local only: `var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md`

- [ ] **Step 1: focused docs tests 실행**

Run:

```bash
uv run pytest \
  tests/unit/test_pilot_launch_readiness_docs_contract.py \
  tests/unit/test_dify_dry_run_docs_contract.py \
  tests/unit/test_bge_evidence_template_docs_contract.py \
  tests/unit/test_branch_protection_docs_contract.py \
  tests/unit/test_branch_protection_evidence_template_docs_contract.py \
  tests/unit/test_csv_baseline_refresh_policy_docs_contract.py \
  tests/unit/test_csv_baseline_freeze_approval_docs_contract.py \
  tests/unit/test_pilot_handoff_release_template_docs_contract.py \
  tests/unit/test_pilot_go_no_go_decision_docs_contract.py \
  tests/unit/test_pilot_evidence_bundle_docs_contract.py \
  tests/unit/test_pilot_rehearsal_docs_contract.py \
  tests/unit/test_dify_handoff_docs_contract.py \
  tests/unit/test_operator_docs_contract.py \
  -q
```

Expected:

```text
all focused docs tests pass
```

- [ ] **Step 2: static verification 실행**

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

- [ ] **Step 3: regression tests 실행**

Run with PostgreSQL running:

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run pytest -q
```

Expected:

```text
pytest passes
```

- [ ] **Step 4: generated evidence final secret marker scan**

Run:

```bash
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' "var/evidence/${SERVICE_ID}"
find "var/evidence/${SERVICE_ID}" -name '*.secret.json' -print
```

Expected:

```text
rg prints no matches
find prints no .secret.json files
```

The approved documentation label `intent_routing_api_key secret variable` may appear in Dify template-derived files, but no raw secret value may appear.

- [ ] **Step 5: git exclusion 확인**

Run:

```bash
git status --short
git diff --name-only | rg '^docs/AdminUI_Handbook/'
git status --short | rg 'var/evidence|var/pilot|\.secret\.json|main-protection\.json|dify-ui'
```

Expected:

```text
no Admin UI diff
no var/evidence, var/pilot, .secret.json, main-protection.json, or Dify UI evidence files staged or tracked
```

- [ ] **Step 6: handoff summary 작성**

Update `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md` with:

```text
final decision value
release-ticket.md path
pilot-go-no-go-decision.md path
local rehearsal manifest hash
Dify workflow version identifier
BGE status and traffic boundary
branch protection verification result
CSV freeze approval ID
all reviewer command outcomes
```

Expected:

```text
execution index can be used by release reviewers to locate every evidence file without exposing secrets
```

## 테스트 전략

- **Focused docs contract tests:** Sprint 7 문서 계약이 Sprint 8 실행 중 깨지지 않았는지 검증한다. 문서 gap을 수정한 경우 해당 focused test가 먼저 실패하고 수정 후 통과해야 한다.
- **Static checks:** `uv run ruff check .`, `uv run mypy src tests`, `docker compose --profile runtime config`.
- **Regression tests:** PostgreSQL 준비 후 `uv run pytest -q`.
- **Script contract checks:** 계획서 명령은 `scripts/run_pilot_rehearsal.py --help`, `scripts/verify_bge_m3_package.py --help`, `scripts/benchmark_bge_m3.py --help`의 현재 CLI와 맞아야 한다.
- **Manual evidence checks:** Dify UI dry-run, BGE measured/exception evidence, branch protection snapshot, CSV freeze approval, release ticket, go/no-go decision record를 reviewer command로 검수한다.
- **Secret safety:** 모든 generated evidence는 bearer token, KEK, raw query, API key, encrypted DEK, ciphertext, live key marker, `.secret.json`을 포함하지 않아야 한다.

## Sprint 8 Acceptance Criteria

- `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md`가 모든 gate 상태, evidence path, reviewer, approval ID, final decision을 연결한다.
- local rehearsal evidence는 재사용 승인 또는 새 실행으로 `final_status PASS`와 `secret_scan.passed true`가 확인된다.
- Dify UI dry-run evidence가 completed copy로 작성되고 workflow version identifier, reviewer, release ticket link, go/no-go link가 기록된다.
- BGE evidence가 `measured-pass`로 완료되거나, closed-network host 미가용 시 `pending-host-access` 예외 승인 ID, owner, expiry, next measurement date, traffic blocking impact를 포함한다.
- Branch protection evidence는 authorized operator capture와 `branch protection capture verified` 결과를 포함한다.
- Rollback/bypass가 실제 실행된 경우 approval ID, exact commit SHA, workflow_dispatch rerun URL, artifact review result, final branch protection state가 기록된다.
- Rollback/bypass가 실행되지 않은 경우 실행하지 않았고 final state를 verified했다는 evidence가 기록된다.
- CSV baseline freeze approval completed copy가 baseline comparison PASS, refresh not approved, approval ID, release owner, QA/security reviewer를 포함한다.
- `var/evidence/${SERVICE_ID}/release-ticket.md`가 evidence links only 방식으로 작성되고 required reference scan은 통과, forbidden marker scan은 no matches다.
- `var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md`가 `Go`, `Conditional Go`, `No Go` 중 하나를 판정하고 blocked gate owner, approval ID, expiry, next review date, launch boundary impact를 기록한다.
- Focused docs tests, static verification, regression tests가 통과한다.
- `docs/AdminUI_Handbook/`, `var/evidence`, `var/pilot`, `.secret.json`, screenshots, workflow exports, `main-protection.json`은 커밋되지 않는다.

## 수동 검수 절차

1. `SERVICE_ID`와 `STATE_PATH`를 정하고 `var/evidence/${SERVICE_ID}/sprint-8-execution-index.md`를 만든다.
2. local rehearsal evidence를 재사용할지 판정한다. 재사용 기준을 만족하지 못하면 새 `SERVICE_ID` 또는 같은 `SERVICE_ID`로 rehearsal을 재생성한다.
3. `pilot-rehearsal-manifest.json`에서 `final_status PASS`, `secret_scan.passed true`를 확인하고 manifest SHA-256을 기록한다.
4. Dify UI dry-run completed evidence를 작성하고 Dify workflow version identifier와 reviewer approval을 기록한다.
5. Dify metadata를 `run_pilot_rehearsal.py --dify-workflow-version --dify-ui-evidence-path`로 manifest에 연결한다.
6. Closed-network host가 준비되었으면 BGE package preflight, benchmark, closed-network rehearsal을 실측한다.
7. Closed-network host가 없으면 `pending-host-access` 예외 승인 ID, owner, expiry, next measurement date를 기록하고 closed-network pilot traffic blocked를 decision record에 남긴다.
8. Authorized operator가 branch protection snapshot을 캡처하고 structured JSON verification이 `branch protection capture verified`를 출력하는지 확인한다.
9. Rollback/bypass를 실제 수행할 승인된 incident/change ticket이 없으면 수행하지 않았다고 기록하고 final branch protection state를 확인한다.
10. CSV baseline comparison PASS를 확인하고 freeze approval completed copy를 작성한다.
11. `release-ticket.md`를 작성하고 required reference scan과 forbidden marker scan을 실행한다.
12. `pilot-go-no-go-decision.md`를 작성하고 최종 `Go`, `Conditional Go`, `No Go` 판정을 남긴다.
13. `var/evidence/${SERVICE_ID}` 전체에 forbidden marker scan을 실행한다.
14. `git status --short`로 runtime evidence가 staged/tracked 되지 않았고 Admin UI diff가 없는지 확인한다.

## 사용자가 선택해야 하는 정책/범위 결정

- **BGE launch boundary:** closed-network host access를 확보해 `measured-pass`까지 Sprint 8에 포함할지, host 미가용을 인정하고 `pending-host-access` 예외 승인으로 Conditional Go 범위에 둘지 선택해야 한다. 추천은 host가 준비되어 있으면 measured-pass, 준비되지 않았으면 closed-network pilot traffic을 막는 Conditional Go다.
- **Dify evidence 형태:** masked screenshot, sanitized workflow export, 또는 둘 다 허용할지 선택해야 한다. 추천은 둘 다 허용하되 release ticket과 manifest에는 path와 workflow version identifier만 기록하는 방식이다.
- **Branch protection rollback drill:** 실제 rollback/bypass drill을 수행할지 선택해야 한다. 추천은 승인된 incident/change ticket이 없으면 실제 bypass 없이 apply/verify evidence와 final-state evidence만 남기는 방식이다.
- **CSV freeze 승인자:** freeze approval ID 발급자와 reviewer를 지정해야 한다. 추천은 release owner 1명과 QA 또는 security reviewer 1명이다.
- **Final decision authority:** 최종 decision owner와 approval record 서명자를 지정해야 한다. 추천은 Pilot owner가 decision owner이고 Engineering, Operations, Security, Dify owner가 approval record에 서명하는 구조다.

## 실행 방식 추천

Subagent-Driven 실행을 추천한다. Dify, BGE, branch protection, CSV freeze, release decision은 서로 다른 운영 surface와 reviewer를 가지므로 task별 fresh subagent가 산출물을 독립 검수하기 좋다. 다만 같은 `SERVICE_ID`와 같은 `var/evidence/${SERVICE_ID}` evidence tree를 공유하는 final release ticket, go/no-go decision, 전체 secret scan은 Inline Execution으로 한 세션에서 이어서 수행하는 편이 안전하다.
