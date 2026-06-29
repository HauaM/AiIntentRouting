from __future__ import annotations

from pathlib import Path

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
        "Dify workflow version identifier",
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
