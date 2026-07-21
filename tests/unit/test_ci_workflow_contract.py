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


def test_ci_locked_install_uses_repository_lockfile() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitignore_entries = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "uv sync --locked --group dev" in text
    assert (ROOT / "uv.lock").exists()
    assert "uv.lock" not in gitignore_entries


def test_ci_workflow_uses_fake_embedding_and_no_real_secrets() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "EMBEDDING_PROVIDER: fake" in text
    assert "ALLOWED_RUNTIME_ENVIRONMENTS: dev,qa,prod" in text
    assert "RAW_TEXT_KEK_ID: ci-kek-001" in text
    assert "API_KEY_SECRET_KEK_ID: ci-api-key-secret-kek-001" in text
    assert (
        "API_KEY_SECRET_KEK_BASE64: "
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=" in text
    )
    assert 'API_KEY_SECRET_LEGACY_KEKS_JSON: "{}"' in text
    for forbidden in (
        "replace-with",
        "intent_routing_api_key",
        "Bearer ",
        "RAW_TEXT_LEGACY_KEKS_JSON: {",
    ):
        assert forbidden not in text


def test_ci_workflow_runs_pilot_e2e_smoke_and_uploads_non_secret_evidence() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    step_names = _workflow_step_names(text)
    stop_step = _workflow_step_block(text, "Stop API")
    upload_step = _workflow_step_block(text, "Upload pilot e2e evidence")

    for expected in (
        "Start API",
        "uv run uvicorn intent_routing.main:create_app --factory",
        "Run pilot e2e smoke",
        "scripts/run_pilot_e2e_smoke.py",
        "--required-preset balanced",
        "Stop API",
        "Upload pilot e2e evidence",
        "actions/upload-artifact@v4",
    ):
        assert expected in text

    assert step_names.index("Start API") < step_names.index("Run pilot e2e smoke")
    assert step_names.index("Run pilot e2e smoke") < step_names.index("Stop API")
    assert step_names.index("Stop API") < step_names.index("Upload pilot e2e evidence")
    assert step_names.index("Upload pilot e2e evidence") < step_names.index("Test")

    assert _yaml_scalar(stop_step, "if") == "always()"
    assert "var/logs/api.pid" in stop_step
    assert "kill" in stop_step
    assert "wait" in stop_step

    assert _yaml_scalar(upload_step, "if") == "always()"
    assert _yaml_scalar(upload_step, "uses") == "actions/upload-artifact@v4"
    assert _yaml_scalar(upload_step, "retention-days") == "14"

    artifact_paths = _yaml_literal_block_lines(upload_step, "path")
    assert artifact_paths == [
        "var/evidence/**/*",
        "var/logs/api.log",
    ]
    for forbidden in (
        "var/**",
        "var/**/*",
        "var/pilot",
        "var/pilot/**",
        "var/pilot/**/*",
        "*.secret.json",
    ):
        assert forbidden not in artifact_paths


def _workflow_step_names(text: str) -> list[str]:
    return [section.splitlines()[0] for section in text.split("\n      - name: ")[1:]]


def _workflow_step_block(text: str, name: str) -> str:
    marker = f"\n      - name: {name}\n"
    _, separator, rest = text.partition(marker)
    if not separator:
        raise AssertionError(f"missing workflow step: {name}")
    block, _, _ = rest.partition("\n      - name: ")
    return f"      - name: {name}\n{block}"


def _yaml_scalar(block: str, key: str) -> str:
    prefix = f"{key}:"
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix).strip()
    raise AssertionError(f"missing scalar key: {key}")


def _yaml_literal_block_lines(block: str, key: str) -> list[str]:
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"{key}: |":
            continue
        key_indent = len(line) - len(line.lstrip())
        values: list[str] = []
        for value_line in lines[index + 1 :]:
            stripped = value_line.strip()
            indent = len(value_line) - len(value_line.lstrip())
            if stripped and indent <= key_indent:
                break
            if stripped:
                values.append(stripped)
        return values
    raise AssertionError(f"missing literal block key: {key}")
