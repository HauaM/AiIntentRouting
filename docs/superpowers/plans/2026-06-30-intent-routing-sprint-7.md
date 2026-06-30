# Sprint 7: Pilot Launch Readiness & Evidence Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 6에서 확정한 증적 템플릿을 실제 파일럿 launch readiness 판단에 필요한 작성, 검수, 예외 승인, release ticket, go/no-go 기록으로 닫는다.

**Architecture:** 라우팅 API, threshold preset, Dify HTTP 계약, BGE-M3 runtime behavior, branch protection rule 자체는 새로 설계하지 않는다. Sprint 7은 기존 rehearsal wrapper와 Sprint 6 evidence template을 source of truth로 두고, 운영자가 실제 증적을 작성한 뒤 release ticket과 최종 go/no-go decision record로 연결하는 launch closure layer를 문서화한다. 생성된 evidence copy, screenshot, workflow export, branch snapshot, release ticket dry-fill은 `var/evidence/...` 아래에 두고 git에는 커밋하지 않는다.

**Tech Stack:** Python 3.12, FastAPI runtime, PostgreSQL 16 + pgvector, Docker Compose, existing rehearsal scripts, GitHub CLI/API evidence capture, Dify UI manual dry-run, Markdown/JSON evidence, pytest docs contract tests, ruff, mypy.

---

## 검토한 현재 상태

- 현재 브랜치: `main`, 원격 추적: `origin/main`.
- 현재 `main` HEAD: `bb4b9e904a1526830559e6b957063a754a12a57f`.
- `git status --short --branch` 기준 worktree는 clean 상태다.
- PR #4 Sprint 6와 PR #5 Admin UI Handbook이 main에 병합되어 있다.
- Sprint 6 sign-off는 승인되었고 pilot readiness는 `Conditional Go`다.
- Sprint 7에서는 `docs/AdminUI_Handbook/`을 참고 자료로만 취급하고 Admin UI 구현이나 handbook 수정은 제외한다.
- Sprint 6 산출물은 다음 운영 기준을 제공한다.
  - `docs/ops/pilot-evidence-bundle-checklist.md`: local rehearsal bundle 검수 기준.
  - `docs/integrations/dify-dry-run-evidence-template.md`: Dify UI dry-run 작성 양식.
  - `docs/integrations/dify-dry-run-rehearsal.md`: Dify UI dry-run 실행 순서와 wrapper 연결.
  - `docs/ops/bge-m3-evidence-template.md`: closed-network/BGE `measured-pass`, `measured-fail`, `pending-host-access` 증적 양식.
  - `docs/ops/branch-protection-evidence-template.md`: `main` branch protection 적용, snapshot, rollback/bypass 증적 양식.
  - `docs/ops/branch-protection.md`: required check `CI / verify` 적용/rollback runbook.
  - `docs/pilot/csv-baseline-refresh-policy.md`: standard 50-row, `balanced` baseline freeze/refresh 정책.
  - `docs/ops/pilot-handoff-release-ticket-template.md`: release ticket template과 go gate.
- 기존 테스트는 docs contract test로 필수 문구, 링크, secret-scan 안전성을 고정한다.

## Sprint 7 범위

포함:

- Dify UI dry-run 실제 증적 작성 절차와 release ticket 연결을 확정한다.
- Closed-network/BGE benchmark 실측 절차 또는 `pending-host-access` 예외 승인 기록을 release decision에 반영한다.
- Branch protection 실제 적용, rule snapshot, rollback/bypass 증적 캡처 절차를 실행 가능하게 정리한다.
- CSV baseline freeze 승인 기록을 명확히 하고 refresh 없이 파일럿을 진행하는 경우의 승인 evidence를 남긴다.
- Pilot handoff/release ticket 실제 작성, 검수, secret scan, reviewer sign-off 흐름을 확정한다.
- Pilot go/no-go 최종 판정 문서를 별도 decision record로 남기고 `Conditional Go`의 조건을 구체화한다.
- 필요 시 local rehearsal evidence를 새 `SERVICE_ID`로 재생성하고 검수하는 절차를 포함한다.
- 모든 신규/변경 운영 문서는 focused docs contract test로 고정한다.

제외:

- Admin UI 구현과 `docs/AdminUI_Handbook/` 수정.
- 라우팅 점수식, threshold preset, risk/off_topic policy 변경.
- Dify plugin packaging, Dify workflow 자동 생성.
- production IAM, OIDC, mTLS, HMAC signing, Kubernetes/OpenShift 구현.
- GitHub-hosted CI에서 실제 BGE-M3 모델 다운로드/실행.
- KEK rewrap execute, retention execute, API key revoke 같은 destructive 운영 동작 자동화.
- `var/evidence/...`, `var/pilot/*.secret.json`, screenshot, workflow export, branch protection JSON snapshot 커밋.

## 파일 범위

새로 만들 파일:

```text
docs/ops/pilot-launch-readiness-checklist.md
docs/ops/pilot-go-no-go-decision-template.md
docs/pilot/csv-baseline-freeze-approval-template.md
tests/unit/test_pilot_launch_readiness_docs_contract.py
tests/unit/test_pilot_go_no_go_decision_docs_contract.py
tests/unit/test_csv_baseline_freeze_approval_docs_contract.py
```

수정할 파일:

```text
README.md
docs/ops/pilot-rehearsal.md
docs/ops/intent-routing-pilot-runbook.md
docs/ops/pilot-evidence-bundle-checklist.md
docs/ops/pilot-handoff-release-ticket-template.md
docs/ops/bge-m3-evidence-template.md
docs/ops/branch-protection-evidence-template.md
docs/ops/branch-protection.md
docs/pilot/csv-baseline-refresh-policy.md
docs/pilot/README.md
docs/integrations/dify-dry-run-evidence-template.md
docs/integrations/dify-dry-run-rehearsal.md
docs/integrations/dify-handoff-checklist.md
tests/unit/test_dify_dry_run_docs_contract.py
tests/unit/test_bge_evidence_template_docs_contract.py
tests/unit/test_branch_protection_evidence_template_docs_contract.py
tests/unit/test_csv_baseline_refresh_policy_docs_contract.py
tests/unit/test_pilot_handoff_release_template_docs_contract.py
```

