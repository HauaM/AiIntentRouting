from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_security_lifecycle_runbook_documents_required_workflows() -> None:
    text = (ROOT / "docs/ops/security-lifecycle.md").read_text(encoding="utf-8")

    for expected in (
        "KEK rotation prerequisites",
        "RAW_TEXT_KEK_ID",
        "RAW_TEXT_KEK_BASE64",
        "RAW_TEXT_LEGACY_KEKS_JSON",
        "scripts/rewrap_raw_text.py",
        "--dry-run",
        "--execute",
        "--confirm-active-key-id",
        "raw-text-key-summary",
        "scripts/apply_log_retention.py",
        "runtime raw-query retention",
        "scripts/export_ops_evidence.py",
        "ops-evidence.json",
        "ops-evidence.md",
        "Rollback before rewrap",
        "Rollback after rewrap",
        "secret leak checks",
    ):
        assert expected in text


def test_security_lifecycle_runbook_does_not_include_secret_values() -> None:
    text = (ROOT / "docs/ops/security-lifecycle.md").read_text(encoding="utf-8")

    for forbidden in (
        "local-admin-token",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=",
        "irt_secret",
    ):
        assert forbidden not in text
