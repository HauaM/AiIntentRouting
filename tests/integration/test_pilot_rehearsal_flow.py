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
from intent_routing.api.dependencies import get_api_key_lookup
from intent_routing.api.runtime import get_runtime_session
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.ops.csv_baseline import freeze_baseline
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


def test_pilot_rehearsal_runs_csv_baseline_when_baseline_is_provided(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"
    csv_path = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"
    threshold_report = _threshold_report(result="PASS")
    baseline = freeze_baseline(threshold_report, csv_path, "balanced")
    baseline["baseline_id"] = "it-helpdesk-pilot-standard-20260629"
    baseline["policy"]["baseline_id"] = "it-helpdesk-pilot-standard-20260629"
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline) + "\n", encoding="utf-8")

    def e2e_stub(*, state_path: Path, out_dir: Path, **_: object) -> dict[str, object]:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "api_key": "redacted-test-key",
                    "key_id": "key-id",
                    "app_id": "app-id",
                    "service_id": "svc-csv-baseline",
                }
            ),
            encoding="utf-8",
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        threshold_json = out_dir / "svc-csv-baseline-threshold-comparison.json"
        threshold_md = out_dir / "svc-csv-baseline-threshold-comparison.md"
        threshold_json.write_text(json.dumps(threshold_report) + "\n", encoding="utf-8")
        threshold_md.write_text("# Threshold\n", encoding="utf-8")
        return {
            **_write_stub_evidence(out_dir, "pilot-e2e-smoke-index", passed=True),
            "threshold_report": {
                "json_path": str(threshold_json),
                "markdown_path": str(threshold_md),
            },
            "quality_gate": {"passed": True},
        }

    def dify_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return _write_stub_evidence(out_dir, "dify-smoke-matrix", passed=True)

    def ops_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return {"payload": {}, **_write_stub_evidence(out_dir, "ops-evidence", passed=True)}

    monkeypatch.setattr(rehearsal_script, "run_pilot_e2e_smoke", e2e_stub)
    monkeypatch.setattr(rehearsal_script, "run_dify_smoke_matrix", dify_stub)
    monkeypatch.setattr(rehearsal_script, "run_ops_evidence_export", ops_stub)

    result = run_pilot_rehearsal(
        mode="local",
        base_url="http://testserver",
        admin_token="local-admin-token",
        service_id="svc-csv-baseline",
        environment="dev",
        state_path=state_path,
        csv_tier="standard",
        required_preset="balanced",
        baseline_path=baseline_path,
        out_dir=out_dir,
    )

    manifest = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    steps = {step["name"]: step for step in manifest["steps"]}
    assert steps["csv-baseline"]["status"] == "pass"
    assert steps["csv-baseline"]["required"] is True
    assert (out_dir / "csv-baseline" / "csv-baseline-comparison.json").exists()


