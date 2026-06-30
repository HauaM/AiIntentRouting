from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/ops/pilot-go-no-go-decision-template.md"
TEMPLATE_PATH = "docs/ops/pilot-go-no-go-decision-template.md"


def _compact(text: str) -> str:
    return " ".join(text.split())


def _assert_markers(text: str, markers: tuple[str, ...]) -> None:
    for marker in markers:
        assert marker in text


def test_pilot_go_no_go_decision_template_contains_required_contract() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    _assert_markers(
        text,
        (
            TEMPLATE_PATH,
            "Pilot Go/No Go Decision Template",
            "release-ticket.md",
            "Dify UI dry-run evidence",
            "BGE evidence status",
            "branch protection evidence",
            "CSV baseline freeze approval",
            "local rehearsal final_status PASS",
            "secret_scan.passed true",
            "blocked gate",
            "condition owner",
            "approval ID",
            "expires before pilot traffic",
            "Admin UI excluded from Sprint 7",
            "no secrets",
            "no raw query text",
        ),
    )

    allowed_values = {
        line.removeprefix("- ").strip()
        for line in text.splitlines()
        if line in {"- Go", "- No Go", "- Conditional Go"}
    }
    assert allowed_values == {"Go", "No Go", "Conditional Go"}

    legacy_no_go = "No" + "-Go"
    assert legacy_no_go not in text


def test_pilot_go_no_go_decision_template_documents_gate_result_fields() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    _assert_markers(
        text,
        (
            "CI / verify:",
            "local rehearsal final_status PASS:",
            "local rehearsal secret_scan.passed true:",
            "Dify UI dry-run evidence:",
            "BGE evidence status:",
            "branch protection evidence:",
            "CSV baseline freeze approval:",
            "release ticket review:",
            "Admin UI excluded from Sprint 7:",
            "pending-host-access",
            "expires before pilot traffic",
            "blocks closed-network pilot traffic",
        ),
    )


def test_pilot_go_no_go_decision_template_documents_decision_criteria() -> None:
    compact_text = _compact(TEMPLATE.read_text(encoding="utf-8"))

    _assert_markers(
        compact_text,
        (
            "Go only when every required gate has accepted evidence",
            "owner approval",
            "Conditional Go only for approved, bounded conditions",
            "condition owner",
            "approval ID",
            "expiry",
            "next review date",
            "launch boundary impact",
            "No Go when evidence is missing, failed, unsafe, or unapproved",
            "Failed or unapproved evidence cannot be converted",
        ),
    )


def test_pilot_go_no_go_decision_template_documents_conditional_go_fields() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "Each Conditional Go condition requires:" in text
    _assert_markers(
        text,
        (
            "- blocked gate:",
            "- condition owner:",
            "- approval ID:",
            "- expiry:",
            "- next review date:",
            "- launch boundary impact:",
        ),
    )


def test_pilot_go_no_go_decision_template_contains_required_sections() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for heading in (
        "# Pilot Go/No Go Decision Template",
        "## Decision",
        "## Decision Criteria",
        "## Evidence Summary",
        "## Gate Results",
        "## Conditional Go Conditions",
        "## Blocked Gates",
        "## Approval Record",
        "## Launch Boundary",
        "## Secret And Raw Query Review",
    ):
        assert heading in text


def test_pilot_go_no_go_decision_template_is_secret_scan_safe(
    tmp_path: Path,
) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[TEMPLATE])

    assert result == SecretScanResult(passed=True, findings=[])


def test_pilot_go_no_go_decision_template_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "docs/ops/pilot-handoff-release-ticket-template.md",
        ROOT / "docs/ops/pilot-launch-readiness-checklist.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert TEMPLATE_PATH in text
