from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "docs/ops/pilot-evidence-bundle-checklist.md"


def test_pilot_evidence_bundle_checklist_documents_required_contract() -> None:
    assert CHECKLIST.exists()

    text = CHECKLIST.read_text(encoding="utf-8")

    for expected in (
        "# Pilot Evidence Bundle Checklist",
        "## Local Evidence Generation",
        "## Required Files",
        "## Reviewer Checks",
        "## Secret Scan Confirmation",
        "## Hash Record",
        "## Failure Handling",
        "## Files That Must Not Be Attached",
        "## Ticket Fields To Copy",
        "run_pilot_rehearsal.py",
        "pilot-rehearsal-manifest.json",
        "pilot-rehearsal-manifest.md",
        "final_status: PASS",
        "secret_scan.passed: true",
        "csv-baseline-comparison.md",
        "dify-smoke-matrix.md",
        "ops-evidence.md",
        "no .secret.json",
        "no Bearer token",
        "no RAW_TEXT_KEK_BASE64",
        "no query_raw",
        "sha256sum pilot-rehearsal-manifest.json",
        "do not commit var/evidence",
        "SERVICE_ID",
        "STATE_PATH",
        "ADMIN_BOOTSTRAP_TOKEN",
    ):
        assert expected in text


def test_assigned_docs_link_sprint_6_review_checklist() -> None:
    assert CHECKLIST.exists()

    for path in (
        ROOT / "README.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
        ROOT / "docs/ops/intent-routing-pilot-runbook.md",
        ROOT / "docs/ops/pilot-readiness-evidence.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert "docs/ops/pilot-evidence-bundle-checklist.md" in text
        assert "Sprint 6 review standard" in text
        assert "diagnostic" in text