def test_pilot_rehearsal_preserves_csv_baseline_failure_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"
    csv_path = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"
    changed_csv = tmp_path / "changed.csv"
    changed_csv.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,changed,it_api_timeout,positive,memo\n",
        encoding="utf-8",
    )
    threshold_report = _threshold_report(result="PASS")
    baseline = freeze_baseline(threshold_report, csv_path, "balanced")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline) + "\n", encoding="utf-8")

    def e2e_stub(*, state_path: Path, out_dir: Path, **_: object) -> dict[str, object]:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "api_key": "redacted-test-key",
                    "key_id": "key-id",
                    "app_id": "app-id",
                    "service_id": "svc-csv-baseline",
                }
            ),
            encoding="utf-8",
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        threshold_json = out_dir / "svc-csv-baseline-threshold-comparison.json"
        threshold_md = out_dir / "svc-csv-baseline-threshold-comparison.md"
        threshold_json.write_text(json.dumps(threshold_report) + "\n", encoding="utf-8")
        threshold_md.write_text("# Threshold\n", encoding="utf-8")
        return {
            **_write_stub_evidence(out_dir, "pilot-e2e-smoke-index", passed=True),
            "threshold_report": {
                "json_path": str(threshold_json),
                "markdown_path": str(threshold_md),
            },
            "quality_gate": {"passed": True},
        }

    def dify_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return _write_stub_evidence(out_dir, "dify-smoke-matrix", passed=True)

    def ops_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return {"payload": {}, **_write_stub_evidence(out_dir, "ops-evidence", passed=True)}

    monkeypatch.setattr(rehearsal_script, "run_pilot_e2e_smoke", e2e_stub)
    monkeypatch.setattr(rehearsal_script, "run_dify_smoke_matrix", dify_stub)
    monkeypatch.setattr(rehearsal_script, "run_ops_evidence_export", ops_stub)

    with pytest.raises(SystemExit) as exc_info:
        run_pilot_rehearsal(
            mode="local",
            base_url="http://testserver",
            admin_token="local-admin-token",
            service_id="svc-csv-baseline",
            environment="dev",
            state_path=state_path,
            csv_tier="custom",
            csv_path=changed_csv,
            required_preset="balanced",
            baseline_path=baseline_path,
            out_dir=out_dir,
        )

    assert exc_info.value.code == 1
    manifest = json.loads(
        (out_dir / "pilot-rehearsal-manifest.json").read_text(encoding="utf-8")
    )
    csv_baseline_step = {step["name"]: step for step in manifest["steps"]}[
        "csv-baseline"
    ]
    assert csv_baseline_step["status"] == "fail"
    assert csv_baseline_step["error_message"] == "csv_sha256 mismatch"


def test_pilot_rehearsal_writes_dify_metadata_and_scans_ui_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"
    dify_ui_evidence_path = tmp_path / "dify-ui-export.md"
    dify_ui_evidence_path.write_text(
        "# Dify UI Export\n\nAll visible secret fields are REDACTED.\n",
        encoding="utf-8",
    )

    def e2e_stub(*, state_path: Path, out_dir: Path, **_: object) -> dict[str, object]:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "api_key": "redacted-test-key",
                    "key_id": "key-id",
                    "app_id": "app-id",
                    "service_id": "svc-dify-metadata",
                }
            ),
            encoding="utf-8",
        )
        return {
            **_write_stub_evidence(out_dir, "pilot-e2e-smoke-index", passed=True),
            "quality_gate": {"passed": True},
        }

    def dify_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return _write_stub_evidence(out_dir, "dify-smoke-matrix", passed=True)

    def ops_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return {"payload": {}, **_write_stub_evidence(out_dir, "ops-evidence", passed=True)}

    monkeypatch.setattr(rehearsal_script, "run_pilot_e2e_smoke", e2e_stub)
    monkeypatch.setattr(rehearsal_script, "run_dify_smoke_matrix", dify_stub)
    monkeypatch.setattr(rehearsal_script, "run_ops_evidence_export", ops_stub)

    result = run_pilot_rehearsal(
        mode="local",
        base_url="http://testserver",
        admin_token="local-admin-token",
        service_id="svc-dify-metadata",
        environment="dev",
        state_path=state_path,
        csv_tier="standard",
        required_preset="balanced",
        out_dir=out_dir,
        dify_workflow_version="workflow-export-20260629-001",
        dify_ui_evidence_path=dify_ui_evidence_path,
    )

    manifest = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    assert manifest["dify_workflow_version_identifier"] == (
        "workflow-export-20260629-001"
    )
    assert manifest["dify_ui_evidence_path"] == str(dify_ui_evidence_path)
    assert manifest["secret_scan"]["passed"] is True
    markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "Dify workflow version identifier" in markdown
    assert str(dify_ui_evidence_path) in markdown
    assert "All visible secret fields are REDACTED" not in markdown


def test_pilot_rehearsal_fails_when_dify_ui_evidence_path_is_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_pilot_rehearsal(
            mode="local",
            base_url="http://testserver",
            admin_token="local-admin-token",
            service_id="svc-missing-dify-evidence",
            environment="dev",
            state_path=tmp_path / "pilot.state.secret.json",
            csv_tier="standard",
            required_preset="balanced",
            out_dir=tmp_path / "evidence",
            dify_ui_evidence_path=tmp_path / "missing-dify-export.png",
        )

    assert exc_info.value.code == 2


