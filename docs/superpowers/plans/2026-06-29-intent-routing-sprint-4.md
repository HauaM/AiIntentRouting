# Sprint 4: 지속 검증과 파일럿 인계 자동화 구현 계획

> **에이전트 작업자 필수 지침:** 이 계획을 실행할 때는 필수 하위 스킬로 `superpowers:subagent-driven-development`(권장) 또는 `superpowers:executing-plans`를 사용한다. 각 단계는 체크박스(`- [ ]`)로 진행 상태를 추적한다.

**목표:** Sprint 0-3에서 만든 Intent Routing Service의 로컬 검증, 파일럿 smoke, CSV threshold gate, Dify 인계, BGE-M3 폐쇄망 검증을 반복 가능한 CI/운영 증적 workflow로 승격한다.

**아키텍처:** 라우팅 엔진, API 계약, 보안 lifecycle 동작은 변경하지 않는다. 기존 FastAPI 서비스와 operator script를 재사용하고, GitHub Actions CI, process-level pilot smoke wrapper, CSV gate policy helper, Dify 인계 checklist, BGE-M3 package 사전 검증만 얇게 추가한다. GitHub CI는 fake embedding과 pgvector service container로 deterministic하게 돌리고, 실제 BGE-M3 모델 실행은 폐쇄망 수동 검수 절차와 package/benchmark evidence로 분리한다.

**기술 스택:** GitHub Actions, Python 3.12, uv, FastAPI, SQLAlchemy/Alembic, PostgreSQL 16 + pgvector, pytest, ruff, mypy, Docker Compose, 기존 pilot script, Markdown/JSON evidence report.

---

## 검토한 컨텍스트

필수 문서를 먼저 확인했다.

- `docs/superpowers/plans/2026-06-25-intent-routing-sprint-0.md`
- `docs/superpowers/plans/2026-06-26-intent-routing-sprint-1.md`
- `docs/superpowers/plans/2026-06-28-intent-routing-sprint-2.md`
- `docs/superpowers/plans/2026-06-28-intent-routing-sprint-3.md`
- `docs/ops/closed-network-deployment.md`
- `docs/ops/security-operations.md`
- `docs/ops/security-lifecycle.md`
- `docs/ops/pilot-readiness-evidence.md`
- `docs/ops/bge-m3-closed-network.md`
- `docs/integrations/dify-branching-playbook.md`
- `docs/pilot/README.md`
- `README.md`

추가로 Sprint 4 범위 판단을 위해 다음 구현 파일도 확인했다.

- `compose.yaml`
- `pyproject.toml`
- `tests/conftest.py`
- `scripts/run_pilot_readiness.py`
- `scripts/run_csv_gate.py`
- `scripts/smoke_runtime_dify.py`
- `scripts/benchmark_bge_m3.py`
- `src/intent_routing/ops/reports.py`
- `src/intent_routing/testing/gate.py`
- `src/intent_routing/testing/csv_runner.py`
- `docs/integrations/dify-http-request-node.md`
- `docs/integrations/dify-http-request-node-template.json`

CI workflow 작성 시 uv의 GitHub Actions 사용 방식은 공식 Astral 문서의 `astral-sh/setup-uv` 권장 패턴을 따른다: <https://docs.astral.sh/uv/guides/integration/github/>

## 현재 구현 상태 관찰

- Sprint 3 PR은 `main`에 merge되었고 현재 HEAD는 `94417515b614fa8879f04d9b0a8b1887f8f505f1`이다.
- `.github/workflows`가 없어서 ruff, mypy, pytest, Compose config 검증이 아직 GitHub에서 자동 실행되지 않는다.
- 최근 로컬 검증은 `uv run ruff check .`, `uv run mypy src tests`, `docker compose --profile runtime config`, DB 연결 pytest 전체 339개가 통과했다.
- `run_pilot_readiness.py`는 health/readyz, seed, threshold 비교, runtime smoke, masked log 확인, readiness evidence 생성을 이미 묶고 있다.
- `run_csv_gate.py`는 strict/balanced/exploratory 비교 report를 만들지만, 특정 preset이 gate를 실패했을 때 CLI가 non-zero로 종료하는 운영 gate 옵션은 없다.
- `smoke_runtime_dify.py`는 단일 Dify-style runtime request에 강하지만, Dify branch 전체를 검수하는 smoke matrix와 negative auth/error evidence는 별도 절차로 남아 있다.
- Dify HTTP template/playbook은 decision/error branch를 문서화하고 unit test로 고정한다. 다만 실제 Dify UI handoff checklist와 증적 보관 절차는 분리된 문서가 없다.
- BGE-M3 benchmark script는 실제 local model path, 1024 dimension, CPU-only latency/memory report를 검증한다. 다만 모델 package directory checksum/manifest preflight는 별도 자동화가 없다.

## Sprint 4 권장 방향

Sprint 4 목표는 **지속 검증과 파일럿 인계 gate**로 잡는다. 사용자가 제안한 다섯 후보는 모두 타당하지만, repo 상태상 새 라우팅 기능보다 “검증 자동화와 handoff 증적”이 다음 병목이다. 따라서 우선순위는 1) GitHub CI, 2) 파일럿 end-to-end smoke 자동화, 3) CSV threshold gate 운영화, 4) Dify handoff checklist, 5) BGE-M3 폐쇄망 package preflight 순서로 구성한다.

## Sprint 4 범위

산출물:

- GitHub Actions CI: ruff, mypy, Alembic migration, pytest, Docker Compose runtime config 자동 실행.
- Process-level pilot e2e smoke: 실제 Uvicorn 프로세스에 HTTP로 seed/readiness/CSV/smoke/evidence를 실행하는 wrapper.
- CSV threshold quality gate: `balanced` preset을 required gate로 지정하고 실패 시 non-zero 종료 및 report에 명시.
- Dify smoke matrix와 인계 checklist: confident, clarify, fallback, off_topic, risk, unauthorized, auth/config error path 검수 절차.
- BGE-M3 package 사전 검증: 폐쇄망 model directory checksum/manifest evidence 생성 후 benchmark runbook과 연결.
- CI/파일럿/보안 문서 업데이트와 계약 테스트.

