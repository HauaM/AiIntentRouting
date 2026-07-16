# macOS Local Development Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a zsh-native macOS command that starts the complete local stack with Colima and visually distinct backend/frontend logs.

**Architecture:** A new `scripts/run_local_dev_stack_macos.sh` owns macOS prerequisite checks, environment loading, Colima/Compose orchestration, application lifecycle, and colorized log following. It reuses the Linux script's runtime contract without calling that Bash 4+ script. Static contract tests and zsh syntax validation protect the platform-specific behavior; README and the macOS runbook expose one canonical command.

**Tech Stack:** zsh, Colima, Docker Compose, uv, Uvicorn, pnpm/Corepack, pytest

## Global Constraints

- The script must run with the macOS-provided `/bin/zsh`.
- Caller-exported environment variables take precedence over `.env`, which takes precedence over local defaults.
- Backend logs use cyan and frontend logs use magenta when stdout is a terminal.
- `NO_COLOR` or non-interactive stdout disables ANSI colors without removing `[backend]` and `[frontend]` prefixes.
- Cleanup must not stop PostgreSQL or delete Docker volumes.
- Existing unrelated worktree changes must remain untouched.

---

### Task 1: macOS Script Contract and Core Orchestration

**Files:**
- Create: `tests/unit/test_macos_local_dev_stack_script.py`
- Create: `scripts/run_local_dev_stack_macos.sh`

**Interfaces:**
- Consumes: `compose.yaml`, `.env`, environment overrides, `scripts/seed_pilot.py`, backend `/healthz` endpoint.
- Produces: executable `scripts/run_local_dev_stack_macos.sh`; `main()` orchestration entry point; raw logs at `var/logs/local-dev-stack/{backend,frontend}.log`.

- [ ] **Step 1: Write failing platform and lifecycle contract tests**

Create `tests/unit/test_macos_local_dev_stack_script.py` with tests that read the script and assert these exact contracts:

```python
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_local_dev_stack_macos.sh"


def script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_macos_script_is_executable_zsh() -> None:
    assert SCRIPT.stat().st_mode & stat.S_IXUSR
    assert script_text().startswith("#!/usr/bin/env zsh\n")
    result = subprocess.run(
        ["zsh", "-n", str(SCRIPT)], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_macos_script_runtime_contract() -> None:
    text = script_text()
    for fragment in (
        '[[ "$(uname -s)" == "Darwin" ]]',
        "load_local_env",
        "CALLER_ENVIRONMENT",
        "ensure_colima",
        "resolve_compose_command",
        "COMPOSE_CMD=(docker compose)",
        "COMPOSE_CMD=(docker-compose)",
        "ensure_local_database",
        "uv run alembic upgrade head",
        "prepare_startup_system_admin_provisioning",
        "uv run uvicorn intent_routing.main:create_app --factory",
        "scripts/seed_pilot.py",
        'ADMIN_API_PROXY="http://${HOST}:${BACKEND_PORT}"',
        "cleanup_stale_log_followers",
        'stop_port_listeners "${BACKEND_PORT}" "backend"',
        'stop_port_listeners "${FRONTEND_PORT}" "frontend"',
    ):
        assert fragment in text
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest tests/unit/test_macos_local_dev_stack_script.py -q
```

Expected: failure because `scripts/run_local_dev_stack_macos.sh` does not exist.

- [ ] **Step 3: Implement the zsh orchestration script**

Create an executable zsh script using the Linux script's functions as the behavioral reference. Implement these concrete differences:

```zsh
#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="${0:A:h:h}"
typeset -A CALLER_ENVIRONMENT
for key in DATABASE_URL APP_ENV INTENT_ROUTING_ENVIRONMENT ADMIN_AUTH_MODE \
  ADMIN_BOOTSTRAP_TOKEN ADMIN_SYSTEM_ADMIN_EMAIL ADMIN_SYSTEM_ADMIN_PASSWORD \
  ADMIN_SYSTEM_ADMIN_DISPLAY_NAME RAW_TEXT_KEK_ID RAW_TEXT_KEK_BASE64 \
  RAW_TEXT_LEGACY_KEKS_JSON EMBEDDING_PROVIDER BGE_M3_MODEL_PATH \
  BGE_M3_MODEL_SHA256 BGE_M3_BATCH_SIZE BGE_M3_MAX_TOKENS EMBED_EXAMPLES_FROM; do
  if (( ${+parameters[$key]} )); then
    CALLER_ENVIRONMENT[$key]="${(P)key}"
  fi
done

load_local_env() {
  [[ -f "${ROOT_DIR}/.env" ]] || return
  set -a
  source "${ROOT_DIR}/.env"
  set +a
  for key value in ${(kv)CALLER_ENVIRONMENT}; do
    export "${key}=${value}"
  done
}
```

