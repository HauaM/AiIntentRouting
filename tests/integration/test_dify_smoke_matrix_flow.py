from __future__ import annotations

import base64
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.api.dependencies import get_api_key_lookup
from intent_routing.api.runtime import get_runtime_session
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.ops.smoke_matrix import default_dify_smoke_cases
from intent_routing.security.api_keys import ApiKeyRecord
from scripts.run_dify_smoke_matrix import run_dify_smoke_matrix
from scripts.seed_pilot import seed_pilot

ROOT = Path(__file__).resolve().parents[2]


def test_dify_smoke_matrix_flow_writes_redacted_branch_evidence(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", base64.b64encode(b"0" * 32).decode("ascii"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "dev")
    clear_embedding_provider_cache()
    app = create_app()
    runtime_module = import_module("intent_routing.api.runtime")

    def override_session() -> Iterator[Session]:
        yield db_session

    def runtime_lookup(key_id: str) -> ApiKeyRecord | None:
        model = IntentRoutingRepository(db_session).get_api_key_by_id(key_id)
        if model is None:
            return None
        return ApiKeyRecord(
            key_id=model.key_id,
            key_hash=model.key_hash,
            key_fingerprint=model.key_fingerprint,
            environment=model.environment,
            app_id=model.app_id,
            service_id=model.service_id,
            allowed_intents=list(model.allowed_intents or []),
            allowed_route_keys=list(model.allowed_route_keys or []),
            status=model.status,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[get_runtime_session] = override_session
    app.dependency_overrides[get_api_key_lookup] = lambda: runtime_lookup
    app.dependency_overrides[runtime_module.get_runtime_session] = override_session
    service_id = f"it-helpdesk-dify-matrix-{uuid4().hex}"
    out_dir = tmp_path / "dify"

    with TestClient(app) as client:
        state = seed_pilot(
            base_url=str(client.base_url),
            admin_token="local-admin-token",
            catalog_path=ROOT / "docs/pilot/it-helpdesk-pilot-catalog.json",
            csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
            service_id=service_id,
            environment="dev",
            http_client=client,
        )
        result = run_dify_smoke_matrix(
            base_url=str(client.base_url),
            state=state,
            out_dir=out_dir,
            http_client=client,
        )

    assert result["passed"] is True
    results_by_case = {item["case"]: item for item in result["results"]}
    assert set(results_by_case) == {case.name for case in default_dify_smoke_cases()}
    for case in default_dify_smoke_cases():
        item = results_by_case[case.name]
        assert item["actual_status"] == case.expected_status
        if case.expected_decision is not None:
            assert item["actual_decision"] == case.expected_decision
        if case.expected_error_code is not None:
            assert item["actual_error_code"] == case.expected_error_code
    assert results_by_case["wrong_api_key_401"]["actual_status"] == 401
    assert results_by_case["wrong_service_403"]["actual_status"] == 403
    assert results_by_case["invalid_body_422"]["actual_status"] == 422

    json_report = (out_dir / "dify-smoke-matrix.json").read_text(encoding="utf-8")
    markdown_report = (out_dir / "dify-smoke-matrix.md").read_text(encoding="utf-8")
    assert state["api_key"] not in json_report
    assert state["api_key"] not in markdown_report
    assert "Bearer" not in json_report
    assert "Bearer" not in markdown_report