범위 제외:

- 라우팅 점수식, threshold preset 값, risk/off_topic 정책 변경 없음.
- HNSW, sparse retrieval, multi-vector retrieval, LLM judge 추가 없음.
- Dify plugin packaging 없음. Sprint 4는 HTTP Request node handoff만 강화한다.
- 관리 UI, production IAM, OIDC, mTLS, HMAC signing, Kubernetes/OpenShift 없음.
- GitHub-hosted CI에서 실제 BGE-M3 모델을 다운로드하거나 실행하지 않는다.
- KEK rewrap/retention/security lifecycle 동작 변경 없음.

## 계획 파일 구조

새로 만들 파일:

```text
.github/workflows/ci.yml
docs/ops/ci-verification.md
docs/ops/pilot-e2e-smoke.md
docs/integrations/dify-handoff-checklist.md
src/intent_routing/ops/quality_gate.py
src/intent_routing/ops/smoke_matrix.py
src/intent_routing/embedding/model_package.py
scripts/run_pilot_e2e_smoke.py
scripts/run_dify_smoke_matrix.py
scripts/verify_bge_m3_package.py
tests/unit/test_ci_workflow_contract.py
tests/unit/test_quality_gate.py
tests/unit/test_smoke_matrix.py
tests/unit/test_dify_handoff_docs_contract.py
tests/unit/test_bge_model_package.py
tests/integration/test_pilot_e2e_smoke_flow.py
tests/integration/test_dify_smoke_matrix_flow.py
```

수정할 파일:

```text
README.md
docs/ops/intent-routing-local-runbook.md
docs/ops/intent-routing-pilot-runbook.md
docs/ops/pilot-readiness-evidence.md
docs/ops/bge-m3-closed-network.md
docs/integrations/dify-http-request-node.md
docs/integrations/dify-branching-playbook.md
scripts/run_csv_gate.py
scripts/run_pilot_readiness.py
src/intent_routing/ops/reports.py
tests/unit/test_ops_reports.py
```

파일별 책임:

- `.github/workflows/ci.yml`: PR, `main` push, 수동 실행에 대한 GitHub-hosted 검증 gate.
- `docs/ops/ci-verification.md`: CI가 무엇을 보장하고 무엇을 보장하지 않는지 설명한다.
- `docs/ops/pilot-e2e-smoke.md`: 로컬/폐쇄망에서 process-level e2e smoke를 실행하는 절차와 evidence 해석을 설명한다.
- `src/intent_routing/ops/quality_gate.py`: threshold comparison에서 required preset gate 판정을 수행한다.
- `src/intent_routing/ops/smoke_matrix.py`: Dify branch smoke case 정의, result aggregation, redacted report rendering을 담당한다.
- `scripts/run_pilot_e2e_smoke.py`: 이미 실행 중인 API에 대해 fresh service seed부터 evidence export까지 수행하고 required gate를 강제한다.
- `scripts/run_dify_smoke_matrix.py`: Dify decision/error branch별 smoke를 실행하고 JSON/Markdown evidence를 쓴다.
- `src/intent_routing/embedding/model_package.py`: local model directory manifest와 deterministic SHA-256 계산을 담당한다.
- `scripts/verify_bge_m3_package.py`: BGE-M3 폐쇄망 model package preflight report를 생성한다.

## 작업 1: GitHub CI 기준선

**파일:**

- 생성: `.github/workflows/ci.yml`
- 생성: `docs/ops/ci-verification.md`
- 생성: `tests/unit/test_ci_workflow_contract.py`
- 수정: `README.md`
- 수정: `docs/ops/intent-routing-local-runbook.md`

- [ ] **단계 1: 실패하는 CI workflow 계약 테스트 작성**

`tests/unit/test_ci_workflow_contract.py`를 생성한다.

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_workflow_runs_required_verification_commands() -> None:
    workflow = ROOT / ".github/workflows/ci.yml"
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")

    for expected in (
        "name: CI",
        "pull_request:",
        "push:",
        "workflow_dispatch:",
        "pgvector/pgvector:pg16",
        "127.0.0.1:55432",
        "DATABASE_URL:",
        "TEST_DATABASE_URL:",
        "uv sync --locked --group dev",
        "uv run ruff check .",
        "uv run mypy src tests",
        "uv run alembic upgrade head",
        "uv run pytest -q",
        "docker compose --profile runtime config",
    ):
        assert expected in text


def test_ci_workflow_uses_fake_embedding_and_no_real_secrets() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "EMBEDDING_PROVIDER: fake" in text
    assert "INTENT_ROUTING_ENVIRONMENT: dev" in text
    assert "RAW_TEXT_KEK_ID: ci-kek-001" in text
    for forbidden in (
        "replace-with",
        "intent_routing_api_key",
        "Bearer ",
        "RAW_TEXT_LEGACY_KEKS_JSON: {",
    ):
        assert forbidden not in text
```

실행:

```bash
uv run pytest tests/unit/test_ci_workflow_contract.py -v
```

예상 결과: `.github/workflows/ci.yml`이 아직 없으므로 실패한다.

- [ ] **단계 2: CI workflow 추가**

아래 계약으로 `.github/workflows/ci.yml`을 생성한다.

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: intent_routing
          POSTGRES_USER: intent
          POSTGRES_PASSWORD: intent
        ports:
          - "55432:5432"
        options: >-
          --health-cmd "pg_isready -U intent -d intent_routing"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing
      TEST_DATABASE_URL: postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing
      ADMIN_BOOTSTRAP_TOKEN: ci-admin-token
      INTENT_ROUTING_ENVIRONMENT: dev
      RAW_TEXT_KEK_ID: ci-kek-001
      RAW_TEXT_KEK_BASE64: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
      RAW_TEXT_LEGACY_KEKS_JSON: "{}"
      EMBEDDING_PROVIDER: fake

    steps:
      - name: Check out repository
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --group dev

      - name: Lint
        run: uv run ruff check .

      - name: Type check
        run: uv run mypy src tests

      - name: Apply migrations
        run: uv run alembic upgrade head

      - name: Test
        run: uv run pytest -q

      - name: Validate runtime Compose config
        run: docker compose --profile runtime config
```

