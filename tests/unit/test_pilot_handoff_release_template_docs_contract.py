from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/ops/pilot-handoff-release-ticket-template.md"
TEMPLATE_PATH = "docs/ops/pilot-handoff-release-ticket-template.md"
GO_NO_GO_TEMPLATE_PATH = "docs/ops/pilot-go-no-go-decision-template.md"
GO_NO_GO_DECISION_RECORD_PATH = (
    "var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md"
)


def _compact(text: str) -> str:
    return " ".join(text.split())


def _section(text: str, start_heading: str, end_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start + len(start_heading))
    return text[start:end]


def _assert_go_no_go_decision_record_criteria(text: str) -> None:
    assert GO_NO_GO_TEMPLATE_PATH in text
    assert GO_NO_GO_DECISION_RECORD_PATH in text
    assert "release-ticket.md" in text
    assert "no secrets" in text
    assert "no raw query text" in text


def test_pilot_handoff_release_ticket_template_contains_required_contract() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for expected in (
        TEMPLATE_PATH,
        "service_id",
        "environment",
        "release_version",
        "commit SHA",
        "PR URL",
        "CI / verify",
        "var/evidence/${SERVICE_ID}/release-ticket.md",
        GO_NO_GO_TEMPLATE_PATH,
        GO_NO_GO_DECISION_RECORD_PATH,
        "Reviewer command source: docs/ops/pilot-launch-readiness-checklist.md",
        "Runbook command source: docs/ops/intent-routing-pilot-runbook.md",
        "Required evidence reference scan result:",
        "Forbidden marker scan result:",
        "release ticket reviewer",
        "Evidence links only: yes / no",
        "No screenshot contents: yes / no",
        "No workflow export contents: yes / no",
        "No secrets or raw query text: yes / no",
        f"Go/no-go decision record: {GO_NO_GO_DECISION_RECORD_PATH}",
        "Decision value: Go / No Go / Conditional Go",
        "Conditional Go conditions",
        "Blocked gates",
        "Owner:",
        "Approval ID:",
        "local rehearsal manifest",
        "manifest sha256",
        "Dify workflow version identifier",
        "Dify UI evidence path",
        "Dify UI dry-run evidence reviewer",
        "Dify evidence linked from release ticket",
        "Dify condition owner",
        "Follow-up approval ID, if blocked",
        "BGE evidence status",
        "branch protection evidence",
        "CSV baseline comparison",
        "docs/pilot/csv-baseline-freeze-approval-template.md",
        "CSV baseline freeze approval",
        "Refresh status: refresh not approved / policy-approved refresh attached",
        "Freeze approval ID",
        "Release owner",
        "QA or security reviewer",
        "rollback plan",
        "go/no-go",
        "Admin UI excluded",
        "no secrets",
        "no raw query text",
    ):
        assert expected in text


def test_pilot_handoff_release_ticket_template_contains_required_sections() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for heading in (
        "# Pilot Handoff And Release Ticket Template",
        "## Release Scope",
        "## Code And CI",
        "## Local Rehearsal Evidence",
        "## Dify UI Dry-Run Evidence",
        "## Closed-Network BGE Evidence",
        "## Branch Protection Evidence",
        "## CSV Baseline Evidence",
        "## Security And Incident Rehearsal Evidence",
        "## Rollback Plan",
        "## Evidence Closure Review",
        "## Open Risks",
        "## Go/No Go Decision",
        "## Approvals",
    ):
        assert heading in text


def test_pilot_handoff_release_ticket_template_documents_required_gates() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    go_no_go_section = _compact(
        _section(text, "## Go/No Go Decision", "## Approvals")
    )

    for marker_group in (
        ("go requires", "CI / verify", "pass"),
        ("go requires", "local rehearsal", "final_status PASS"),
        ("go requires", "local rehearsal", "secret_scan.passed true"),
        ("Dify UI evidence path", "workflow version identifier"),
        ("Dify UI dry-run evidence reviewer", "approval"),
        ("Dify UI evidence path", "release-ticket.md"),
        ("blocked Dify evidence", "condition owner", "approval ID"),
        ("CSV baseline comparison", "PASS"),
        ("CSV baseline freeze approval", "policy-approved refresh approval"),
        ("branch protection evidence", "main"),
        ("authorized branch protection evidence", "main"),
        ("operator-not-permitted", "pilot go/no-go"),
        ("Admin UI excluded", "Sprint 7"),
        ("ticket", "no secrets", "raw query text"),
        ("BGE measured-pass", "closed-network pilot traffic"),
        (
            "Conditional Go",
            "pending-host-access",
            "exception approval ID",
            "exception owner",
            "expiration before pilot traffic",
            "next measurement date",
        ),
        ("measured-fail", "pilot launch", "corrected evidence passes"),
        (
            "rollback or bypass evidence",
            "approval ID",
            "exact commit SHA",
            "workflow_dispatch rerun URL",
            "artifact review result",
            "final branch protection state",
        ),
    ):
        for marker in marker_group:
            assert marker in go_no_go_section


def test_pilot_handoff_release_ticket_template_references_reviewer_command_sources() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for expected in (
        "Run reviewer commands from the checklist; do not copy command text "
        "into release-ticket.md.",
        "Reviewer command source: docs/ops/pilot-launch-readiness-checklist.md",
        "Runbook command source: docs/ops/intent-routing-pilot-runbook.md",
        "Required evidence reference scan result:",
        "Forbidden marker scan result:",
    ):
        assert expected in text


def test_pilot_handoff_release_ticket_template_documents_go_no_go_record_link_criteria() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    _assert_go_no_go_decision_record_criteria(text)


def test_pilot_handoff_release_ticket_template_omits_copy_unsafe_commands() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for forbidden in (
        "rg -n 'PASS|CI / verify",
        "rg -n 'Bearer |Authorization: Bearer",
        "RAW_TEXT_KEK_BASE64",
        "RAW_TEXT_LEGACY_KEKS_JSON",
        "api_key=",
        "intent_routing_api_key",
        "query_raw",
        "text_raw",
        "encrypted_dek",
        "ciphertext",
        "irt_live_",
        "irt_secret",
    ):
        assert forbidden not in text


def test_pilot_handoff_release_ticket_template_is_secret_scan_safe(
    tmp_path: Path,
) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[TEMPLATE])

    assert result == SecretScanResult(passed=True, findings=[])


def test_pilot_handoff_release_ticket_template_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs/ops/intent-routing-pilot-runbook.md",
        ROOT / "docs/integrations/dify-handoff-checklist.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert TEMPLATE_PATH in text


def test_pilot_rehearsal_documents_release_ticket_dry_fill_scans() -> None:
    text = (ROOT / "docs/ops/pilot-rehearsal.md").read_text(encoding="utf-8")

    assert (
        "rg -n 'PASS|CI / verify|pilot-rehearsal-manifest.md|"
        "Dify workflow version identifier|go/no-go' "
        "var/evidence/${SERVICE_ID}/release-ticket.md"
    ) in text

    for marker in (
        "Bearer ",
        "RAW_TEXT_KEK_BASE64",
        "RAW_TEXT_LEGACY_KEKS_JSON",
        "api_key=",
        "Authorization: Bearer",
        "intent_routing_api_key",
        "query_raw",
        "text_raw",
        "encrypted_dek",
        "ciphertext",
        "irt_live_",
        "irt_secret",
    ):
        assert marker in text


def test_pilot_rehearsal_documents_go_no_go_record_link_criteria() -> None:
    text = (ROOT / "docs/ops/pilot-rehearsal.md").read_text(encoding="utf-8")

    _assert_go_no_go_decision_record_criteria(text)
