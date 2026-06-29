from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.api.dependencies import get_api_key_lookup, get_runtime_environment
from intent_routing.api.runtime import get_runtime_session
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.security.api_keys import ApiKeyRecord
from scripts import run_pilot_rehearsal as rehearsal_script
from scripts.run_pilot_rehearsal import run_pilot_rehearsal

ROOT = Path(__file__).resolve().parents[2]


def test_local_pilot_rehearsal_runs_smokes_ops_export_and_secret_scan(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_api_key = "local-admin-token"
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", raw_api_key)
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", base64.b64encode(b"0" * 32).decode("ascii"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "dev")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
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
    app.dependency_overrides[get_runtime_environment] = lambda: "dev"
    app.dependency_overrides[runtime_module.get_runtime_session] = override_session
    app.state.readiness_session_factory = override_session
    service_id = f"it-helpdesk-rehearsal-{uuid4().hex}"
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"
    ops_requests: list[httpx.Request] = []

    def ops_handler(request: httpx.Request) -> httpx.Response:
        ops_requests.append(request)
        if request.url.path == "/readyz":
            return httpx.Response(200, json={"status": "ready"})
        assert request.headers["X-Admin-Token"] == raw_api_key
        assert request.headers["X-Service-Scope"] == service_id
        if request.url.path == f"/admin/v1/services/{service_id}/releases/active":
            return httpx.Response(
                200,
                json={
                    "release_version": "rel-rehearsal-001",
                    "service_id": service_id,
                    "environment": "dev",
                    "policy_version": "pol-rehearsal-001",
                    "intent_catalog_version": "cat-rehearsal-001",
                    "model_version": "emb-fake-v1",
                    "vector_index_version": "vec-rehearsal-001",
                    "test_dataset_version": "tds-rehearsal-001",
                    "test_run_id": "trn-rehearsal-001",
                    "pass_rate": 1.0,
                    "risk_pass_rate": 1.0,
                    "active": True,
                    "released_by": "pilot-rehearsal",
                    "released_at": "2026-06-29T00:00:00Z",
                    "rollback_target": None,
                },
            )
        if request.url.path == f"/admin/v1/services/{service_id}/runtime-metrics":
            return httpx.Response(
                200,
                json={
                    "service_id": service_id,
                    "window_hours": 24,
                    "request_count": 4,
                    "decision_counts": {"confident": 1, "unauthorized": 3},
                    "error_counts": {},
                    "latency_ms": {"p50": 12, "p95": 18, "max": 18},
                    "top_route_keys": [
                        {"route_key": "it.api_timeout.manual_lookup", "count": 1}
                    ],
                    "raw_query_retention": {
                        "encrypted_count": 0,
                        "incomplete_count": 0,
                        "redacted_count": 4,
                    },
                },
            )
        if (
            request.url.path
            == f"/admin/v1/services/{service_id}/security/raw-text-key-summary"
        ):
            return httpx.Response(
                200,
                json={
                    "service_id": service_id,
                    "active_key_id": "pilot-kek-20260628-002",
                    "intent_examples": [],
                    "runtime_logs": [{"key_id": None, "count": 4, "state": "redacted"}],
                },
            )
        if request.url.path == f"/admin/v1/services/{service_id}/audit-logs":
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"error": "unexpected path"})

    with TestClient(app) as client:
        result = run_pilot_rehearsal(
            mode="local",
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
            ops_transport=httpx.MockTransport(ops_handler),
        )

    assert Path(result["json_path"]).name == "pilot-rehearsal-manifest.json"
    assert Path(result["markdown_path"]).name == "pilot-rehearsal-manifest.md"
    assert Path(result["json_path"]).exists()
    assert Path(result["markdown_path"]).exists()
    assert state_path.exists()
    assert not (out_dir / state_path.name).exists()
    assert [request.url.path for request in ops_requests] == [
        "/readyz",
        f"/admin/v1/services/{service_id}/releases/active",
        f"/admin/v1/services/{service_id}/runtime-metrics",
        f"/admin/v1/services/{service_id}/security/raw-text-key-summary",
        f"/admin/v1/services/{service_id}/audit-logs",
        f"/admin/v1/services/{service_id}/audit-logs",
        f"/admin/v1/services/{service_id}/audit-logs",
        f"/admin/v1/services/{service_id}/audit-logs",
    ]

    manifest = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    assert manifest["service_id"] == service_id
    assert manifest["mode"] == "local"
    assert manifest["final_status"] == "PASS"
    assert manifest["secret_scan"]["passed"] is True
    steps = {step["name"]: step for step in manifest["steps"]}
    assert steps["bge-package"]["status"] == "skip"
    assert steps["bge-package"]["required"] is False
    assert steps["bge-benchmark"]["status"] == "skip"
    assert steps["bge-benchmark"]["required"] is False
    assert steps["csv-baseline"]["status"] == "skip"
    assert steps["csv-baseline"]["required"] is False
    for step_name in ("pilot-e2e-smoke", "dify-smoke-matrix", "ops-evidence-export"):
        assert steps[step_name]["status"] == "pass"
        assert steps[step_name]["required"] is True

    evidence_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in out_dir.rglob("*")
        if path.is_file()
    )
    forbidden_fragments = (
        ".secret.json",
        raw_api_key,
        "Bearer ",
        "query_raw",
        "encrypted_dek",
        "ciphertext",
        "API timeout 500 에러가 납니다",
    )
    for fragment in forbidden_fragments:
        assert fragment not in evidence_text


def test_pilot_rehearsal_writes_manifest_when_e2e_fails_before_state_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"

    def fail_before_state_file(**_: object) -> dict[str, object]:
        raise RuntimeError("seed failed before state write")

    def fail_if_called(**_: object) -> dict[str, object]:
        raise AssertionError("dependent step should not run after e2e failure")

    monkeypatch.setattr(rehearsal_script, "run_pilot_e2e_smoke", fail_before_state_file)
    monkeypatch.setattr(rehearsal_script, "run_dify_smoke_matrix", fail_if_called)
    monkeypatch.setattr(rehearsal_script, "run_ops_evidence_export", fail_if_called)

    with pytest.raises(SystemExit) as exc_info:
        run_pilot_rehearsal(
            mode="local",
            base_url="http://testserver",
            admin_token="local-admin-token",
            service_id="svc-e2e-fails-before-state",
            environment="dev",
            state_path=state_path,
            csv_tier="standard",
            required_preset="balanced",
            out_dir=out_dir,
        )

    assert exc_info.value.code == 1
    manifest_path = out_dir / "pilot-rehearsal-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    steps = {step["name"]: step for step in manifest["steps"]}
    assert steps["pilot-e2e-smoke"]["status"] == "fail"
    assert "FileNotFoundError" not in steps["pilot-e2e-smoke"]["error_message"]