- [ ] **단계 3: CI 범위 문서화**

`docs/ops/ci-verification.md`를 생성하고 다음 섹션을 포함한다.

- CI가 검증하는 항목: ruff, mypy, Alembic migration, pgvector 기반 pytest, Compose runtime config.
- CI가 의도적으로 검증하지 않는 항목: 실제 BGE-M3 모델, 폐쇄망 secret manager, 실제 Dify UI.
- 로컬 재현 필수 명령:

```bash
docker compose up -d postgres
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest -q
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
```

- GitHub branch protection 권장: `main` merge 전에 `CI / verify` check를 필수로 요구한다.
- artifact 정책: Sprint 4 CI 기준선은 secret-bearing state file을 업로드하지 않는다.

- [ ] **단계 4: 기존 runbook에서 CI 문서 연결**

Update `README.md` and `docs/ops/intent-routing-local-runbook.md` to link `docs/ops/ci-verification.md`.

- [ ] **단계 5: 작업 검증**

실행:

```bash
uv run pytest tests/unit/test_ci_workflow_contract.py -v
docker compose --profile runtime config
```

예상 결과: 테스트가 통과하고 Compose config가 정상 출력된다.

- [ ] **단계 6: 커밋**

```bash
git add .github/workflows/ci.yml README.md docs/ops/ci-verification.md docs/ops/intent-routing-local-runbook.md tests/unit/test_ci_workflow_contract.py
git commit -m "ci: add automated verification workflow"
```

## 작업 2: CSV Threshold 품질 Gate

**파일:**

- 생성: `src/intent_routing/ops/quality_gate.py`
- 생성: `tests/unit/test_quality_gate.py`
- 수정: `scripts/run_csv_gate.py`
- 수정: `src/intent_routing/ops/reports.py`
- 수정: `tests/unit/test_ops_reports.py`

- [ ] **단계 1: 실패하는 quality gate 테스트 작성**

`tests/unit/test_quality_gate.py`를 생성한다.

```python
import pytest

from intent_routing.ops.quality_gate import evaluate_required_preset_gate


RUNS = {
    "strict": {"gate_passed": False, "pass_rate": 0.5, "risk_pass_rate": 1.0},
    "balanced": {"gate_passed": True, "pass_rate": 0.8, "risk_pass_rate": 1.0},
    "exploratory": {"gate_passed": True, "pass_rate": 0.7, "risk_pass_rate": 1.0},
}


def test_required_preset_gate_passes_when_balanced_passes() -> None:
    result = evaluate_required_preset_gate(RUNS, required_preset="balanced")

    assert result.required_preset == "balanced"
    assert result.passed is True
    assert result.block_reasons == []


def test_required_preset_gate_blocks_when_balanced_fails() -> None:
    runs = {preset: dict(payload) for preset, payload in RUNS.items()}
    runs["balanced"]["gate_passed"] = False
    runs["balanced"]["pass_rate"] = 0.6

    result = evaluate_required_preset_gate(runs, required_preset="balanced")

    assert result.passed is False
    assert "required preset balanced failed CSV gate" in result.block_reasons
    assert "balanced pass_rate=60.0%" in result.block_reasons


def test_required_preset_gate_rejects_missing_preset() -> None:
    with pytest.raises(ValueError, match="missing required preset"):
        evaluate_required_preset_gate({"strict": RUNS["strict"]}, required_preset="balanced")
```

실행:

```bash
uv run pytest tests/unit/test_quality_gate.py -v
```

예상 결과: `intent_routing.ops.quality_gate`가 아직 없으므로 실패한다.

- [ ] **단계 2: quality gate helper 구현**

`src/intent_routing/ops/quality_gate.py`를 아래 내용으로 생성한다.

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RequiredPresetGate:
    required_preset: str
    passed: bool
    pass_rate: float
    risk_pass_rate: float
    block_reasons: list[str] = field(default_factory=list)


def evaluate_required_preset_gate(
    runs: Mapping[str, Mapping[str, Any]],
    *,
    required_preset: str,
) -> RequiredPresetGate:
    run = runs.get(required_preset)
    if run is None:
        raise ValueError(f"missing required preset: {required_preset}")

    pass_rate = float(run["pass_rate"])
    risk_pass_rate = float(run["risk_pass_rate"])
    block_reasons: list[str] = []
    if not bool(run["gate_passed"]):
        block_reasons.append(f"required preset {required_preset} failed CSV gate")
    if pass_rate < 0.70:
        block_reasons.append(f"{required_preset} pass_rate={pass_rate * 100:.1f}%")
    if risk_pass_rate < 1.0:
        block_reasons.append(f"{required_preset} risk_pass_rate={risk_pass_rate * 100:.1f}%")

    return RequiredPresetGate(
        required_preset=required_preset,
        passed=not block_reasons,
        pass_rate=pass_rate,
        risk_pass_rate=risk_pass_rate,
        block_reasons=block_reasons,
    )
```

- [ ] **단계 3: CSV report rendering에 required gate 추가**

`src/intent_routing/ops/reports.py`를 수정한다.

- `render_threshold_report`에 optional `required_gate: Mapping[str, Any] | None = None` 인자를 추가한다.
- `## Findings` 앞에 `## Required Gate` 섹션을 렌더링한다.
- balanced가 통과할 때 예상 Markdown:

```markdown
## Required Gate

- Required preset: `balanced`
- Gate: `PASS`
- Pass rate: `80.0%`
- Risk pass rate: `100.0%`
```

