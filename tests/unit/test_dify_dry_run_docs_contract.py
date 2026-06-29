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
        "The rehearsal wrapper records only the Dify workflow version identifier and evidence path.",
        "Screenshots and workflow exports must show masked values only.",
        "Do not paste screenshot/export contents into pilot-rehearsal-manifest.md.",
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
        "masked screenshot or workflow export path",
        "Dify secret variable for the Intent Routing API key",
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