def test_closed_network_bge_checksum_mismatch_keeps_package_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_dir = tmp_path / "evidence"
    actual_sha = "1" * 64
    expected_sha = "0" * 64

    def package_mismatch(*, out_dir: Path, **_: object) -> dict[str, object]:
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "bge-m3-package.json"
        markdown_path = out_dir / "bge-m3-package.md"
        json_path.write_text('{"sha256": "' + actual_sha + '"}\n', encoding="utf-8")
        markdown_path.write_text("# BGE-M3 Package\n", encoding="utf-8")
        return {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "sha256": actual_sha,
        }

    def benchmark_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return _write_stub_evidence(out_dir, "bge-m3-benchmark", passed=True)

    def e2e_stub(*, state_path: Path, out_dir: Path, **_: object) -> dict[str, object]:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "api_key": "redacted-test-key",
                    "key_id": "key-id",
                    "app_id": "app-id",
                    "service_id": "svc-bge-mismatch",
                }
            ),
            encoding="utf-8",
        )
        return {
            **_write_stub_evidence(out_dir, "pilot-e2e-smoke-index", passed=True),
            "quality_gate": {"passed": True},
        }

    def dify_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return _write_stub_evidence(out_dir, "dify-smoke-matrix", passed=True)

    def ops_stub(*, out_dir: Path, **_: object) -> dict[str, object]:
        return {"payload": {}, **_write_stub_evidence(out_dir, "ops-evidence", passed=True)}

    monkeypatch.setattr(rehearsal_script, "verify_bge_m3_package", package_mismatch)
    monkeypatch.setattr(rehearsal_script, "benchmark_bge_m3", benchmark_stub)
    monkeypatch.setattr(rehearsal_script, "run_pilot_e2e_smoke", e2e_stub)
    monkeypatch.setattr(rehearsal_script, "run_dify_smoke_matrix", dify_stub)
    monkeypatch.setattr(rehearsal_script, "run_ops_evidence_export", ops_stub)

    with pytest.raises(SystemExit) as exc_info:
        run_pilot_rehearsal(
            mode="closed-network",
            base_url="http://testserver",
            admin_token="local-admin-token",
            service_id="svc-bge-mismatch",
            environment="pilot",
            state_path=state_path,
            out_dir=out_dir,
            required_preset="balanced",
            bge_model_path=tmp_path / "models" / "bge-m3",
            bge_expected_sha256=expected_sha,
            run_bge_benchmark=True,
        )

    assert exc_info.value.code == 1
    manifest_path = out_dir / "pilot-rehearsal-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bge_step = {step["name"]: step for step in manifest["steps"]}["bge-package"]
    assert bge_step["status"] == "fail"
    evidence_paths = {Path(item["path"]).name for item in bge_step["evidence_files"]}
    assert evidence_paths == {"bge-m3-package.json", "bge-m3-package.md"}


def _write_stub_evidence(out_dir: Path, stem: str, *, passed: bool) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.json"
    markdown_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps({"passed": passed}) + "\n", encoding="utf-8")
    markdown_path.write_text(f"# {stem}\n", encoding="utf-8")
    return {
        "passed": passed,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def _threshold_report(*, result: str) -> dict[str, object]:
    return {
        "service_id": "svc-csv-baseline",
        "policy_version": "pol-test",
        "intent_catalog_version": "cat-test",
        "runs": {
            "balanced": {
                "pass_rate": 1.0,
                "risk_pass_rate": 1.0,
                "gate_passed": result == "PASS",
            }
        },
        "results": {
            "balanced": [
                {
                    "case_id": "C001",
                    "case_type": "positive",
                    "expected_decision": "confident",
                    "expected_intent": "it_api_timeout",
                    "actual_decision": "confident",
                    "actual_intent": "it_api_timeout",
                    "actual_route_key": "it.api_timeout.manual_lookup",
                    "result": result,
                }
            ]
        },
    }