- balanced가 실패할 때 예상 Markdown:

```markdown
## Required Gate

- Required preset: `balanced`
- Gate: `FAIL`
- Pass rate: `60.0%`
- Risk pass rate: `100.0%`
- Block: required preset balanced failed CSV gate
- Block: balanced pass_rate=60.0%
```

`tests/unit/test_ops_reports.py`에 required gate 통과/실패 assertion을 각각 하나씩 추가한다.

- [ ] **단계 4: `run_csv_gate.py`에 CLI 강제 gate 추가**

`scripts/run_csv_gate.py`를 수정한다.

- `run_threshold_comparison`에 `required_preset: str | None = None` 인자를 추가한다.
- CLI option을 추가한다.

```python
parser.add_argument(
    "--require-preset",
    choices=PRESET_ORDER,
    help="Exit non-zero if the required threshold preset fails the CSV gate.",
)
```

- 모든 preset run을 수집한 뒤 `required_preset`이 설정되어 있으면 아래를 실행한다.

```python
quality_gate = evaluate_required_preset_gate(
    runs,
    required_preset=required_preset,
)
```

- JSON output에 `quality_gate`를 아래 형태로 포함한다.

```json
"quality_gate": {
  "required_preset": "balanced",
  "passed": true,
  "pass_rate": 0.8,
  "risk_pass_rate": 1.0,
  "block_reasons": []
}
```

- `quality_gate`를 `render_threshold_report`에 전달한다.
- `main`에서 report path 출력 후 `quality_gate.passed is False`이면 `SystemExit(1)`을 발생시킨다.
- `--require-preset`이 없을 때의 기본 동작은 변경하지 않는다.

- [ ] **단계 5: CLI 성공/실패 동작 테스트**

`tests/unit/test_ops_reports.py` 또는 새 `tests/unit/test_run_csv_gate_quality_gate.py`에 테스트를 추가한다.

- balanced가 통과하면 `--require-preset balanced`는 exit 0이다.
- balanced가 실패하면 `--require-preset balanced`는 `SystemExit(1)`을 발생시킨다.
- required preset이 실패해도 JSON/Markdown 파일은 기록된다.
- stdout/stderr에는 `api_key`가 포함되지 않는다.

실행:

```bash
uv run pytest tests/unit/test_quality_gate.py tests/unit/test_ops_reports.py -v
```

예상 결과: 통과한다.

- [ ] **단계 6: 커밋**

```bash
git add src/intent_routing/ops/quality_gate.py src/intent_routing/ops/reports.py scripts/run_csv_gate.py tests/unit/test_quality_gate.py tests/unit/test_ops_reports.py
git commit -m "feat: enforce required CSV threshold gate"
```

## 작업 3: 파일럿 End-to-End Smoke 자동화

**파일:**

- 생성: `scripts/run_pilot_e2e_smoke.py`
- 생성: `docs/ops/pilot-e2e-smoke.md`
- 생성: `tests/integration/test_pilot_e2e_smoke_flow.py`
- 수정: `scripts/run_pilot_readiness.py`
- 수정: `README.md`
- 수정: `docs/ops/pilot-readiness-evidence.md`
- 수정: `docs/ops/intent-routing-pilot-runbook.md`

- [ ] **단계 1: e2e wrapper용 실패하는 integration test 작성**

`tests/integration/test_pilot_readiness_flow.py`의 TestClient override pattern을 재사용해 `tests/integration/test_pilot_e2e_smoke_flow.py`를 생성한다.

테스트는 다음을 검증해야 한다.

- wrapper가 unique service를 seed한다.
- `readiness-report.json`과 `readiness-report.md`가 존재한다.
- threshold comparison JSON/Markdown이 존재한다.
- `quality_gate.required_preset == "balanced"`이다.
- `quality_gate.passed is True`이다.
- Markdown/JSON evidence에 `.secret.json`, raw API key, `query_raw`, bearer token이 나타나지 않는다.

실행:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest tests/integration/test_pilot_e2e_smoke_flow.py -v
```

예상 결과: `scripts/run_pilot_e2e_smoke.py`가 아직 없으므로 실패한다.

- [ ] **단계 2: e2e wrapper 구현**

`scripts/run_pilot_e2e_smoke.py`를 생성하고 다음 public function을 제공한다.

```python
def run_pilot_e2e_smoke(
    *,
    base_url: str,
    admin_token: str,
    service_id: str,
    environment: str,
    state_path: Path,
    out_dir: Path,
    csv_tier: str = "standard",
    csv_path: Path | None = None,
    required_preset: str = "balanced",
    http_client: Any | None = None,
) -> dict[str, Any]:
    ...
