from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_workflow_candidate_contract_docs_exist_and_name_required_endpoints() -> None:
    adr = ROOT / "docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md"
    contract = ROOT / "docs/api/admin-workflow-candidate-contracts.md"
    pattern = ROOT / "docs/AdminUI_Handbook/v04/PATTERN_KIT.md"

    assert adr.exists()
    assert contract.exists()

    adr_text = adr.read_text(encoding="utf-8")
    contract_text = contract.read_text(encoding="utf-8")
    pattern_text = pattern.read_text(encoding="utf-8")

    for phrase in [
        "Status",
        "Decision",
        "Alternatives Considered",
        "Consequences",
        "service-scoped candidate endpoints",
    ]:
        assert phrase in adr_text

    for endpoint in [
        "GET /admin/v1/services/{service_id}/policy-versions",
        "GET /admin/v1/services/{service_id}/catalog-versions",
        "GET /admin/v1/services/{service_id}/test-runs",
        "GET /admin/v1/services/{service_id}/release-candidates",
        "GET /admin/v1/services/{service_id}/intent-route-candidates",
        "GET /admin/v1/api-keys",
    ]:
        assert endpoint in contract_text

    for required_field in ["threshold_value", "key_fingerprint", "expires_at"]:
        assert required_field in contract_text
    assert "revoked_by" not in contract_text

    for phrase in [
        "Workflow candidate selectors",
        "Manual internal ID entry is transitional",
        "Phase 2 governed workflows remain disabled",
    ]:
        assert phrase in pattern_text
