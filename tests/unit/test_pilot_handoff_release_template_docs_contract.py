from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/ops/pilot-handoff-release-ticket-template.md"
TEMPLATE_PATH = "docs/ops/pilot-handoff-release-ticket-template.md"


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
        "local rehearsal manifest",
        "manifest sha256",
        "Dify workflow version identifier",
        "Dify UI evidence path",
        "BGE evidence status",
        "branch protection evidence",
        "CSV baseline comparison",
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
        "## Open Risks",
        "## Go/No-Go Decision",
        "## Approvals",
    ):
        assert heading in text


def test_pilot_handoff_release_ticket_template_documents_required_gates() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for gate in (
        "go requires CI / verify pass",
        "go requires local rehearsal final_status PASS",
        "go requires local rehearsal secret_scan.passed true",
        "go requires Dify UI evidence path and workflow version identifier",
        "go requires CSV baseline comparison PASS",
        "go requires branch protection evidence for main",
        "go requires BGE measured-pass before closed-network pilot traffic",
        "Admin UI excluded from Sprint 6",
        "ticket must not contain secrets or raw query text",
    ):
        assert gate in text


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