```

구현 규칙:

- health/readyz, seed, threshold comparison, smoke, masked log 확인은 `run_pilot_readiness`를 호출해 수행한다.
- `run_pilot_readiness`가 `required_preset`을 `run_threshold_comparison`에 전달하도록 한다.
- `pilot-e2e-smoke-index.json`과 `pilot-e2e-smoke-index.md`를 기록한다.
- readiness report와 threshold report path를 포함한다.
- `quality_gate`를 포함한다.
- CLI에서는 `quality_gate.passed is False`이면 non-zero로 종료한다.
- raw API key, bearer token, encrypted DEK, ciphertext, raw query text를 출력하거나 기록하지 않는다.

CLI 계약:

```bash
uv run python scripts/run_pilot_e2e_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --out-dir var/evidence/${SERVICE_ID}/e2e
```

- [ ] **단계 3: required CSV gate를 readiness 흐름에 연결**

`scripts/run_pilot_readiness.py`를 수정한다.

- optional `required_preset: str | None = None` 인자를 추가한다.
- 이를 `run_threshold_comparison`에 전달한다.
- 값이 있을 때 readiness payload에 `quality_gate`를 포함한다.
- 기본값은 `None`으로 두어 기존 caller 동작을 유지한다.

- [ ] **단계 4: process-level smoke 문서화**

`docs/ops/pilot-e2e-smoke.md`를 생성하고 다음 내용을 포함한다.

- 사전 조건: API가 이미 실행 중이고 DB migration이 완료되어 있으며, CI/local은 fake embedding을 사용하고 BGE-M3는 모델 검증 후에만 사용한다.
- local run 명령.
- closed-network run 명령.
- 예상 생성 파일.
- 필수 acceptance: `/healthz` ok, `/readyz` ready, `balanced` gate PASS, risk pass rate 100%, Dify smoke decision 통과, masked log에 raw query 미노출.
- migration 실패, duplicate `service_id`, auth 실패, balanced gate 실패, Dify smoke mismatch에 대한 failure triage table.
- secret scan 명령:

```bash
grep -R -n -E 'Bearer[[:space:]]+|api_key|secret state|encrypted_dek|ciphertext|query_raw' var/evidence/${SERVICE_ID}/e2e
```

예상 결과: redacted metadata로 명시한 JSON field name을 제외하고 match가 없어야 한다.

- [ ] **단계 5: runbook 업데이트**

Update `README.md`, `docs/ops/pilot-readiness-evidence.md`, and `docs/ops/intent-routing-pilot-runbook.md` to recommend `run_pilot_e2e_smoke.py` as the Sprint 4 default before Dify handoff.

- [ ] **단계 6: 작업 검증**

실행:

```bash
uv run pytest tests/integration/test_pilot_e2e_smoke_flow.py -v
uv run pytest tests/integration/test_pilot_readiness_flow.py -v
```

예상 결과: 통과한다.

- [ ] **단계 7: 커밋**

```bash
git add scripts/run_pilot_e2e_smoke.py scripts/run_pilot_readiness.py README.md docs/ops/pilot-e2e-smoke.md docs/ops/pilot-readiness-evidence.md docs/ops/intent-routing-pilot-runbook.md tests/integration/test_pilot_e2e_smoke_flow.py
git commit -m "feat: add pilot e2e smoke gate"
```

## 작업 4: Dify Smoke Matrix와 인계 체크리스트

**파일:**

- 생성: `src/intent_routing/ops/smoke_matrix.py`
- 생성: `scripts/run_dify_smoke_matrix.py`
- 생성: `docs/integrations/dify-handoff-checklist.md`
- 생성: `tests/unit/test_smoke_matrix.py`
- 생성: `tests/unit/test_dify_handoff_docs_contract.py`
- 생성: `tests/integration/test_dify_smoke_matrix_flow.py`
- 수정: `scripts/run_pilot_readiness.py`
- 수정: `docs/integrations/dify-http-request-node.md`
- 수정: `docs/integrations/dify-branching-playbook.md`

- [ ] **단계 1: 실패하는 smoke matrix 테스트 작성**

`tests/unit/test_smoke_matrix.py`를 생성하고 default matrix에 다음 case가 포함되는지 검증한다.

```python
expected = {
    "confident",
    "clarify",
    "fallback",
    "off_topic",
    "risk",
    "wrong_api_key_401",
    "wrong_service_403",
    "invalid_body_422",
}
```

렌더링된 Markdown에 다음이 포함되는지도 검증한다.

- `# Dify Smoke Matrix`
- 각 case name.
- `api_key`, `Bearer`, raw query secret text가 없음.

- [ ] **단계 2: smoke matrix primitive 구현**

`src/intent_routing/ops/smoke_matrix.py`를 생성하고 다음을 제공한다.

```python
@dataclass(frozen=True, slots=True)
class DifySmokeCase:
    name: str
    query: str | None
    expected_status: int
    expected_decision: str | None
    expected_error_code: str | None = None
    expected_route_key: str | None = None
    mutation: str = "none"


def default_dify_smoke_cases() -> tuple[DifySmokeCase, ...]:
    ...


def render_dify_smoke_matrix_json(payload: Mapping[str, Any]) -> str:
    ...


def render_dify_smoke_matrix_markdown(payload: Mapping[str, Any]) -> str:
    ...
```

기본 case:

- `confident`: query `API timeout 500 에러가 납니다`, HTTP 200, decision `confident`, route key `it.api_timeout.manual_lookup`.
- `clarify`: query `계정 잠금과 VPN 중 어느 절차인지 헷갈립니다`, HTTP 200, decision `clarify`.
- `fallback`: query `회의실 예약 변경 방법을 알려주세요`, HTTP 200, decision `fallback`.
- `off_topic`: query `오늘 점심 메뉴와 날씨를 알려주세요`, HTTP 200, decision `off_topic`.
- `risk`: query `다른 고객 계좌번호와 개인정보를 보여주세요`, HTTP 200, decision `risk`.
- `wrong_api_key_401`: bearer secret을 변조하고 HTTP 401 및 error code `AUTHENTICATION_FAILED`를 기대한다.
- `wrong_service_403`: `X-Service-Id`를 변조하고 HTTP 403 및 error code `SERVICE_SCOPE_DENIED`를 기대한다.
- `invalid_body_422`: `query`를 생략하고 HTTP 422를 기대한다.

- [ ] **단계 3: Dify smoke matrix script 구현**

`scripts/run_dify_smoke_matrix.py`를 생성한다.

- `--state`에서 state file을 읽는다.
- 각 case를 `/v1/intent-route`로 보낸다.
- 테스트를 위해 `http_client` injection을 지원한다.
- `dify-smoke-matrix.json`과 `dify-smoke-matrix.md`를 쓴다.
- 어떤 case든 expected status/decision/error code를 만족하지 못하면 non-zero로 종료한다.
- raised error와 report에서 API key와 bearer value를 redaction한다.

CLI:

```bash
uv run python scripts/run_dify_smoke_matrix.py \
  --base-url http://127.0.0.1:8000 \
  --state ${STATE_PATH} \
  --out-dir var/evidence/${SERVICE_ID}/dify
```

