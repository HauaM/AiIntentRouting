from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_dockerfile_uses_locked_uv_runtime_contract() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "python:3.12" in dockerfile
    assert "PYTHONUNBUFFERED=1" in dockerfile
    assert "uv sync --locked" in dockerfile
    assert "uv run uvicorn intent_routing.main:create_app --factory" in dockerfile
    assert "USER app" in dockerfile
    for forbidden in (
        "local-admin-token",
        "RAW_TEXT_KEK_BASE64=AAAAAAAA",
        "irt_",
    ):
        assert forbidden not in dockerfile


def test_dockerignore_excludes_local_state_and_caches() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    for expected in (
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "var",
        "*.secret.json",
    ):
        assert expected in dockerignore


def test_closed_network_env_contract_uses_release_owned_bge_profile() -> None:
    env_text = (ROOT / ".env.closed-network.example").read_text(encoding="utf-8")
    values = _parse_env(env_text)

    assert values["ALLOWED_RUNTIME_ENVIRONMENTS"] == "dev,qa,prod"
    assert values["EMBEDDING_PROVIDER"] == "bge-m3"
    assert values["BGE_M3_MODEL_PATH"] == "/models/bge-m3"
    assert values["BGE_M3_BATCH_SIZE"] == "16"
    assert values["BGE_M3_MAX_TOKENS"] == "256"
    assert "replace-with-db-password" in values["DATABASE_URL"]
    assert values["ADMIN_BOOTSTRAP_TOKEN"] == "replace-with-internal-secret-manager-value"
    assert (
        values["RAW_TEXT_KEK_BASE64"]
        == "replace-with-32-byte-base64-kek-from-approved-secret-store"
    )
    assert "RAW_KEK_ID=" not in env_text
    assert "RAW_KEK_BASE64=" not in env_text


def test_compose_has_runtime_profile_migrate_api_and_readiness_healthcheck() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "postgres:" in compose
    assert "migrate:" in compose
    assert "api:" in compose
    assert "profiles:" in compose
    assert "- runtime" in compose
    assert "uv run alembic upgrade head" in compose
    assert "uv run uvicorn intent_routing.main:create_app --factory" in compose
    assert "/models/bge-m3:/models/bge-m3:ro" in compose
    assert "http://127.0.0.1:8000/readyz" in compose
    assert "condition: service_healthy" in compose
    assert "condition: service_completed_successfully" in compose


def test_closed_network_deployment_runbook_documents_operator_sequence() -> None:
    runbook = (ROOT / "docs/ops/closed-network-deployment.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "docker compose --profile runtime build",
        "docker save",
        "docker load",
        "docker compose --profile runtime up -d postgres migrate api",
        "curl -s http://127.0.0.1:8000/healthz",
        "curl -s http://127.0.0.1:8000/readyz",
        "ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod",
        "/models/bge-m3",
        "release_version",
        ".env.closed-network.example",
    ):
        assert expected in runbook


def _parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values