원칙:

- `docs/ops/pilot-launch-readiness-checklist.md`는 Sprint 7의 top-level 운영 순서다.
- `docs/ops/pilot-go-no-go-decision-template.md`는 최종 판정 기록이다.
- `docs/ops/pilot-handoff-release-ticket-template.md`는 release ticket 본문이고, go/no-go decision record를 링크한다.
- `docs/pilot/csv-baseline-freeze-approval-template.md`는 baseline을 refresh하지 않고 freeze 상태로 유지하는 승인 evidence다.
- Sprint 7에서 채운 evidence copy는 `var/evidence/${SERVICE_ID}/...`에만 저장한다.
- 문서 템플릿에는 secret, raw query, bearer token, KEK, ciphertext, encrypted DEK를 붙여 넣지 않는다.
- `docs/AdminUI_Handbook/` 경로는 diff에 없어야 한다.

## 작업 1: Pilot Launch Readiness Checklist 신설

**Files:**

- Create: `docs/ops/pilot-launch-readiness-checklist.md`
- Create: `tests/unit/test_pilot_launch_readiness_docs_contract.py`
- Modify: `README.md`
- Modify: `docs/ops/pilot-rehearsal.md`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Modify: `docs/ops/pilot-evidence-bundle-checklist.md`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_pilot_launch_readiness_docs_contract.py`를 추가한다.

```python
from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "docs/ops/pilot-launch-readiness-checklist.md"
CHECKLIST_PATH = "docs/ops/pilot-launch-readiness-checklist.md"


def test_pilot_launch_readiness_checklist_contains_required_contract() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")

    for expected in (
        CHECKLIST_PATH,
        "Pilot Launch Readiness & Evidence Closure",
        "Admin UI excluded from Sprint 7",
        "Dify UI dry-run evidence",
        "Dify workflow version identifier",
        "release-ticket.md",
        "BGE evidence status",
        "measured-pass",
        "pending-host-access exception approval",
        "branch protection evidence",
        "CI / verify",
        "CSV baseline freeze approval",
        "local rehearsal regeneration",
        "pilot go/no-go decision record",
        "Conditional Go",
        "go requires",
        "no secrets",
        "no raw query text",
    ):
        assert expected in text


def test_pilot_launch_readiness_checklist_contains_required_sections() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")

    for heading in (
        "# Pilot Launch Readiness Checklist",
        "## Scope",
        "## Evidence Closure Order",
        "## Local Rehearsal Regeneration",
        "## Dify UI Dry-Run Closure",
        "## Closed-Network BGE Closure",
        "## Branch Protection Closure",
        "## CSV Baseline Freeze Closure",
        "## Release Ticket Review",
        "## Go/No-Go Decision",
        "## Failure Handling",
        "## Files That Must Not Be Committed",
    ):
        assert heading in text


def test_pilot_launch_readiness_checklist_is_secret_scan_safe(tmp_path: Path) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[CHECKLIST])

    assert result == SecretScanResult(passed=True, findings=[])


def test_pilot_launch_readiness_checklist_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
        ROOT / "docs/ops/intent-routing-pilot-runbook.md",
        ROOT / "docs/ops/pilot-evidence-bundle-checklist.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert CHECKLIST_PATH in text
```

Run:

```bash
uv run pytest tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: FAIL because `docs/ops/pilot-launch-readiness-checklist.md` does not exist yet.

- [ ] **Step 2: launch readiness checklist 작성**

`docs/ops/pilot-launch-readiness-checklist.md`에 아래 섹션과 운영 순서를 작성한다.

```text
# Pilot Launch Readiness Checklist
## Scope
## Evidence Closure Order
## Local Rehearsal Regeneration
## Dify UI Dry-Run Closure
## Closed-Network BGE Closure
## Branch Protection Closure
## CSV Baseline Freeze Closure
## Release Ticket Review
## Go/No-Go Decision
## Failure Handling
## Files That Must Not Be Committed
```

필수 문구:

```text
Admin UI excluded from Sprint 7 pilot launch readiness.
Complete this checklist before marking pilot readiness as go.
Conditional Go is allowed only when each remaining condition has an owner, an approval ID, and a blocking impact recorded in the go/no-go decision record.
The filled release ticket path is var/evidence/${SERVICE_ID}/release-ticket.md.
The pilot go/no-go decision record path is var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md.
```

Evidence closure order는 아래 순서로 고정한다.

```text
1. Regenerate or review local rehearsal evidence.
2. Complete Dify UI dry-run evidence and record the Dify workflow version identifier.
3. Complete closed-network BGE measured evidence or record pending-host-access exception approval.
4. Capture branch protection evidence for main and CI / verify.
5. Record CSV baseline freeze approval or policy-approved refresh approval.
6. Dry-fill the release ticket and run secret-scan review commands.
7. Write the pilot go/no-go decision record.
```

- [ ] **Step 3: 기존 문서 링크 추가**

다음 문서에 `docs/ops/pilot-launch-readiness-checklist.md` 링크를 추가한다.

```text
README.md
docs/ops/pilot-rehearsal.md
docs/ops/intent-routing-pilot-runbook.md
docs/ops/pilot-evidence-bundle-checklist.md
```

문구는 Sprint 6 checklist가 bundle review 기준이고 Sprint 7 checklist가 launch closure 기준임을 구분한다.

- [ ] **Step 4: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: commit**

