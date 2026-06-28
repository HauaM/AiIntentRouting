import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dify_http_request_node_template_carries_runtime_contract() -> None:
    template = json.loads(
        (ROOT / "docs/integrations/dify-http-request-node-template.json").read_text(
            encoding="utf-8"
        )
    )

    assert template["node_type"] == "http_request"
    assert template["method"] == "POST"
    assert template["url"] == "http://intent-routing.internal/v1/intent-route"
    assert template["timeout_seconds"] == 8
    headers = {header["name"]: header["value"] for header in template["headers"]}
    assert headers == {
        "Authorization": "Bearer {{intent_routing_api_key}}",
        "X-Key-Id": "{{intent_routing_key_id}}",
        "X-App-Id": "dify-platform",
        "X-Service-Id": "{{service_id}}",
        "X-Request-Id": "{{workflow_run_id}}",
        "Content-Type": "application/json",
    }
    assert template["body"]["query"] == "{{user_query}}"
    assert template["body"]["channel"] == "chat"
    assert template["body"]["user_context"]["workflow_run_id"] == "{{workflow_run_id}}"


def test_dify_template_documents_all_decision_and_error_branches() -> None:
    template = json.loads(
        (ROOT / "docs/integrations/dify-http-request-node-template.json").read_text(
            encoding="utf-8"
        )
    )
    branches = {branch["name"]: branch for branch in template["branches"]}

    for expected in (
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
    ):
        assert expected in branches
        assert "trace_id" in branches[expected]["carry"]
        assert "request_id" in branches[expected]["carry"]


def test_dify_branching_playbook_links_template_and_timeout_policy() -> None:
    text = (ROOT / "docs/integrations/dify-branching-playbook.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "docs/integrations/dify-http-request-node-template.json",
        "decision=confident",
        "decision=clarify",
        "decision=fallback",
        "decision=off_topic",
        "decision=risk",
        "decision=unauthorized",
        "401",
        "403",
        "422",
        "408",
        "5xx",
        "timeout",
        "no automatic retry loop",
    ):
        assert expected in text