Set the same defaults as `scripts/run_local_dev_stack.sh`, using `127.0.0.1:30142`. Implement `ensure_colima` with `colima status`, `colima start`, and `docker context use colima`. Implement `resolve_compose_command` by testing `docker compose version` first and `docker-compose version` second. Store the selected command in `COMPOSE_CMD` and invoke it as `"${COMPOSE_CMD[@]}"`.

Port PID collection must use zsh arrays:

```zsh
local -a pids
pids=("${(@f)$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)}")
```

Replace Bash lowercase expansion with zsh `${value:l}` and replace `wait -n` with a polling loop that exits when either tracked application PID is no longer alive. Preserve migration, admin ownership, seeding, readiness, and frontend proxy behavior from the reference script.

- [ ] **Step 4: Make the script executable and verify GREEN**

Run:

```bash
chmod +x scripts/run_local_dev_stack_macos.sh
uv run pytest tests/unit/test_macos_local_dev_stack_script.py -q
```

Expected: all macOS script contract tests pass.

- [ ] **Step 5: Commit core orchestration**

Run `git add scripts/run_local_dev_stack_macos.sh tests/unit/test_macos_local_dev_stack_script.py && git commit -m "feat: add macOS local stack orchestration"`.

### Task 2: Colored Log Contract

**Files:**
- Modify: `tests/unit/test_macos_local_dev_stack_script.py`
- Modify: `scripts/run_local_dev_stack_macos.sh`

**Interfaces:**
- Consumes: service label (`backend` or `frontend`) and raw log lines on stdin.
- Produces: `prefix_logs <label> <color>` with ANSI only for interactive output and stable plain-text prefixes otherwise.

- [ ] **Step 1: Add failing color tests**

Append:

```python
def test_macos_script_colors_service_logs_and_honors_no_color() -> None:
    text = script_text()
    assert "BACKEND_COLOR=$'\\033[36m'" in text
    assert "FRONTEND_COLOR=$'\\033[35m'" in text
    assert "RESET_COLOR=$'\\033[0m'" in text
    assert '[[ -t 1 && -z "${NO_COLOR:-}" ]]' in text
    assert 'prefix_logs backend "${BACKEND_COLOR}"' in text
    assert 'prefix_logs frontend "${FRONTEND_COLOR}"' in text
    assert '>"${backend_log}" 2>&1 &' in text
    assert '>"${frontend_log}" 2>&1 &' in text
```

- [ ] **Step 2: Run the focused test and verify RED**

Run `uv run pytest tests/unit/test_macos_local_dev_stack_script.py::test_macos_script_colors_service_logs_and_honors_no_color -q`.

Expected: missing color constants and color-aware `prefix_logs` calls.

- [ ] **Step 3: Implement terminal-aware colors**

Add:

```zsh
BACKEND_COLOR=$'\033[36m'
FRONTEND_COLOR=$'\033[35m'
RESET_COLOR=$'\033[0m'

prefix_logs() {
  local label="$1"
  local color="$2"
  if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    awk -v prefix="${color}[${label}] ${RESET_COLOR}" \
      '{ print prefix $0; fflush(); }'
  else
    awk -v prefix="[${label}] " '{ print prefix $0; fflush(); }'
  fi
}
```

Follow raw backend and frontend files using their respective colors. Do not write escape codes into the raw files.

- [ ] **Step 4: Run all script tests**

Run `uv run pytest tests/unit/test_macos_local_dev_stack_script.py tests/unit/test_local_dev_stack_script.py -q`.

