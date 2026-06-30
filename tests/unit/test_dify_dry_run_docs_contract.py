from __future__ import annotations

from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]


def test_dify_dry_run_rehearsal_doc_covers_operator_contract() -> None:
    doc = ROOT / "docs/integrations/dify-dry-run-rehearsal.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    for expected in (
        "Dify workflow version identifier",
        'export STATE_PATH="var/pilot/${SERVICE_ID}/pilot.state.secret.json"',
        "intent_routing_api_key secret variable",
        "workflow_run_id",
        "Timeout: 8 seconds",
        "no automatic retry loop",
        "dify-smoke-matrix.json",
        "dify-smoke-matrix.md",
        "pilot-rehearsal-manifest.md",
        "confident",
        "clarify",
        "fallback",
        "off_topic",
        "risk",
        "unauthorized",
        "401",
        "403",
        "422",
        "408",
        "5xx",
        "timeout",
        "trace_id",
        "request_id",
        "release_version",
    ):
        assert expected in text

    assert (
        'export STATE_PATH="var/evidence/${SERVICE_ID}/pilot.state.secret.json"'
        not in text
    )


def test_dify_checklists_link_dry_run_rehearsal_and_metadata() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "docs/integrations/dify-handoff-checklist.md",
            ROOT / "docs/integrations/dify-http-request-node.md",
            ROOT / "docs/integrations/dify-branching-playbook.md",
        )
    )

    for expected in (
        "dify-dry-run-rehearsal.md",
        "dify-dry-run-evidence-template.md",
        "Dify workflow version identifier",
        "The rehearsal wrapper records only the Dify workflow version identifier "
        "and evidence path.",
        "Screenshots and workflow exports must show masked values only.",
        "Do not paste screenshot/export contents into pilot-rehearsal-manifest.md.",
        "go requires Dify UI dry-run evidence reviewer approval.",
        "go requires the Dify UI evidence path to be linked from release-ticket.md.",
        "blocked Dify evidence requires a condition owner and approval ID before Conditional Go.",
        "pilot-rehearsal-manifest.md",
        "dify-smoke-matrix.json",
        "dify-smoke-matrix.md",
        "intent_routing_api_key secret variable",
        "workflow_run_id",
        "trace_id",
        "request_id",
        "release_version",
    ):
        assert expected in combined


def test_dify_dry_run_evidence_template_covers_ui_contract() -> None:
    doc = ROOT / "docs/integrations/dify-dry-run-evidence-template.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    for expected in (
        "docs/integrations/dify-dry-run-evidence-template.md",
        "Dify workflow version identifier",
        "var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md",
        "release-ticket.md",
        "pilot-go-no-go-decision.md",
        "operator result must be pass, fail, or blocked",
        "Dify UI evidence reviewer",
        "masked screenshot or sanitized workflow export",
        "do not attach unmasked screenshots",
        "masked screenshot or workflow export path",
        "Condition owner, if blocked",
        "Follow-up approval ID, if blocked",
        "intent_routing_api_key secret variable",
        "workflow_run_id",
        "Timeout: 8 seconds",
        "no automatic retry loop",
        "confident",
        "clarify",
        "fallback",
        "off_topic",
        "risk",
        "unauthorized",
        "401",
        "403",
        "422",
        "408",
        "5xx",
        "timeout",
        "trace_id",
        "request_id",
        "release_version",
        "pilot-rehearsal-manifest.md",
    ):
        assert expected in text


def test_dify_dry_run_evidence_template_is_secret_scan_safe(
    tmp_path: Path,
) -> None:
    doc = ROOT / "docs/integrations/dify-dry-run-evidence-template.md"
    assert doc.exists()

    result = scan_evidence_directory(tmp_path, extra_paths=[doc])

    assert result == SecretScanResult(passed=True, findings=[])


def test_secret_scan_allows_approved_dify_secret_variable_label(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "dify-dry-run-evidence.md"
    evidence.write_text(
        "HTTP authorization header uses the intent_routing_api_key secret variable.\n",
        encoding="utf-8",
    )

    result = scan_evidence_directory(tmp_path)

    assert result == SecretScanResult(passed=True, findings=[])
