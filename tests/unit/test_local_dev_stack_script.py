import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_local_dev_stack.sh"
COMPOSE = ROOT / "compose.yaml"
ENV_EXAMPLE = ROOT / ".env.example"
LOCAL_RUNBOOK = ROOT / "docs/ops/intent-routing-local-runbook.md"


def test_local_dev_stack_script_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "BACKEND_PORT=\"${BACKEND_PORT:-30141}\"" in text
    assert "FRONTEND_PORT=\"${FRONTEND_PORT:-30140}\"" in text
    assert (
        'ADMIN_UI_SERVICE_ID="${ADMIN_UI_SERVICE_ID:-'
        'it-helpdesk-pilot-sprint10-operation-monitoring}"'
    ) in text
    assert (
        'DEFAULT_DATABASE_URL="postgresql+psycopg://'
        'intent:intent@127.0.0.1:30142/intent_routing"'
    ) in text
    assert "uv run alembic upgrade head" in text
    assert "ensure_local_database" in text
    assert "docker compose up -d postgres" in text
    assert "Port 30142 is already used by another container" in text
    assert "Skipping compose postgres management for custom DATABASE_URL" in text
    assert "uv run uvicorn intent_routing.main:create_app --factory" in text
    assert "seed_local_admin_service" in text
    assert "scripts/seed_pilot.py" in text
    assert "--service-id" in text
    assert '"${ADMIN_UI_SERVICE_ID}"' in text
    assert "--port \"${BACKEND_PORT}\"" in text
    assert "ADMIN_API_PROXY=\"http://${HOST}:${BACKEND_PORT}\"" in text
    assert "resolve_pnpm_command" in text
    assert "PNPM_CMD=(corepack pnpm)" in text
    assert '"${PNPM_CMD[@]}" dev' in text
    assert "require_command pnpm" not in text
    assert "stop_port_listeners \"${BACKEND_PORT}\" \"backend\"" in text
    assert "stop_port_listeners \"${FRONTEND_PORT}\" \"frontend\"" in text
    assert "prefix_logs backend" in text
    assert "prefix_logs frontend" in text


def test_local_dev_stack_script_is_executable_bash() -> None:
    mode = SCRIPT.stat().st_mode

    assert mode & stat.S_IXUSR

    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_local_dev_stack_database_port_contract_is_consistent() -> None:
    for path in (COMPOSE, ENV_EXAMPLE, LOCAL_RUNBOOK):
        text = path.read_text(encoding="utf-8")

        assert "127.0.0.1:30142" in text
