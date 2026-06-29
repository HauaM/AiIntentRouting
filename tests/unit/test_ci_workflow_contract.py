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
