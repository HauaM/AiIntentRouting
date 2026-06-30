from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "docs/ops/pilot-launch-readiness-checklist.md"
CHECKLIST_PATH = "docs/ops/pilot-launch-readiness-checklist.md"


def test_pilot_launch_readiness_checklist_contains_required_contract() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")

    for expected in (
        CHECKLIST_PATH,
        "Pilot Launch Readiness & Evidence Closure",
        "Admin UI excluded from Sprint 7",
        "Dify UI dry-run evidence",
        "Dify workflow version identifier",
        "release-ticket.md",
        "BGE evidence status",
        "measured-pass",
        "pending-host-access exception approval",
        "branch protection evidence",
        "CI / verify",
        "CSV baseline freeze approval",
        "local rehearsal regeneration",
        "pilot go/no-go decision record",
        "Conditional Go",
        "go requires",
        "no secrets",
        "no raw query text",
    ):
        assert expected in text


def test_pilot_launch_readiness_checklist_contains_required_sections() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")

    for heading in (
        "# Pilot Launch Readiness Checklist",
        "## Scope",
        "## Evidence Closure Order",
        "## Local Rehearsal Regeneration",
        "## Dify UI Dry-Run Closure",
        "## Closed-Network BGE Closure",
        "## Branch Protection Closure",
        "## CSV Baseline Freeze Closure",
        "## Release Ticket Review",
        "## Go/No-Go Decision",
        "## Failure Handling",
        "## Files That Must Not Be Committed",
    ):
        assert heading in text


def test_pilot_launch_readiness_checklist_is_secret_scan_safe(tmp_path: Path) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[CHECKLIST])

    assert result == SecretScanResult(passed=True, findings=[])


def test_pilot_launch_readiness_checklist_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
        ROOT / "docs/ops/intent-routing-pilot-runbook.md",
        ROOT / "docs/ops/pilot-evidence-bundle-checklist.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert CHECKLIST_PATH in text
