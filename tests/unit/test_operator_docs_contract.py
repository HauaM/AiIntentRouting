from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_and_pilot_runbook_document_repeatable_local_environment() -> None:
    texts = [
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "docs/ops/intent-routing-pilot-runbook.md").read_text(encoding="utf-8"),
    ]

    for text in texts:
        assert "export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod" in text
        assert "export RAW_TEXT_KEK_BASE64=" in text
        assert "export ADMIN_BOOTSTRAP_TOKEN=local-admin-token" in text
        assert "export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)" in text
        assert "var/pilot/${SERVICE_ID}.state.secret.json" in text
        assert "--service-id ${SERVICE_ID}" in text
        assert "--state ${STATE_PATH}" in text


def test_operator_docs_link_closed_network_deployment_runbook() -> None:
    texts = [
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "docs/ops/intent-routing-local-runbook.md").read_text(encoding="utf-8"),
        (ROOT / "docs/ops/intent-routing-pilot-runbook.md").read_text(encoding="utf-8"),
    ]

    for text in texts:
        assert "docs/ops/closed-network-deployment.md" in text


def test_operator_docs_link_security_lifecycle_and_ops_evidence_workflow() -> None:
    texts = [
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "docs/ops/closed-network-deployment.md").read_text(encoding="utf-8"),
        (ROOT / "docs/ops/pilot-readiness-evidence.md").read_text(encoding="utf-8"),
    ]

    for text in texts:
        assert "docs/ops/security-lifecycle.md" in text
        assert "scripts/export_ops_evidence.py" in text
        assert "ops-evidence.json" in text
        assert "ops-evidence.md" in text


def test_dify_docs_use_actual_pilot_intent_and_route_keys() -> None:
    texts = [
        (ROOT / "docs/integrations/dify-http-request-node.md").read_text(
            encoding="utf-8"
        ),
        (ROOT / "docs/api/openapi-runtime-examples.md").read_text(encoding="utf-8"),
    ]

    for text in texts:
        assert "it_api_timeout" in text
        assert "it.api_timeout.manual_lookup" in text
        assert "var/pilot/it-helpdesk-pilot.state.secret.json" not in text
        for stale_value in (
            "rel-it-helpdesk-20260625-001",
            "intent-api-timeout",
            "it.helpdesk.api_timeout",
            "intent-db-timeout",
            "it.helpdesk.db_timeout",
        ):
            assert stale_value not in text


def test_openapi_clarify_example_uses_pilot_candidate_set() -> None:
    text = (ROOT / "docs/api/openapi-runtime-examples.md").read_text(encoding="utf-8")

    assert "it_api_timeout" in text
    assert "it.api_timeout.manual_lookup" in text
    assert "it_password_reset" in text
    assert "it.password_reset.self_service" in text
