import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from intent_routing.db.session import get_database_url

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_LOCAL_ENV = {
    "DATABASE_URL": "postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing",
    "APP_ENV": "local",
    "ALLOWED_RUNTIME_ENVIRONMENTS": "dev,qa,prod",
    "ADMIN_AUTH_MODE": "trusted_headers",
    "ADMIN_BOOTSTRAP_TOKEN": "local-admin-token",
    "RAW_TEXT_KEK_ID": "local-kek-001",
    "RAW_TEXT_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "RAW_TEXT_LEGACY_KEKS_JSON": "{}",
    "API_KEY_SECRET_KEK_ID": "local-api-key-secret-kek-001",
    "API_KEY_SECRET_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "API_KEY_SECRET_LEGACY_KEKS_JSON": "{}",
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
    assert "# ADMIN_SYSTEM_ADMIN_EMAIL=local-admin@example.com" in text
    assert "# ADMIN_SYSTEM_ADMIN_PASSWORD=local-admin-password" in text
    assert "# ADMIN_SYSTEM_ADMIN_DISPLAY_NAME=Local Admin" in text
    assert "ADMIN_SYSTEM_ADMIN_EMAIL" not in values
    assert "ADMIN_SYSTEM_ADMIN_PASSWORD" not in values


def test_database_url_fallback_matches_local_compose_port(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert (
        get_database_url()
        == "postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing"
    )


def test_runtime_environment_allowlist_defaults_to_dev_qa_prod(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOWED_RUNTIME_ENVIRONMENTS", raising=False)

    from intent_routing.config import get_allowed_runtime_environments

    assert get_allowed_runtime_environments() == frozenset({"dev", "qa", "prod"})


def test_runtime_environment_allowlist_rejects_unknown_values(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOWED_RUNTIME_ENVIRONMENTS", "dev,test,prod")

    from intent_routing.config import get_allowed_runtime_environments

    with pytest.raises(ValueError, match="unsupported runtime environment"):
        get_allowed_runtime_environments()


def test_api_key_secret_keyring_config_requires_kek(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY_SECRET_KEK_BASE64", raising=False)

    from intent_routing.config import (
        MissingApiKeySecretKekError,
        load_api_key_secret_keyring_config,
    )

    with pytest.raises(MissingApiKeySecretKekError):
        load_api_key_secret_keyring_config({})


def test_api_key_secret_keyring_config_accepts_legacy_keks() -> None:
    from intent_routing.config import load_api_key_secret_keyring_config

    config = load_api_key_secret_keyring_config(
        {
            "API_KEY_SECRET_KEK_ID": "active-kek",
            "API_KEY_SECRET_KEK_BASE64": "active-secret",
            "API_KEY_SECRET_LEGACY_KEKS_JSON": '{"retired-kek":"retired-secret"}',
        }
    )

    assert config.active_key_id == "active-kek"
    assert config.active_kek_base64 == "active-secret"
    assert config.legacy_keks == {"retired-kek": "retired-secret"}


def test_api_key_secret_keyring_config_reports_its_malformed_legacy_json_key() -> None:
    from intent_routing.config import load_api_key_secret_keyring_config

    with pytest.raises(
        ValueError,
        match="API_KEY_SECRET_LEGACY_KEKS_JSON must be valid JSON",
    ):
        load_api_key_secret_keyring_config(
            {
                "API_KEY_SECRET_KEK_BASE64": "active-secret",
                "API_KEY_SECRET_LEGACY_KEKS_JSON": "not-json",
            }
        )


def test_api_key_secret_keyring_config_rejects_active_legacy_key_id_collision() -> None:
    from intent_routing.config import load_api_key_secret_keyring_config

    with pytest.raises(
        ValueError,
        match="active key_id must not appear in API_KEY_SECRET_LEGACY_KEKS_JSON",
    ):
        load_api_key_secret_keyring_config(
            {
                "API_KEY_SECRET_KEK_ID": "active-kek",
                "API_KEY_SECRET_KEK_BASE64": "active-secret",
                "API_KEY_SECRET_LEGACY_KEKS_JSON": '{"active-kek":"retired-secret"}',
            }
        )


def test_api_key_secret_keyring_config_repr_does_not_expose_kek_material() -> None:
    from intent_routing.config import load_api_key_secret_keyring_config

    config = load_api_key_secret_keyring_config(
        {
            "API_KEY_SECRET_KEK_BASE64": "active-secret",
            "API_KEY_SECRET_LEGACY_KEKS_JSON": '{"retired-kek":"retired-secret"}',
        }
    )

    config_repr = repr(config)

    assert "active-secret" not in config_repr
    assert "retired-secret" not in config_repr


def test_closed_network_env_uses_secret_placeholders_without_live_key_material() -> None:
    text = (ROOT / ".env.closed-network.example").read_text(encoding="utf-8")
    values = _parse_env_text(text)

    assert (
        values["RAW_TEXT_KEK_BASE64"]
        == "replace-with-32-byte-base64-kek-from-approved-secret-store"
    )
    assert values["RAW_TEXT_LEGACY_KEKS_JSON"] == "{}"
    assert (
        values["API_KEY_SECRET_KEK_BASE64"]
        == "replace-with-32-byte-base64-kek-from-approved-secret-store"
    )
    assert values["API_KEY_SECRET_LEGACY_KEKS_JSON"] == "{}"
    assert "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=" not in text


def test_ci_verification_docs_include_api_key_secret_kek_contract() -> None:
    text = (ROOT / "docs/ops/ci-verification.md").read_text(encoding="utf-8")

    assert "export API_KEY_SECRET_KEK_ID=ci-api-key-secret-kek-001" in text
    assert (
        "export API_KEY_SECRET_KEK_BASE64="
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=" in text
    )
    assert 'export API_KEY_SECRET_LEGACY_KEKS_JSON="{}"' in text


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