- [ ] **단계 4: pilot readiness smoke set에 matrix 일부 추가**

`scripts/run_pilot_readiness.py`를 수정한다.

- 현재 `SMOKE_CASES`에 `clarify`를 추가한다.
- lightweight readiness smoke set은 HTTP 200 decision branch 중심으로 유지한다.
- negative auth case는 `run_dify_smoke_matrix.py`에서 분리 검증하는 편이 명확하므로 readiness에는 추가하지 않는다.

- [ ] **단계 5: integration test 작성**

기존 TestClient seed pattern을 사용해 `tests/integration/test_dify_smoke_matrix_flow.py`를 생성한다.

다음을 검증한다.

- 모든 default case가 실행된다.
- 정상 decision case가 기대한 `decision`을 반환한다.
- wrong API key는 401을 반환한다.
- wrong service는 403을 반환한다.
- invalid body는 422를 반환한다.
- report file에 API key가 포함되지 않는다.

- [ ] **단계 6: Dify 인계 체크리스트 작성**

`docs/integrations/dify-handoff-checklist.md`를 생성하고 다음을 포함한다.

- HTTP Request node variable mapping checklist.
- Timeout 8초 설정.
- 408/5xx/timeout에 대한 automatic retry loop 금지.
- `confident`, `clarify`, `fallback`, `off_topic`, `risk`, `unauthorized` branch checklist.
- 401/403/422/408/5xx/timeout error branch checklist.
- evidence 첨부 checklist:
  - `dify-smoke-matrix.json`
  - `dify-smoke-matrix.md`
  - `readiness-report.md`
  - threshold comparison Markdown
  - screenshot 또는 export된 Dify workflow version identifier
- manual UI check:
  - Dify secret variable이 `intent_routing_api_key`를 숨긴다.
  - `X-Request-Id`가 `workflow_run_id`에 매핑된다.
  - downstream node가 `trace_id`, `request_id`, `release_version`을 보존한다.
  - risk branch가 business route를 호출하지 않는다.

Dify 관련 문서에서 checklist를 링크한다.

- [ ] **단계 7: 작업 검증**

실행:

```bash
uv run pytest tests/unit/test_smoke_matrix.py tests/unit/test_dify_handoff_docs_contract.py -v
uv run pytest tests/integration/test_dify_smoke_matrix_flow.py tests/integration/test_dify_smoke_flow.py -v
```

예상 결과: 통과한다.

- [ ] **단계 8: 커밋**

```bash
git add src/intent_routing/ops/smoke_matrix.py scripts/run_dify_smoke_matrix.py scripts/run_pilot_readiness.py docs/integrations/dify-handoff-checklist.md docs/integrations/dify-http-request-node.md docs/integrations/dify-branching-playbook.md tests/unit/test_smoke_matrix.py tests/unit/test_dify_handoff_docs_contract.py tests/integration/test_dify_smoke_matrix_flow.py
git commit -m "feat: add Dify handoff smoke matrix"
```

## 작업 5: BGE-M3 폐쇄망 Package 사전 검증

**파일:**

- 생성: `src/intent_routing/embedding/model_package.py`
- 생성: `scripts/verify_bge_m3_package.py`
- 생성: `tests/unit/test_bge_model_package.py`
- 수정: `docs/ops/bge-m3-closed-network.md`
- 수정: `docs/ops/closed-network-deployment.md`

- [ ] **단계 1: 실패하는 model package 테스트 작성**

`tests/unit/test_bge_model_package.py`를 생성한다.

```python
from pathlib import Path

import pytest

from intent_routing.embedding.model_package import build_model_package_manifest


def test_model_package_manifest_is_deterministic(tmp_path: Path) -> None:
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    (model_dir / "config.json").write_text('{"hidden_size":1024}\n', encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("tokenizer\n", encoding="utf-8")

    first = build_model_package_manifest(model_dir)
    second = build_model_package_manifest(model_dir)

    assert first == second
    assert first.model_path == str(model_dir.resolve())
    assert first.file_count == 2
    assert first.total_bytes > 0
    assert len(first.sha256) == 64
    assert first.offline_required is True


def test_model_package_manifest_rejects_missing_or_empty_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="existing local BGE-M3 model directory"):
        build_model_package_manifest(tmp_path / "missing")

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="at least one file"):
        build_model_package_manifest(empty)
```

실행:

```bash
uv run pytest tests/unit/test_bge_model_package.py -v
```

예상 결과: `intent_routing.embedding.model_package`가 아직 없으므로 실패한다.

- [ ] **단계 2: deterministic model package manifest 구현**

`src/intent_routing/embedding/model_package.py`를 생성한다.

```python
@dataclass(frozen=True, slots=True)
class ModelPackageManifest:
    model_path: str
    file_count: int
    total_bytes: int
    sha256: str
    offline_required: bool = True


def build_model_package_manifest(model_path: Path) -> ModelPackageManifest:
    ...


def render_model_package_json(manifest: ModelPackageManifest) -> str:
    ...


def render_model_package_markdown(manifest: ModelPackageManifest) -> str:
    ...
```

Hashing 규칙:

- `model_path`를 resolve한다.
- missing path, non-directory path, empty directory를 거부한다.
- 모든 파일을 recursive하게 포함하고 POSIX relative path 기준으로 정렬한다.
- relative path bytes, null separator, file bytes, newline separator 순서로 SHA-256을 update한다.
- model directory 밖을 가리키는 symlink를 따라가지 않는다.
- `FlagEmbedding`, `torch`, `sentence_transformers`를 import하지 않는다.

- [ ] **단계 3: package verification CLI 추가**

`scripts/verify_bge_m3_package.py`를 생성한다.

```bash
uv run python scripts/verify_bge_m3_package.py \
  --model-path /models/bge-m3 \
  --out-dir var/benchmarks \
  --expected-sha256 <optional-approved-checksum>
```

동작:

- `bge-m3-package.json`을 쓴다.
- `bge-m3-package.md`를 쓴다.
- 두 path를 출력한다.
- `--expected-sha256`가 제공됐고 실제 checksum과 다르면 실제 report를 쓴 뒤 non-zero로 종료한다.
- output에는 model file content를 포함하지 않는다.

- [ ] **단계 4: BGE runbook 업데이트**

`docs/ops/bge-m3-closed-network.md`를 수정한다.

- benchmark 전에 preflight command를 추가한다.
- handoff package에 package checksum evidence를 필수로 요구한다.
- CI는 temp file로 manifest logic만 검증하고 실제 모델은 실행하지 않는다고 명시한다.

Dify traffic을 허용하기 전에 package preflight를 실행해야 한다는 내용을 `docs/ops/closed-network-deployment.md`에 추가한다.

- [ ] **단계 5: 작업 검증**

실행:

```bash
uv run pytest tests/unit/test_bge_model_package.py tests/unit/test_bge_benchmark_script.py -v
```

예상 결과: 통과한다.

- [ ] **단계 6: 커밋**

```bash
git add src/intent_routing/embedding/model_package.py scripts/verify_bge_m3_package.py docs/ops/bge-m3-closed-network.md docs/ops/closed-network-deployment.md tests/unit/test_bge_model_package.py
git commit -m "feat: add BGE-M3 package preflight evidence"
```

## 작업 6: CI에서 파일럿 E2E Smoke 실행

**파일:**

- 수정: `.github/workflows/ci.yml`
- 수정: `docs/ops/ci-verification.md`
- 수정: `tests/unit/test_ci_workflow_contract.py`

- [ ] **단계 1: CI 계약 테스트 확장**

`tests/unit/test_ci_workflow_contract.py`에 다음 assertion을 추가한다.

```python
for expected in (
    "Start API",
    "uv run uvicorn intent_routing.main:create_app --factory",
    "Run pilot e2e smoke",
    "scripts/run_pilot_e2e_smoke.py",
    "--required-preset balanced",
    "Upload pilot e2e evidence",
    "actions/upload-artifact@v4",
):
    assert expected in text
```

- [ ] **단계 2: API process와 e2e smoke step 추가**

`Apply migrations` 뒤, 전체 `Test` 전에 다음 단계를 추가한다.

```yaml
      - name: Start API
        run: |
          mkdir -p var/logs
          uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000 > var/logs/api.log 2>&1 &
          echo $! > var/logs/api.pid
          for i in $(seq 1 30); do
            if curl -fsS http://127.0.0.1:8000/readyz; then
              exit 0
            fi
            sleep 1
          done
          cat var/logs/api.log
          exit 1

      - name: Run pilot e2e smoke
        run: |
          SERVICE_ID="it-helpdesk-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
          STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
          uv run python scripts/run_pilot_e2e_smoke.py \
            --base-url http://127.0.0.1:8000 \
            --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
            --service-id "${SERVICE_ID}" \
            --environment "${INTENT_ROUTING_ENVIRONMENT}" \
            --state-path "${STATE_PATH}" \
            --csv-tier standard \
            --required-preset balanced \
            --out-dir "var/evidence/${SERVICE_ID}/e2e"

      - name: Upload pilot e2e evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pilot-e2e-evidence
          path: |
            var/evidence/**/*
            var/logs/api.log
          retention-days: 14
```

`var/pilot/*.secret.json`은 업로드하지 않는다.

- [ ] **단계 3: CI pilot evidence 문서화**

`docs/ops/ci-verification.md`를 수정한다.

- CI는 non-secret e2e evidence를 14일 동안 업로드한다.
- CI는 generated state secret file을 업로드하지 않는다.
- Sprint 4 merge 이후 branch protection에서 CI를 required로 걸어야 한다.
- pilot e2e만 실패하고 unit test는 통과하면 `pilot-e2e-smoke-index.md`, threshold comparison Markdown, `api.log`를 확인한다.

- [ ] **단계 4: 작업 검증**

실행:

```bash
uv run pytest tests/unit/test_ci_workflow_contract.py -v
```

예상 결과: 통과한다.

- [ ] **단계 5: 커밋**

```bash
git add .github/workflows/ci.yml docs/ops/ci-verification.md tests/unit/test_ci_workflow_contract.py
git commit -m "ci: run pilot e2e smoke"
```

## 작업 7: 최종 검증과 인계

**파일:**

- 최종 문서 링크나 명령 보정이 필요할 때만 작업 1-6에서 이미 건드린 파일을 수정한다.

- [ ] **단계 1: focused test 실행**

실행:

```bash
uv run pytest \
  tests/unit/test_ci_workflow_contract.py \
  tests/unit/test_quality_gate.py \
  tests/unit/test_ops_reports.py \
  tests/unit/test_smoke_matrix.py \
  tests/unit/test_dify_handoff_docs_contract.py \
  tests/unit/test_bge_model_package.py \
  -v
```

예상 결과: 통과한다.

- [ ] **단계 2: integration smoke test 실행**

PostgreSQL이 실행 중이고 migration이 적용된 상태에서 실행한다.

```bash
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest \
  tests/integration/test_pilot_e2e_smoke_flow.py \
  tests/integration/test_dify_smoke_matrix_flow.py \
  tests/integration/test_pilot_readiness_flow.py \
  tests/integration/test_dify_smoke_flow.py \
  -v
```

예상 결과: 통과한다.

- [ ] **단계 3: 전체 로컬 검증 실행**

실행:

```bash
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest -q
```

예상 결과: ruff와 mypy가 통과하고, Compose config가 출력되며, pytest가 통과한다.

- [ ] **단계 4: process-level manual smoke를 로컬에서 실행**

첫 번째 터미널:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON='{}'
export EMBEDDING_PROVIDER=fake
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

두 번째 터미널:

```bash
export SERVICE_ID=it-helpdesk-sprint4-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
uv run python scripts/run_pilot_e2e_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token local-admin-token \
  --service-id ${SERVICE_ID} \
  --environment dev \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --out-dir var/evidence/${SERVICE_ID}/e2e
uv run python scripts/run_dify_smoke_matrix.py \
  --base-url http://127.0.0.1:8000 \
  --state ${STATE_PATH} \
  --out-dir var/evidence/${SERVICE_ID}/dify
```

예상 결과:

- `pilot-e2e-smoke-index.md`가 존재한다.
- `dify-smoke-matrix.md`가 존재한다.
- balanced gate가 PASS다.
- shared evidence에 raw query, API key, bearer token, encrypted DEK, ciphertext가 나타나지 않는다.

- [ ] **단계 5: documentation contract scan 실행**

실행:

```bash
rg -n "[T]BD|[T]ODO|[f]ill in|[i]mplement later|[a]ppropriate error|[s]imilar to Task" docs/superpowers/plans/2026-06-29-intent-routing-sprint-4.md docs/ops docs/integrations
```

예상 결과: Sprint 4 문서가 새로 만든 match가 없어야 한다.

- [ ] **단계 6: 최종 문서 보정 커밋**

```bash
git status --short
git add README.md docs scripts src tests .github/workflows/ci.yml
git commit -m "docs: finalize Sprint 4 verification handoff"
```

## 인수 기준

- GitHub Actions CI가 존재하며 pull request, `main` push, 수동 실행에서 실행된다.
- CI는 `pgvector/pgvector:pg16`을 사용하고 `127.0.0.1:55432`에 연결해 실행된다.
- CI는 `uv run ruff check .`, `uv run mypy src tests`, `uv run alembic upgrade head`, `uv run pytest -q`, `docker compose --profile runtime config`를 실행한다.
- CI는 API process를 시작하고 `--required-preset balanced`로 `run_pilot_e2e_smoke.py`를 실행한다.
- CI는 non-secret pilot e2e evidence를 업로드하고 `.secret.json` state file은 업로드하지 않는다.
- `run_csv_gate.py --require-preset balanced`는 balanced gate가 실패하면 non-zero를 반환하고, 이 경우에도 JSON/Markdown evidence를 기록한다.
- Pilot e2e smoke는 index report, readiness report, threshold comparison report, redacted evidence를 기록한다.
- Dify smoke matrix는 confident, clarify, fallback, off_topic, risk, wrong API key 401, wrong service 403, invalid body 422를 포함한다.
- Dify 인계 checklist는 variable mapping, branch mapping, timeout/no-retry 동작, evidence 첨부, 수동 UI 확인을 포함한다.
- BGE-M3 package 사전 검증은 model runtime dependency를 import하지 않고 deterministic checksum JSON/Markdown을 기록한다.
- 새 문서는 README 또는 관련 ops/integration runbook에서 링크된다.
- 기존 339-test baseline에 Sprint 4 test를 더한 전체 로컬 검증이 통과한다.

## 수동 검수 절차

1. GitHub PR에서 `CI / verify`가 초록색인지 확인한다.
2. CI artifact `pilot-e2e-evidence`를 내려받아 `pilot-e2e-smoke-index.md`, threshold comparison Markdown, `readiness-report.md`, `api.log`를 확인한다.
3. artifact에 `.secret.json`, raw API key, `Bearer `, `encrypted_dek`, `ciphertext`, `query_raw`가 포함되지 않았는지 확인한다.
4. Dify UI에서 `docs/integrations/dify-http-request-node-template.json` 값을 HTTP Request node에 반영한다.
5. `docs/integrations/dify-handoff-checklist.md`에 따라 secret variable masking, `workflow_run_id` mapping, timeout 8초, no retry loop, decision/error branches를 확인한다.
6. 로컬 또는 폐쇄망 API에 대해 `run_dify_smoke_matrix.py`를 실행하고 `dify-smoke-matrix.md`를 handoff evidence로 보관한다.
7. 폐쇄망 BGE-M3 host에서 `verify_bge_m3_package.py`를 먼저 실행한 뒤 `benchmark_bge_m3.py`를 실행한다.
8. BGE package checksum, benchmark p50/p95, max RSS, model path, max tokens 256을 pilot evidence bundle에 첨부한다.
9. branch protection에서 Sprint 4 CI check가 required로 설정되어 있는지 확인한다.

## 제품 책임자 정책/범위 결정사항

구현 전 반드시 선택해야 하는 결정:

- **CI required check 적용 시점:** Sprint 4 PR merge 직후 `main` branch protection에 `CI / verify`를 required로 걸지, 한 번의 관찰 기간 후 걸지 결정한다. 추천은 Sprint 4 merge 직후 적용이다.
- **CI e2e smoke 실행 빈도:** 모든 PR에서 process-level e2e smoke를 돌릴지, `workflow_dispatch`/nightly로만 돌릴지 결정한다. 추천은 fake embedding이라 비용이 낮으므로 모든 PR에서 실행이다.
- **CI artifact retention:** 기본 계획은 14일이다. 내부 감사 요구가 있으면 30일로 늘린다.
- **BGE-M3 실제 모델 검증 위치:** GitHub-hosted CI에는 모델을 올리지 않는다. 실제 모델 package/benchmark는 폐쇄망 host에서 수동 증적으로 운영한다.
- **Balanced gate 실패 시 merge 차단:** 기본 계획은 `balanced` preset 실패를 CI 실패로 처리한다. strict/exploratory는 비교와 권고 자료로 유지한다.

## 권장 실행 방식

추천 실행 방식은 **Subagent-Driven**이다. 작업 1/2/3/4/5가 서로 파일 범위가 비교적 독립적이고, CI YAML, CSV gate, e2e script, Dify matrix, BGE package preflight를 각 subagent가 작은 단위로 구현한 뒤 main agent가 통합 검증하기 좋다. Inline Execution도 가능하지만 Sprint 4는 문서, workflow, script, integration test가 동시에 움직이므로 Subagent-Driven이 회귀를 더 빨리 잡는다.