```bash
git add README.md docs/ops/pilot-launch-readiness-checklist.md docs/ops/pilot-rehearsal.md docs/ops/intent-routing-pilot-runbook.md docs/ops/pilot-evidence-bundle-checklist.md tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: add pilot launch readiness checklist"
```

## 작업 2: Dify UI Dry-Run Evidence 실제 작성 흐름 확정

**Files:**

- Modify: `docs/integrations/dify-dry-run-evidence-template.md`
- Modify: `docs/integrations/dify-dry-run-rehearsal.md`
- Modify: `docs/integrations/dify-handoff-checklist.md`
- Modify: `docs/ops/pilot-handoff-release-ticket-template.md`
- Modify: `docs/ops/pilot-launch-readiness-checklist.md`
- Modify: `tests/unit/test_dify_dry_run_docs_contract.py`
- Modify: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_launch_readiness_docs_contract.py`

- [ ] **Step 1: docs contract test 확장**

`tests/unit/test_dify_dry_run_docs_contract.py`에 아래 필수 문자열을 추가한다.

```text
var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md
release-ticket.md
pilot-go-no-go-decision.md
operator result must be pass, fail, or blocked
Dify UI evidence reviewer
masked screenshot or sanitized workflow export
do not attach unmasked screenshots
```

`tests/unit/test_pilot_handoff_release_template_docs_contract.py`에 아래 필수 문자열을 추가한다.

```text
Dify UI dry-run evidence reviewer
Dify evidence linked from release ticket
Dify condition owner
```

Run:

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py -q
```

Expected: FAIL because the docs do not yet contain the new Sprint 7 closure terms.

- [ ] **Step 2: Dify evidence template 보강**

`docs/integrations/dify-dry-run-evidence-template.md`의 `## Approval` 섹션에 아래 필드를 추가한다.

```text
- Operator result: pass / fail / blocked
- Dify UI evidence reviewer:
- Release ticket path: var/evidence/${SERVICE_ID}/release-ticket.md
- Go/no-go decision path: var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
- Condition owner, if blocked:
- Follow-up approval ID, if blocked:
```

`## Evidence Paths` 섹션은 아래 기준을 명시한다.

```text
Use var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md for the completed copy.
Evidence may be a masked screenshot, a sanitized workflow export, or both when the reviewer allows both forms.
Do not attach unmasked screenshots, raw API keys, raw secret variable values, raw query text, or workflow exports containing secret material.
```

- [ ] **Step 3: Dify rehearsal 문서에 release ticket 연결 추가**

`docs/integrations/dify-dry-run-rehearsal.md`에 아래 release closure 순서를 추가한다.

```text
1. Copy docs/integrations/dify-dry-run-evidence-template.md to var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md.
2. Complete every decision branch and error branch row.
3. Record the Dify workflow version identifier.
4. Run scripts/run_pilot_rehearsal.py with --dify-workflow-version and --dify-ui-evidence-path.
5. Confirm pilot-rehearsal-manifest.md records only the version identifier and evidence path.
6. Copy the Dify evidence path, reviewer, and condition owner into var/evidence/${SERVICE_ID}/release-ticket.md.
7. Copy the Dify status into var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md.
```

- [ ] **Step 4: Dify handoff checklist와 release ticket template 보강**

`docs/integrations/dify-handoff-checklist.md`와 `docs/ops/pilot-handoff-release-ticket-template.md`에 아래 gate를 추가한다.

```text
go requires Dify UI dry-run evidence reviewer approval.
go requires the Dify UI evidence path to be linked from release-ticket.md.
blocked Dify evidence requires a condition owner and approval ID before Conditional Go.
```

- [ ] **Step 5: 수동 검수 절차 실행**

Dify UI 접근 가능한 operator가 아래 흐름을 실행한다.

```bash
mkdir -p var/evidence/${SERVICE_ID}/dify-ui
cp docs/integrations/dify-dry-run-evidence-template.md \
  var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md
```

완료된 evidence를 wrapper에 연결한다.

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
pilot-rehearsal-manifest.md includes the Dify workflow version identifier
pilot-rehearsal-manifest.md includes var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md
pilot-rehearsal-manifest.md does not inline screenshot or workflow export content
secret_scan.passed is true
```

- [ ] **Step 6: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_dify_dry_run_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: commit**

```bash
git add docs/integrations/dify-dry-run-evidence-template.md docs/integrations/dify-dry-run-rehearsal.md docs/integrations/dify-handoff-checklist.md docs/ops/pilot-handoff-release-ticket-template.md docs/ops/pilot-launch-readiness-checklist.md tests/unit/test_dify_dry_run_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: close Dify dry-run release evidence flow"
```

## 작업 3: Closed-Network/BGE Evidence 또는 Host Access 예외 승인 확정

**Files:**

- Modify: `docs/ops/bge-m3-evidence-template.md`
- Modify: `docs/ops/pilot-rehearsal.md`
- Modify: `docs/ops/pilot-handoff-release-ticket-template.md`
- Modify: `docs/ops/pilot-launch-readiness-checklist.md`
- Modify: `tests/unit/test_bge_evidence_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_launch_readiness_docs_contract.py`

- [ ] **Step 1: docs contract test 확장**

`tests/unit/test_bge_evidence_template_docs_contract.py`에 아래 필수 문자열을 추가한다.

```text
pending-host-access exception approval
exception approval ID
exception owner
expires before pilot traffic
next measurement date
Conditional Go cannot send closed-network pilot traffic
```

Run:

```bash
uv run pytest tests/unit/test_bge_evidence_template_docs_contract.py -q
```

Expected: FAIL because exception approval fields are not documented yet.

- [ ] **Step 2: BGE evidence template에 예외 승인 필드 추가**

`docs/ops/bge-m3-evidence-template.md`의 `## Status` 또는 별도 `## Pending Host Access Exception` 섹션에 아래 필드를 추가한다.

