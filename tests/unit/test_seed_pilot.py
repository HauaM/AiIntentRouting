import json
import stat
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest

import scripts.seed_pilot as seed_module


def test_seed_pilot_uses_context_manager_for_real_admin_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_path = _write_catalog(tmp_path, threshold_preset="balanced")
    csv_path = _write_csv(tmp_path)
    fake_api = _FakeAdminApi()

    def fake_admin_client(**_kwargs: Any) -> _FakeAdminApi:
        return fake_api

    monkeypatch.setattr(seed_module, "AdminApiClient", fake_admin_client)

    seed_module.seed_pilot(
        base_url="http://admin.test",
        admin_token="local-admin-token",
        catalog_path=catalog_path,
        csv_path=csv_path,
    )

    assert fake_api.entered is True
    assert fake_api.exited is True


def test_seed_pilot_runs_csv_gate_with_balanced_threshold_for_strict_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = _write_catalog(tmp_path, threshold_preset="strict")
    csv_path = _write_csv(tmp_path)
    http_client = _FakeHttpClient(gate_passed=True)

    state = seed_module.seed_pilot(
        base_url="http://testserver",
        admin_token="local-admin-token",
        catalog_path=catalog_path,
        csv_path=csv_path,
        http_client=http_client,
    )

    test_run_request = next(
        request for request in http_client.requests if request["path"].endswith("/test-runs")
    )
    assert "threshold_preset" not in test_run_request["json"]
    assert state["test_runs"]["balanced"]["gate_passed"] is True
    assert "strict" not in state["test_runs"]


def test_seed_pilot_creates_catalog_version_with_description(
    tmp_path: Path,
) -> None:
    catalog_path = _write_catalog(tmp_path, threshold_preset="balanced")
    csv_path = _write_csv(tmp_path)
    http_client = _FakeHttpClient(gate_passed=True)

    seed_module.seed_pilot(
        base_url="http://testserver",
        admin_token="local-admin-token",
        catalog_path=catalog_path,
        csv_path=csv_path,
        http_client=http_client,
    )

    catalog_version_request = next(
        request
        for request in http_client.requests
        if request["path"].endswith("/catalog-versions")
    )
    assert catalog_version_request["json"] == {
        "description": "Pilot catalog version seed"
    }


def test_seed_pilot_fails_when_balanced_gate_fails_for_strict_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = _write_catalog(tmp_path, threshold_preset="strict")
    csv_path = _write_csv(tmp_path)
    http_client = _FakeHttpClient(gate_passed=False)

    with pytest.raises(RuntimeError, match="Pilot CSV gate failed for balanced threshold"):
        seed_module.seed_pilot(
            base_url="http://testserver",
            admin_token="local-admin-token",
            catalog_path=catalog_path,
            csv_path=csv_path,
            http_client=http_client,
        )


def test_main_writes_secret_state_file_without_printing_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    catalog_path = _write_catalog(tmp_path, threshold_preset="balanced")
    csv_path = _write_csv(tmp_path)
    state_path = tmp_path / "secret-state" / "pilot.state.secret.json"

    def fake_seed_pilot(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["catalog_path"] == catalog_path
        assert kwargs["csv_path"] == csv_path
        assert kwargs["service_id"] == "svc-cli"
        assert kwargs["environment"] == "dev"
        return _state(service_id="svc-cli", api_key="irt_secret_value")

    monkeypatch.setattr(seed_module, "seed_pilot", fake_seed_pilot)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seed_pilot.py",
            "--base-url",
            "http://admin.test",
            "--admin-token",
            "local-admin-token",
            "--catalog",
            str(catalog_path),
            "--csv",
            str(csv_path),
            "--service-id",
            "svc-cli",
            "--environment",
            "dev",
            "--state-path",
            str(state_path),
        ],
    )

    seed_module.main()

    stdout = capsys.readouterr().out
    assert "irt_secret_value" not in stdout
    assert "key_live_test" in stdout
    assert state_path.parent.is_dir()
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert json.loads(state_path.read_text(encoding="utf-8"))["api_key"] == "irt_secret_value"