Expected: both platform contracts pass.

- [ ] **Step 5: Commit colored logging**

Run `git add scripts/run_local_dev_stack_macos.sh tests/unit/test_macos_local_dev_stack_script.py && git commit -m "feat: color macOS service logs"`.

### Task 3: macOS Documentation

**Files:**
- Modify: `tests/unit/test_macos_local_dev_stack_script.py`
- Modify: `README.md`
- Modify: `docs/ops/macos-colima-docker-setup.md`

**Interfaces:**
- Consumes: the new script's command and behavior.
- Produces: canonical one-command macOS quick start plus retained manual diagnostics.

- [ ] **Step 1: Add failing documentation assertions**

Append:

```python
def test_macos_script_is_documented_as_primary_workflow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/ops/macos-colima-docker-setup.md").read_text(
        encoding="utf-8"
    )
    for text in (readme, runbook):
        assert "./scripts/run_local_dev_stack_macos.sh" in text
    assert "[backend]" in readme
    assert "[frontend]" in readme
    assert "NO_COLOR=1" in runbook
```

- [ ] **Step 2: Run the documentation test and verify RED**

Run `uv run pytest tests/unit/test_macos_local_dev_stack_script.py::test_macos_script_is_documented_as_primary_workflow -q`.

Expected: new command and color behavior are absent.

- [ ] **Step 3: Update README and runbook**

Replace the README's “macOS에서 백엔드와 프론트엔드 각각 실행” introduction with a one-command quick start:

```markdown
### macOS에서 전체 개발 환경 한 번에 실행

```bash
./scripts/run_local_dev_stack_macos.sh
```

스크립트는 `.env`를 자동으로 읽고 Colima, PostgreSQL, 마이그레이션, 백엔드와 Admin UI를 순서대로 준비합니다. 한 터미널에서 백엔드는 청록색 `[backend]`, 프론트엔드는 보라색 `[frontend]`로 표시됩니다.
```

Retain the manual commands under a “수동 실행 및 문제 진단” subsection. Add the same command to the macOS runbook, explain that `Ctrl+C` leaves PostgreSQL running, and document `NO_COLOR=1 ./scripts/run_local_dev_stack_macos.sh`.

- [ ] **Step 4: Run documentation and script tests**

Run `uv run pytest tests/unit/test_macos_local_dev_stack_script.py tests/unit/test_local_dev_stack_script.py tests/unit/test_env_contract.py -q`.

Expected: all selected tests pass.

- [ ] **Step 5: Commit documentation without staging unrelated changes**

Review the existing README and runbook diff first, then stage only the macOS runner documentation hunks and commit them with `git commit -m "docs: document macOS local stack runner"`. Do not stage unrelated pre-existing user edits.

### Task 4: Full Verification

**Files:**
- Verify only; no planned modifications.

**Interfaces:**
- Consumes: completed script, tests, and documentation.
- Produces: evidence that the deliverable is syntactically valid and compatible with the repository checks.

- [ ] **Step 1: Run static checks**

```bash
zsh -n scripts/run_local_dev_stack_macos.sh
uv run ruff check tests/unit/test_macos_local_dev_stack_script.py
uv run mypy src tests
```

Expected: all commands exit zero.

- [ ] **Step 2: Run the complete unit suite**

Run `uv run pytest tests/unit -q`.

Expected: zero failures.

- [ ] **Step 3: Perform macOS smoke verification**

Run `./scripts/run_local_dev_stack_macos.sh`, wait for both readiness messages, request `http://127.0.0.1:30141/readyz`, and log in through the Admin UI using the configured local administrator. Confirm cyan `[backend]` and magenta `[frontend]` prefixes, then press `Ctrl+C` and confirm ports `30140` and `30141` no longer have listeners while the Compose PostgreSQL container remains healthy.

- [ ] **Step 4: Review the final diff**

Run:

```bash
git diff --check
git status --short
git diff -- scripts/run_local_dev_stack_macos.sh tests/unit/test_macos_local_dev_stack_script.py README.md docs/ops/macos-colima-docker-setup.md
```

Expected: only intended files and pre-existing user changes are present; no whitespace errors or secrets are introduced.
