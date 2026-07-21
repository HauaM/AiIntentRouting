from __future__ import annotations

import base64
import json
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
from intent_routing.security.api_keys import ApiKeyRecord
from scripts.run_pilot_e2e_smoke import run_pilot_e2e_smoke

ROOT = Path(__file__).resolve().parents[2]


def test_pilot_e2e_smoke_writes_quality_gate_index_and_redacted_evidence(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_api_key = "local-admin-token"
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", raw_api_key)
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
    app.state.readiness_session_factory = override_session
    service_id = f"it-helpdesk-e2e-{uuid4().hex}"
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"

    with TestClient(app) as client:
        result = run_pilot_e2e_smoke(
            base_url=str(client.base_url),
            admin_token=raw_api_key,
            service_id=service_id,
            environment="dev",
            state_path=state_path,
            csv_tier="custom",
            csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
            required_preset="balanced",
            out_dir=out_dir,
            http_client=client,
        )

    assert result["service_id"] == service_id
    assert Path(result["readiness_report"]["json_path"]).exists()
    assert Path(result["readiness_report"]["markdown_path"]).exists()
    assert Path(result["threshold_report"]["json_path"]).exists()
    assert Path(result["threshold_report"]["markdown_path"]).exists()
    assert Path(result["json_path"]).exists()
    assert Path(result["markdown_path"]).exists()
    assert result["quality_gate"]["required_preset"] == "balanced"
    assert result["quality_gate"]["passed"] is True

    index_json = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    assert index_json["quality_gate"]["required_preset"] == "balanced"
    assert index_json["quality_gate"]["passed"] is True

    evidence_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path(result["json_path"]),
            Path(result["markdown_path"]),
            Path(result["readiness_report"]["json_path"]),
            Path(result["readiness_report"]["markdown_path"]),
            Path(result["threshold_report"]["json_path"]),
            Path(result["threshold_report"]["markdown_path"]),
        )
    )
    forbidden_fragments = (
        ".secret.json",
        raw_api_key,
        "query_raw",
        "Bearer ",
        "encrypted_dek",
        "ciphertext",
        "API timeout 500 에러가 납니다",
    )
    for fragment in forbidden_fragments:
        assert fragment not in evidence_text