def test_write_state_replaces_symlink_without_touching_target(tmp_path: Path) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    target_path = tmp_path / "target.json"
    target_path.write_text("do not overwrite", encoding="utf-8")
    state_path.symlink_to(target_path)

    seed_module._write_state(state_path, _state(api_key="irt_secret_value"))

    assert not state_path.is_symlink()
    assert target_path.read_text(encoding="utf-8") == "do not overwrite"
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert json.loads(state_path.read_text(encoding="utf-8"))["api_key"] == "irt_secret_value"


class _FakeAdminApi:
    def __init__(self, *, gate_passed: bool = True) -> None:
        self.gate_passed = gate_passed
        self.entered = False
        self.exited = False

    def __enter__(self) -> "_FakeAdminApi":
        self.entered = True
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        self.exited = True

    def post(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        return _admin_response(path, json=json, gate_passed=self.gate_passed)

    def patch(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        return _admin_response(path, json=json, gate_passed=self.gate_passed)


class _FakeHttpClient:
    def __init__(self, *, gate_passed: bool) -> None:
        self.gate_passed = gate_passed
        self.requests: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        **kwargs: Any,
    ) -> httpx.Response:
        self.requests.append(
            {
                "method": method,
                "path": path,
                "headers": headers,
                "json": kwargs.get("json"),
            }
        )
        return httpx.Response(
            201,
            json=_admin_response(path, json=kwargs.get("json"), gate_passed=self.gate_passed),
        )


def _admin_response(
    path: str,
    *,
    json: Mapping[str, Any] | None,
    gate_passed: bool,
) -> dict[str, Any]:
    if path == "/admin/v1/api-keys":
        return {
            "key_id": "key_live_test",
            "api_key": "irt_test_secret",
        }
    if path.endswith("/policy-versions"):
        return {"policy_version": "pol-svc-test-001"}
    if path.endswith("/catalog-versions"):
        return {"intent_catalog_version": "cat-svc-test-001"}
    if path.endswith("/test-runs"):
        return {
            "test_run_id": "tr-svc-test-001",
            "gate_passed": gate_passed,
            "threshold_preset": "balanced",
        }
    if path.endswith("/releases"):
        return {"release_version": "rel-svc-test-001"}
    if path.endswith(":activate"):
        return {"release_version": "rel-svc-test-001"}
    if path.endswith("/examples"):
        return {"example_id": "example-test"}
    return {}


def _write_catalog(tmp_path: Path, *, threshold_preset: str) -> Path:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "service_id": "svc-test",
                "display_name": "Seed test service",
                "environment": "dev",
                "app_id": "app-test",
                "threshold_preset": threshold_preset,
                "off_topic_keywords": ["weather"],
                "off_topic_message": "Outside service scope.",
                "intents": [
                    {
                        "intent_id": "intent_test",
                        "domain": "it",
                        "display_name": "Intent test",
                        "description": "Test pilot seeding.",
                        "route_key": "it.seed.test",
                        "include_keywords": ["seed"],
                        "exclude_keywords": [],
                        "positive_examples": ["seed example"],
                        "negative_examples": ["other example"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return catalog_path


def _write_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "cases.csv"
    csv_path.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "P001,seed example,intent_test,positive,seed test\n",
        encoding="utf-8",
    )
    return csv_path


def _state(
    *,
    service_id: str = "svc-test",
    api_key: str = "irt_test_secret",
) -> dict[str, Any]:
    return {
        "service_id": service_id,
        "environment": "dev",
        "app_id": "app-test",
        "key_id": "key_live_test",
        "api_key": api_key,
        "policy_version": "pol-svc-test-001",
        "intent_catalog_version": "cat-svc-test-001",
        "test_runs": {"balanced": {"gate_passed": True}},
        "release_version": "rel-svc-test-001",
    }