```text
- Exception approval ID:
- Exception owner:
- Approved by:
- Approval timestamp:
- Expires before pilot traffic: yes
- Next measurement date:
- Decision impact: Conditional Go cannot send closed-network pilot traffic until measured-pass is attached.
```

정책 문구:

```text
pending-host-access requires an exception approval ID, an owner, and a next measurement date.
pending-host-access may support documentation closure, but it blocks closed-network pilot traffic.
Conditional Go with pending-host-access must state that Dify or closed-network traffic remains blocked until measured-pass evidence is attached.
```

- [ ] **Step 3: release ticket와 launch checklist에 BGE closure 연결**

`docs/ops/pilot-handoff-release-ticket-template.md`와 `docs/ops/pilot-launch-readiness-checklist.md`에 아래 gate를 추가한다.

```text
go requires BGE measured-pass before closed-network pilot traffic.
Conditional Go with pending-host-access requires exception approval ID, exception owner, expiration before pilot traffic, and next measurement date.
measured-fail blocks pilot launch until corrected evidence passes.
```

- [ ] **Step 4: closed-network 실측 경로 수동 검수**

폐쇄망 host가 준비된 경우 아래 command를 실행한다.

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

- [ ] **Step 5: host 미가용 예외 승인 수동 검수**

폐쇄망 host가 아직 없으면 completed evidence copy를 `var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md`로 작성한다.

Required values:

```text
Status: pending-host-access
Exception approval ID: a release, security, or operations approval identifier
Exception owner: named owner
Approved by: release owner and operations or security reviewer
Expires before pilot traffic: yes
Next measurement date: concrete date
Decision impact: closed-network pilot traffic blocked until measured-pass
```

Expected:

```text
release-ticket.md links var/evidence/${SERVICE_ID}/bge/bge-m3-evidence.md
pilot-go-no-go-decision.md states Conditional Go only if no closed-network pilot traffic is enabled
```

- [ ] **Step 6: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_bge_evidence_template_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: commit**

```bash
git add docs/ops/bge-m3-evidence-template.md docs/ops/pilot-rehearsal.md docs/ops/pilot-handoff-release-ticket-template.md docs/ops/pilot-launch-readiness-checklist.md tests/unit/test_bge_evidence_template_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: define BGE launch exception evidence"
```

## 작업 4: Branch Protection 적용과 Rollback 증적 캡처 절차 실행 가능화

**Files:**

- Modify: `docs/ops/branch-protection-evidence-template.md`
- Modify: `docs/ops/branch-protection.md`
- Modify: `docs/ops/pilot-handoff-release-ticket-template.md`
- Modify: `docs/ops/pilot-launch-readiness-checklist.md`
- Modify: `tests/unit/test_branch_protection_evidence_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_launch_readiness_docs_contract.py`

- [ ] **Step 1: docs contract test 확장**

`tests/unit/test_branch_protection_evidence_template_docs_contract.py`에 아래 필수 문자열을 추가한다.

```text
authorized operator capture
operator-not-permitted evidence request
apply evidence
rollback evidence
main-protection.json
branch protection capture verified
restore or confirm final branch protection state
```

Run:

```bash
uv run pytest tests/unit/test_branch_protection_evidence_template_docs_contract.py -q
```

Expected: FAIL until the template and runbook include the Sprint 7 closure terms.

- [ ] **Step 2: branch protection evidence template 보강**

`docs/ops/branch-protection-evidence-template.md`에 아래 필드를 추가한다.

```text
- Evidence type: apply / verify / rollback / operator-not-permitted
- Authorized operator:
- Operator permission result: authorized / operator-not-permitted
- Rule snapshot path: var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
- Verification output: branch protection capture verified
- Final state reviewer:
- Release ticket path: var/evidence/${SERVICE_ID}/release-ticket.md
- Go/no-go decision path: var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
```

`operator-not-permitted` 기준:

```text
operator-not-permitted may record an evidence request, but it does not satisfy pilot go/no-go.
An authorized operator must attach main-protection.json or explicitly approve a blocked Conditional Go with owner and deadline.
```

- [ ] **Step 3: runbook에 apply/rollback capture 순서 정리**

`docs/ops/branch-protection.md`에 아래 순서를 추가한다.

```text
1. Confirm the target branch is main.
2. Apply or confirm required status check CI / verify with strict: true.
3. Capture main-protection.json using gh api from an authorized operator shell.
4. Run the structured JSON verification snippet.
5. Record PR merge block evidence.
6. Record pilot-e2e-evidence artifact review.
7. For rollback or bypass, record approval ID, exact commit SHA, workflow_dispatch rerun URL, artifact review result, and final restored state.
8. Link the completed evidence copy from release-ticket.md and pilot-go-no-go-decision.md.
```

- [ ] **Step 4: 수동 캡처 검수**

권한 있는 operator shell에서 실행한다.

```bash
mkdir -p var/evidence/${SERVICE_ID}/branch-protection
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  > var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
```

검증:

```bash
uv run python - var/evidence/${SERVICE_ID}/branch-protection/main-protection.json <<'PY'
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

- [ ] **Step 5: release ticket gate 보강**

`docs/ops/pilot-handoff-release-ticket-template.md`에 아래 gate를 추가한다.

```text
go requires authorized branch protection evidence for main.
operator-not-permitted does not satisfy pilot go/no-go.
rollback or bypass evidence must include approval ID, exact commit SHA, workflow_dispatch rerun URL, artifact review result, and final branch protection state.
```

- [ ] **Step 6: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_branch_protection_evidence_template_docs_contract.py tests/unit/test_branch_protection_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: commit**

```bash
git add docs/ops/branch-protection-evidence-template.md docs/ops/branch-protection.md docs/ops/pilot-handoff-release-ticket-template.md docs/ops/pilot-launch-readiness-checklist.md tests/unit/test_branch_protection_evidence_template_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: close branch protection launch evidence"
```

## 작업 5: CSV Baseline Freeze 승인 기록 확정

**Files:**

- Create: `docs/pilot/csv-baseline-freeze-approval-template.md`
- Create: `tests/unit/test_csv_baseline_freeze_approval_docs_contract.py`
- Modify: `docs/pilot/csv-baseline-refresh-policy.md`
- Modify: `docs/pilot/README.md`
- Modify: `docs/ops/pilot-handoff-release-ticket-template.md`
- Modify: `docs/ops/pilot-launch-readiness-checklist.md`
- Modify: `tests/unit/test_csv_baseline_refresh_policy_docs_contract.py`
- Modify: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_launch_readiness_docs_contract.py`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_csv_baseline_freeze_approval_docs_contract.py`를 추가한다.

```python
from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/pilot/csv-baseline-freeze-approval-template.md"
TEMPLATE_PATH = "docs/pilot/csv-baseline-freeze-approval-template.md"


def test_csv_baseline_freeze_approval_template_contains_required_contract() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for expected in (
        TEMPLATE_PATH,
        "CSV Baseline Freeze Approval Template",
        "it-helpdesk-pilot-baseline.json",
        "standard 50-row",
        "balanced",
        "allowed_new_failures: 0",
        "allowed_new_reviews: 0",
        "CSV baseline comparison PASS",
        "refresh not approved",
        "approval ID",
        "release owner",
        "QA or security reviewer",
        "no raw query text",
        "no secret-bearing fields",
        "release-ticket.md",
    ):
        assert expected in text


def test_csv_baseline_freeze_approval_template_is_secret_scan_safe(
    tmp_path: Path,
) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[TEMPLATE])

    assert result == SecretScanResult(passed=True, findings=[])


def test_csv_baseline_freeze_template_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "docs/pilot/csv-baseline-refresh-policy.md",
        ROOT / "docs/pilot/README.md",
        ROOT / "docs/ops/pilot-handoff-release-ticket-template.md",
        ROOT / "docs/ops/pilot-launch-readiness-checklist.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert TEMPLATE_PATH in text
```

Run:

```bash
uv run pytest tests/unit/test_csv_baseline_freeze_approval_docs_contract.py -q
```

Expected: FAIL because the template does not exist yet.

- [ ] **Step 2: freeze approval template 작성**

`docs/pilot/csv-baseline-freeze-approval-template.md`에 아래 섹션을 작성한다.

```text
# CSV Baseline Freeze Approval Template
## Target Baseline
## Current Comparison Evidence
## Freeze Decision
## Reviewers
## Release Ticket Link
## Secret And Raw Query Review
```

필수 정책:

```text
The checked-in baseline remains docs/pilot/it-helpdesk-pilot-baseline.json.
The baseline freezes the standard 50-row CSV for the balanced preset.
allowed_new_failures: 0 remains in force.
allowed_new_reviews: 0 remains in force.
Use refresh not approved when no policy-approved behavior change is accepted.
Freeze approval requires an approval ID, release owner approval, and QA or security reviewer approval.
Go requires CSV baseline comparison PASS.
The record must not contain raw query text or secret-bearing fields.
```

- [ ] **Step 3: refresh policy와 pilot docs 연결**

`docs/pilot/csv-baseline-refresh-policy.md`에 freeze 승인 절차를 추가한다.

```text
When the baseline is intentionally kept frozen for pilot launch, complete docs/pilot/csv-baseline-freeze-approval-template.md and link the completed copy from release-ticket.md.
Refresh remains blocked unless the policy-approved approval ID and reviewed diff evidence are attached.
```

`docs/pilot/README.md`는 baseline freeze template이 launch approval evidence임을 링크한다.

- [ ] **Step 4: release ticket와 launch checklist에 freeze gate 추가**

`docs/ops/pilot-handoff-release-ticket-template.md`와 `docs/ops/pilot-launch-readiness-checklist.md`에 아래 필드를 추가한다.

```text
- CSV baseline freeze approval:
- Refresh status: refresh not approved / policy-approved refresh attached
- Freeze approval ID:
- Release owner:
- QA or security reviewer:
```

Gate:

```text
go requires CSV baseline comparison PASS.
go requires either CSV baseline freeze approval or a policy-approved refresh approval.
```

- [ ] **Step 5: baseline secret 검수**

```bash
rg -n 'query|authorization|api_key|Bearer |encrypted_dek|ciphertext|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON' docs/pilot/it-helpdesk-pilot-baseline.json
```

Expected: no matches.

- [ ] **Step 6: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_csv_baseline_freeze_approval_docs_contract.py tests/unit/test_csv_baseline_refresh_policy_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: commit**

```bash
git add docs/pilot/csv-baseline-freeze-approval-template.md docs/pilot/csv-baseline-refresh-policy.md docs/pilot/README.md docs/ops/pilot-handoff-release-ticket-template.md docs/ops/pilot-launch-readiness-checklist.md tests/unit/test_csv_baseline_freeze_approval_docs_contract.py tests/unit/test_csv_baseline_refresh_policy_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: add CSV baseline freeze approval record"
```

## 작업 6: Pilot Handoff/Release Ticket 실제 작성과 검수 흐름 확정

**Files:**

- Modify: `docs/ops/pilot-handoff-release-ticket-template.md`
- Modify: `docs/ops/pilot-launch-readiness-checklist.md`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Modify: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_launch_readiness_docs_contract.py`

- [ ] **Step 1: docs contract test 확장**

`tests/unit/test_pilot_handoff_release_template_docs_contract.py`에 아래 필수 문자열을 추가한다.

