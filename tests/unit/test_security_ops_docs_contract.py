from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_security_operations_runbook_documents_required_controls() -> None:
    text = (ROOT / "docs/ops/security-operations.md").read_text(encoding="utf-8")

    for expected in (
        "API key lifecycle",
        "create",
        "overlap",
        "smoke",
        "revoke",
        "rollback",
        "ADMIN_BOOTSTRAP_TOKEN",
        "system_admin",
        "service_developer",
        "service_operator",
        "auditor",
        "RAW_TEXT_KEK_ID",
        "RAW_TEXT_KEK_BASE64",
        "single active KEK",
        "rewrap",
        "approval ID",
        "raw_query.viewed",
    ):
        assert expected in text


def test_security_operations_runbook_does_not_include_secret_values() -> None:
    text = (ROOT / "docs/ops/security-operations.md").read_text(encoding="utf-8")

    for forbidden in (
        "local-admin-token",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "irt_secret",
    ):
        assert forbidden not in text
