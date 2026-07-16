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
        ["zsh", "-n", str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
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


def test_macos_script_avoids_zsh_host_and_json_expansion_traps() -> None:
    text = script_text()
    capture_block = text.split("for key in", 1)[1].split("; do", 1)[0]

    assert " HOST " not in capture_block
    assert 'export HOST="${LOCAL_DEV_HOST:-127.0.0.1}"' in text
    assert 'RAW_TEXT_LEGACY_KEKS_JSON="{}"' in text
    assert 'RAW_TEXT_LEGACY_KEKS_JSON:-{}' not in text
