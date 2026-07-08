from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/api/admin-phase2-contracts.md"


def _contract_text() -> str:
    assert CONTRACT.exists()
    return CONTRACT.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    start_marker = f"## {heading}"
    start = text.index(start_marker)
    next_heading = text.find("\n## ", start + len(start_marker))
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def test_admin_phase2_contract_docs_define_resource_action_and_approval_model() -> None:
    text = _contract_text()

    for resource_type in (
        "`intent`",
        "`example`",
        "`release`",
        "`runtime_log`",
        "`raw_query`",
        "`export`",
    ):
        assert resource_type in text

    for action_name in (
        "`request`",
        "`approve`",
        "`reject`",
        "`activate`",
        "`rollback`",
        "`decrypt`",
        "`export`",
    ):
        assert action_name in text

    for invariant in (
        "author cannot approve own request",
        "two-person raw query approval",
        "audit event required for every state transition",
    ):
        assert invariant in text


def test_admin_phase2_contract_docs_use_exact_role_literals() -> None:
    text = _contract_text()

    for role_name in (
        "`service_developer`",
        "`service_owner`",
        "`service_operator`",
        "`auditor`",
        "`system_admin`",
    ):
        assert role_name in text

    for prose_role_name in (
        "Service developer",
        "Service owner",
        "Service operator",
        "Auditor",
    ):
        assert prose_role_name not in text


def test_admin_phase2_contract_docs_define_exact_endpoint_set() -> None:
    text = _contract_text()
    expected_endpoints = {
        "POST /admin/v1/services/{service_id}/publish-requests",
        "POST /admin/v1/services/{service_id}/publish-requests/{request_id}:approve",
        "POST /admin/v1/services/{service_id}/publish-requests/{request_id}:reject",
        "POST /admin/v1/services/{service_id}/runtime-logs/{trace_id}/raw-query-view-requests",
        "POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:approve",
        "POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:reject",
        "POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:issue-token",
        "GET /admin/v1/services/{service_id}/releases/{release_version}/diff",
        "POST /admin/v1/services/{service_id}/exports",
    }

    documented_endpoints = {
        line.strip().removeprefix("## ")
        for line in text.splitlines()
        if line.startswith(("## GET /admin/v1/", "## POST /admin/v1/"))
    }

    assert documented_endpoints == expected_endpoints


def test_admin_phase2_contract_docs_define_raw_query_token_consumption() -> None:
    text = _contract_text()

    for phrase in (
        "POST /admin/v1/services/{service_id}/runtime-logs/{trace_id}:decrypt-raw-query",
        "`raw_query_view_token`",
        "raw_query.viewed",
        "token hash/expiry/request/trace/service validation",
        "denies direct decrypt without an approved token in Phase 2",
    ):
        assert phrase in text


def test_admin_phase2_contract_docs_publish_permissions_are_resource_specific() -> None:
    text = _contract_text()
    approve_section = _section(
        text,
        "POST /admin/v1/services/{service_id}/publish-requests/{request_id}:approve",
    )
    reject_section = _section(
        text,
        "POST /admin/v1/services/{service_id}/publish-requests/{request_id}:reject",
    )

    assert "{resource_type}:approve" in approve_section
    assert "{resource_type}:reject" in reject_section
    assert "intent/example/release approvals map to the requested resource type" in text
    assert "`release:approve`" not in approve_section
    assert "`release:reject`" not in reject_section


def test_admin_phase2_contract_docs_exports_are_synchronous() -> None:
    text = _contract_text()
    export_section = _section(text, "POST /admin/v1/services/{service_id}/exports")
    documented_endpoints = {
        line.strip().removeprefix("## ")
        for line in text.splitlines()
        if line.startswith(("## GET /admin/v1/", "## POST /admin/v1/"))
    }

    assert "synchronous" in export_section
    assert "No async polling/download endpoint" in export_section
    assert "exists in this first contract" in export_section
    assert "masked export content" in export_section
    assert "`download_url`" not in export_section
    assert "polling" not in " ".join(documented_endpoints)
    assert not any("/exports/" in endpoint for endpoint in documented_endpoints)


def test_admin_phase2_contract_docs_define_security_rules() -> None:
    text = _contract_text()

    for rule in (
        "masked-only export",
        "no API key secrets",
        "no raw query text in exports/evidence/logs",
        "no encrypted DEKs/ciphertext/KEK material",
    ):
        assert rule in text