```text
var/evidence/${SERVICE_ID}/release-ticket.md
release ticket reviewer
evidence links only
no screenshot contents
no workflow export contents
go/no-go decision record
Conditional Go conditions
blocked gates
owner
approval ID
```

Run:

```bash
uv run pytest tests/unit/test_pilot_handoff_release_template_docs_contract.py -q
```

Expected: FAIL until the release ticket template includes the Sprint 7 review flow.

- [ ] **Step 2: release ticket template 보강**

`docs/ops/pilot-handoff-release-ticket-template.md`에 `## Evidence Closure Review` 섹션을 추가한다.

필수 필드:

```text
- Release ticket path: var/evidence/${SERVICE_ID}/release-ticket.md
- Release ticket reviewer:
- Evidence links only: yes / no
- No screenshot contents: yes / no
- No workflow export contents: yes / no
- No secrets or raw query text: yes / no
- Go/no-go decision record: var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
- Conditional Go conditions:
- Blocked gates:
- Owner:
- Approval ID:
```

필수 reviewer command:

```bash
rg -n 'PASS|CI / verify|pilot-rehearsal-manifest.md|Dify workflow version identifier|BGE evidence status|branch protection evidence|CSV baseline|go/no-go' var/evidence/${SERVICE_ID}/release-ticket.md
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/release-ticket.md
```

Expected:

```text
first rg prints required evidence references
second rg prints no matches
```

- [ ] **Step 3: runbook에 dry-fill 순서 보강**

`docs/ops/intent-routing-pilot-runbook.md`와 `docs/ops/pilot-launch-readiness-checklist.md`에 아래 순서를 추가한다.

```text
1. Copy docs/ops/pilot-handoff-release-ticket-template.md to var/evidence/${SERVICE_ID}/release-ticket.md.
2. Fill the release ticket with evidence paths, hashes, statuses, reviewer names, approval IDs, and go gate summary only.
3. Do not paste screenshot contents, workflow export contents, raw query text, API keys, bearer tokens, KEK material, encrypted DEKs, or ciphertext.
4. Run the reviewer commands.
5. Link the release ticket from pilot-go-no-go-decision.md.
```

- [ ] **Step 4: release ticket dry-fill 수동 검수**

실제 evidence가 준비된 `SERVICE_ID`로 실행한다.

```bash
cp docs/ops/pilot-handoff-release-ticket-template.md \
  var/evidence/${SERVICE_ID}/release-ticket.md
```

검수:

```bash
rg -n 'PASS|CI / verify|pilot-rehearsal-manifest.md|Dify workflow version identifier|BGE evidence status|branch protection evidence|CSV baseline|go/no-go' var/evidence/${SERVICE_ID}/release-ticket.md
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/release-ticket.md
```

Expected:

```text
first rg prints required evidence references
second rg prints no matches
```

- [ ] **Step 5: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/ops/pilot-handoff-release-ticket-template.md docs/ops/pilot-launch-readiness-checklist.md docs/ops/intent-routing-pilot-runbook.md tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: define release ticket evidence review flow"
```

## 작업 7: Pilot Go/No-Go 최종 판정 문서화

**Files:**

- Create: `docs/ops/pilot-go-no-go-decision-template.md`
- Create: `tests/unit/test_pilot_go_no_go_decision_docs_contract.py`
- Modify: `docs/ops/pilot-handoff-release-ticket-template.md`
- Modify: `docs/ops/pilot-launch-readiness-checklist.md`
- Modify: `docs/ops/pilot-rehearsal.md`
- Modify: `tests/unit/test_pilot_handoff_release_template_docs_contract.py`
- Modify: `tests/unit/test_pilot_launch_readiness_docs_contract.py`

- [ ] **Step 1: docs contract test 작성**

`tests/unit/test_pilot_go_no_go_decision_docs_contract.py`를 추가한다.

```python
from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/ops/pilot-go-no-go-decision-template.md"
TEMPLATE_PATH = "docs/ops/pilot-go-no-go-decision-template.md"


def test_pilot_go_no_go_decision_template_contains_required_contract() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for expected in (
        TEMPLATE_PATH,
        "Pilot Go/No-Go Decision Template",
        "Go",
        "No-Go",
        "Conditional Go",
        "release-ticket.md",
        "Dify UI dry-run evidence",
        "BGE evidence status",
        "branch protection evidence",
        "CSV baseline freeze approval",
        "local rehearsal final_status PASS",
        "secret_scan.passed true",
        "blocked gate",
        "condition owner",
        "approval ID",
        "expires before pilot traffic",
        "Admin UI excluded from Sprint 7",
        "no secrets",
        "no raw query text",
    ):
        assert expected in text


def test_pilot_go_no_go_decision_template_contains_required_sections() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for heading in (
        "# Pilot Go/No-Go Decision Template",
        "## Decision",
        "## Evidence Summary",
        "## Gate Results",
        "## Conditional Go Conditions",
        "## Blocked Gates",
        "## Approval Record",
        "## Launch Boundary",
        "## Secret And Raw Query Review",
    ):
        assert heading in text


def test_pilot_go_no_go_decision_template_is_secret_scan_safe(
    tmp_path: Path,
) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[TEMPLATE])

    assert result == SecretScanResult(passed=True, findings=[])


def test_pilot_go_no_go_decision_template_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "docs/ops/pilot-handoff-release-ticket-template.md",
        ROOT / "docs/ops/pilot-launch-readiness-checklist.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert TEMPLATE_PATH in text
