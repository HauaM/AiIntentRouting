import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_LOCAL_ENV = {
    "DATABASE_URL": "postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing",
    "APP_ENV": "local",
    "INTENT_ROUTING_ENVIRONMENT": "dev",
    "ADMIN_AUTH_MODE": "trusted_headers",
    "ADMIN_BOOTSTRAP_TOKEN": "local-admin-token",
    "RAW_TEXT_KEK_ID": "local-kek-001",
    "RAW_TEXT_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "RAW_TEXT_LEGACY_KEKS_JSON": "{}",
    "EMBEDDING_PROVIDER": "fake",
    "BGE_M3_MODEL_PATH": "/models/bge-m3",
    "BGE_M3_MODEL_SHA256": "",
    "BGE_M3_BATCH_SIZE": "16",
    "BGE_M3_MAX_TOKENS": "256",
    "EMBED_EXAMPLES_FROM": "masked",
}


def _parse_env_example() -> dict[str, str]:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    return _parse_env_text(text)


def _parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_env_example_uses_runtime_local_defaults() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    values = _parse_env_example()

    assert values == EXPECTED_LOCAL_ENV
    assert "RAW_KEK_ID=" not in text
    assert "RAW_KEK_BASE64=" not in text


def test_closed_network_env_uses_secret_placeholders_without_live_key_material() -> None:
    text = (ROOT / ".env.closed-network.example").read_text(encoding="utf-8")
    values = _parse_env_text(text)

    assert (
        values["RAW_TEXT_KEK_BASE64"]
        == "replace-with-32-byte-base64-kek-from-approved-secret-store"
    )
    assert values["RAW_TEXT_LEGACY_KEKS_JSON"] == "{}"
    assert "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=" not in text


def test_gitignore_excludes_local_operator_outputs() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "var/" in text
    assert "*.secret.json" in text


def test_project_imports_without_pytest_pythonpath() -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", "import intent_routing"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
