from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_env_example_uses_runtime_variable_names() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=" in text
    assert "ADMIN_BOOTSTRAP_TOKEN=" in text
    assert "INTENT_ROUTING_ENVIRONMENT=" in text
    assert "RAW_TEXT_KEK_ID=" in text
    assert "RAW_TEXT_KEK_BASE64=" in text
    assert "RAW_KEK_ID=" not in text
    assert "RAW_KEK_BASE64=" not in text


def test_gitignore_excludes_local_operator_outputs() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "var/" in text
    assert "*.secret.json" in text