```

Run:

```bash
uv run pytest tests/unit/test_pilot_go_no_go_decision_docs_contract.py -q
```

Expected: FAIL because the template does not exist yet.

- [ ] **Step 2: go/no-go decision template 작성**

`docs/ops/pilot-go-no-go-decision-template.md`에 아래 섹션을 작성한다.

```text
# Pilot Go/No-Go Decision Template
## Decision
## Evidence Summary
## Gate Results
## Conditional Go Conditions
## Blocked Gates
## Approval Record
## Launch Boundary
## Secret And Raw Query Review
```

Decision allowed values:

```text
Go
No-Go
Conditional Go
```

Gate Results 필수 항목:

```text
- CI / verify:
- local rehearsal final_status PASS:
- local rehearsal secret_scan.passed true:
- Dify UI dry-run evidence:
- BGE evidence status:
- branch protection evidence:
- CSV baseline freeze approval:
- release ticket review:
- Admin UI excluded from Sprint 7:
```

Conditional Go 조건:

```text
Each Conditional Go condition requires a blocked gate, condition owner, approval ID, expiry, next review date, and launch boundary impact.
pending-host-access expires before pilot traffic and blocks closed-network pilot traffic.
```

- [ ] **Step 3: release ticket와 launch checklist에 decision record 연결**

`docs/ops/pilot-handoff-release-ticket-template.md`, `docs/ops/pilot-launch-readiness-checklist.md`, `docs/ops/pilot-rehearsal.md`에 아래 링크 기준을 추가한다.

```text
Use docs/ops/pilot-go-no-go-decision-template.md for the final decision record.
Save the completed copy as var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md.
The decision record links release-ticket.md and must contain no secrets or raw query text.
```

- [ ] **Step 4: go/no-go decision 수동 dry-fill 검수**

```bash
cp docs/ops/pilot-go-no-go-decision-template.md \
  var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
```

검수:

```bash
rg -n 'Go|No-Go|Conditional Go|release-ticket.md|Dify UI dry-run evidence|BGE evidence status|branch protection evidence|CSV baseline freeze approval|secret_scan.passed true' var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
rg -n 'Bearer |Authorization: Bearer|RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md
```

Expected:

```text
first rg prints required decision references
second rg prints no matches
```

- [ ] **Step 5: focused test 통과 확인**

```bash
uv run pytest tests/unit/test_pilot_go_no_go_decision_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: commit**

```bash
git add docs/ops/pilot-go-no-go-decision-template.md docs/ops/pilot-handoff-release-ticket-template.md docs/ops/pilot-launch-readiness-checklist.md docs/ops/pilot-rehearsal.md tests/unit/test_pilot_go_no_go_decision_docs_contract.py tests/unit/test_pilot_handoff_release_template_docs_contract.py tests/unit/test_pilot_launch_readiness_docs_contract.py
git commit -m "docs: add pilot go-no-go decision record"
```

## 작업 8: Local Rehearsal Evidence 재생성/검수와 통합 검증

**Files:**

- Modify only if needed: docs/tests touched by Tasks 1-7.

- [ ] **Step 1: focused docs tests 실행**

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

DB가 없는 환경에서는 먼저 실행한다.

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run pytest -q
```

- [ ] **Step 4: local rehearsal evidence 재생성**

필요 시 새 `SERVICE_ID`로 실행한다.

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
```

API terminal:

