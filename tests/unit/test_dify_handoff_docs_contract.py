from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dify_handoff_checklist_contains_required_operator_controls() -> None:
    checklist = ROOT / "docs/integrations/dify-handoff-checklist.md"
    assert checklist.exists()
    text = checklist.read_text(encoding="utf-8")

    for expected in (
        "# Dify Handoff Checklist",
        "intent_routing_api_key",
        "X-Request-Id",
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
        "dify-smoke-matrix.json",
        "dify-smoke-matrix.md",
        "readiness-report.md",
        "threshold comparison Markdown",
        "Dify workflow version identifier",
        "trace_id",
        "request_id",
        "release_version",
        "risk branch does not call business route",
    ):
        assert expected in text


def test_dify_integration_docs_link_to_handoff_checklist() -> None:
    for path in (
        ROOT / "docs/integrations/dify-http-request-node.md",
        ROOT / "docs/integrations/dify-branching-playbook.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "dify-handoff-checklist.md" in text
