from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "docs/ops/pilot-launch-readiness-checklist.md"
CHECKLIST_PATH = "docs/ops/pilot-launch-readiness-checklist.md"


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_pilot_launch_readiness_checklist_contains_required_contract() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")
    compact_text = _compact(text)

    for expected in (
        CHECKLIST_PATH,
        "Pilot Launch Readiness & Evidence Closure",
        "Admin UI excluded from Sprint 7",
        "Dify UI dry-run evidence",
        "Dify workflow version identifier",
        "Dify UI dry-run evidence reviewer",
        "Dify evidence linked from release ticket",
        "Dify condition owner",
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

    for expected in (
        "go requires BGE measured-pass before closed-network pilot traffic",
        (
            "Conditional Go with pending-host-access requires exception "
            "approval ID, exception owner, expiration before pilot traffic, "
            "and next measurement date"
        ),
        "measured-fail blocks pilot launch until corrected evidence passes",
        (
            "Do not convert a failed measurement into Conditional Go. Keep the "
            "decision as No Go until the evidence is corrected, regenerated, "
            "and accepted as measured-pass."
        ),
    ):
        assert expected in compact_text


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