```bash
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

Rehearsal terminal:

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

Expected:

```text
pilot-rehearsal-manifest.json final_status PASS
secret_scan.passed true
csv-baseline status pass
dify-smoke-matrix status pass
ops-evidence-export status pass
```

- [ ] **Step 5: evidence secret scan reviewer commands 실행**

```bash
uv run python -m json.tool var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
sha256sum var/evidence/${SERVICE_ID}/rehearsal/pilot-rehearsal-manifest.json
find var/evidence/${SERVICE_ID}/rehearsal -name '*.secret.json' -print
rg -n 'Authorization: Bearer|Bearer |RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|api_key=|intent_routing_api_key|query_raw|text_raw|encrypted_dek|ciphertext|irt_live_|irt_secret' var/evidence/${SERVICE_ID}/rehearsal
```

Expected:

```text
json.tool prints formatted JSON
sha256sum prints one digest for pilot-rehearsal-manifest.json
find prints no .secret.json files
rg prints no matches
```

`rg` returns exit code 1 when it finds no matches. For this reviewer scan, exit code 1 with no output is expected.

- [ ] **Step 6: 금지 경로와 Admin UI diff 확인**

```bash
git diff --name-only | rg '^docs/AdminUI_Handbook/'
git status --short | rg 'var/evidence|var/pilot|\.secret\.json'
```

Expected: no matches.

- [ ] **Step 7: final commit**

아직 커밋되지 않은 Sprint 7 docs/test 변경이 있으면:

```bash
git add README.md docs/ops docs/integrations docs/pilot tests/unit
git commit -m "docs: finalize Sprint 7 pilot launch readiness"
```

## 테스트 전략

- **Focused docs contract tests:** Sprint 7 신규/변경 문서가 필수 gate, evidence path, approval field, secret-scan 안전성, cross-link를 포함하는지 검증한다.
- **Existing docs contract tests:** Sprint 6에서 고정한 Dify/BGE/branch/CSV/release ticket 문서 계약이 깨지지 않았는지 검증한다.
- **Static checks:** `uv run ruff check .`, `uv run mypy src tests`, `docker compose --profile runtime config`.
- **Regression tests:** DB가 준비된 환경에서 `uv run pytest -q`.
- **Manual evidence verification:** local rehearsal manifest, Dify UI evidence path, BGE measured/exception evidence, branch protection snapshot, CSV freeze approval, release ticket, go/no-go decision record를 reviewer command로 검수한다.
- **Secret safety:** 모든 committed template과 generated evidence review command가 bearer token, KEK, API key, raw query, encrypted DEK, ciphertext marker를 차단한다.

## Sprint 7 Acceptance Criteria

- `docs/ops/pilot-launch-readiness-checklist.md`가 Dify, BGE, branch protection, CSV baseline, release ticket, go/no-go decision closure 순서를 포함한다.
- Dify UI dry-run evidence template과 rehearsal 문서가 completed evidence path, reviewer approval, release ticket link, go/no-go decision link를 포함한다.
- BGE evidence template이 `measured-pass` 실측 경로와 `pending-host-access` 예외 승인 필드, owner, expiry, next measurement date, pilot traffic blocking 기준을 포함한다.
- Branch protection evidence template과 runbook이 authorized operator capture, `main-protection.json`, structured verification, rollback/bypass record, final state restore/confirm 기준을 포함한다.
- CSV baseline freeze approval template이 current baseline 유지, `allowed_new_failures: 0`, `allowed_new_reviews: 0`, approval ID, release owner, QA/security reviewer, no raw query 기준을 포함한다.
- Release ticket template이 evidence links only, reviewer, blocked gates, Conditional Go conditions, go/no-go decision record link를 포함한다.
- Go/no-go decision template이 `Go`, `No-Go`, `Conditional Go`, gate summary, blocked gate owner, approval ID, expiry, launch boundary impact를 포함한다.
- Focused docs tests, static verification, DB-backed regression이 통과한다.
- 필요 시 새 local rehearsal evidence가 생성되고 `final_status PASS`, `secret_scan.passed true`가 확인된다.
- `docs/AdminUI_Handbook/`, `var/evidence/...`, `var/pilot/*.secret.json`, screenshot/export/snapshot 파일은 커밋되지 않는다.

## 수동 검수 절차

1. `docs/ops/pilot-launch-readiness-checklist.md`를 따라 새 `SERVICE_ID` 또는 승인된 기존 `SERVICE_ID`를 선택한다.
2. local rehearsal evidence가 오래되었거나 Dify evidence path가 바뀌었으면 새 `SERVICE_ID`로 local rehearsal을 재생성한다.
3. `pilot-rehearsal-manifest.json`에서 `final_status=PASS`, `secret_scan.passed=true`를 확인하고 manifest SHA-256을 기록한다.
4. Dify UI dry-run completed evidence를 `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`에 저장하고 workflow version identifier를 release ticket에 연결한다.
5. Closed-network host가 준비되었으면 BGE package preflight, benchmark, closed-network rehearsal을 실측한다.
6. Closed-network host가 없으면 `pending-host-access` evidence copy에 exception approval ID, owner, expiry, next measurement date를 기록하고 closed-network pilot traffic blocked를 decision record에 남긴다.
7. 권한 있는 operator가 branch protection snapshot을 `var/evidence/${SERVICE_ID}/branch-protection/main-protection.json`으로 캡처하고 structured verification이 `branch protection capture verified`를 출력하는지 확인한다.
8. CSV baseline freeze approval copy를 작성하고 CSV baseline comparison PASS 또는 policy-approved refresh approval을 release ticket에 연결한다.
9. `docs/ops/pilot-handoff-release-ticket-template.md`를 `var/evidence/${SERVICE_ID}/release-ticket.md`로 복사해 evidence path, hash, status, reviewer, approval ID만 기록한다.
10. `docs/ops/pilot-go-no-go-decision-template.md`를 `var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md`로 복사해 `Go`, `No-Go`, `Conditional Go` 중 하나로 판정한다.
11. release ticket과 go/no-go decision record에 secret/raw query reviewer command를 실행하고 출력이 없는지 확인한다.
12. `git diff --name-only`와 `git status --short`로 Admin UI, `var/evidence`, `var/pilot`, `.secret.json`이 커밋 대상에 없는지 확인한다.

## 사용자가 선택해야 하는 정책/범위 결정

- **BGE launch boundary:** Sprint 7에서 actual pilot go를 요구하려면 closed-network/BGE `measured-pass`가 필요하다. Host access가 없으면 `pending-host-access` 예외 승인을 남길 수 있지만, 추천 판정은 closed-network pilot traffic을 막는 `Conditional Go`다.
- **Dify evidence 형태:** masked screenshot만 받을지, sanitized workflow export만 받을지, 둘 다 허용할지 결정해야 한다. 추천은 둘 다 허용하되 release ticket과 manifest에는 path와 workflow version identifier만 기록하는 방식이다.
- **Branch protection operator:** `main` rule snapshot을 캡처할 authorized operator를 지정해야 한다. `operator-not-permitted`만으로는 pilot go/no-go를 만족하지 않는 정책을 추천한다.
- **Rollback drill 범위:** 실제 branch protection rollback/bypass를 수행할지, 아니면 승인 ID와 workflow_dispatch rerun 절차를 실행 가능한 evidence template으로만 닫을지 결정해야 한다. 추천은 실제 bypass 없이 apply/verify evidence와 rollback procedure evidence를 준비하고, 실제 bypass는 incident/change ticket에서만 실행하는 방식이다.
- **CSV baseline 승인자:** baseline freeze approval ID 발급자와 reviewer를 정해야 한다. 추천은 release owner 1명과 QA 또는 security reviewer 1명이다.
- **Final decision authority:** `Go`, `No-Go`, `Conditional Go` 최종 서명자를 정해야 한다. 추천은 Pilot owner가 decision owner이고 Engineering, Operations, Security, Dify owner가 approval record에 서명하는 구조다.

## 실행 방식 추천

Subagent-Driven 실행을 추천한다. 작업 1, 5, 7은 새 문서와 새 docs contract test 중심이고, 작업 2, 3, 4, 6은 기존 Sprint 6 템플릿을 보강하는 독립 흐름이라 task별 fresh subagent가 검수하기 좋다. 다만 실제 local rehearsal 재생성, branch protection capture, release ticket dry-fill, go/no-go decision dry-fill은 같은 `SERVICE_ID`와 같은 evidence tree를 공유하므로 마지막 통합 검증은 Inline Execution으로 한 세션에서 이어서 수행하는 편이 안전하다.
