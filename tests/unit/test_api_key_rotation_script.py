from __future__ import annotations

import json
import stat
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

import scripts.rotate_api_key as rotate_module


def test_rotate_api_key_creates_new_key_smokes_revokes_and_writes_redacted_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_state = tmp_path / "pilot.rotated.state.secret.json"
    report_dir = tmp_path / "reports"
    catalog_path = _write_catalog(tmp_path)
    state_path.write_text(json.dumps(_state()), encoding="utf-8")
    fake_client = _FakeAdminApiClient()
    smoke_calls: list[dict[str, Any]] = []

    def fake_smoke(**kwargs: Any) -> dict[str, Any]:
        smoke_calls.append(dict(kwargs))
        assert kwargs["state"]["api_key"] == "irt_new_secret"
        return {
            "trace_id": "trace-rotation",
            "decision": "confident",
            "route_key": "it.api_timeout.manual_lookup",
        }

    monkeypatch.setattr(rotate_module, "AdminApiClient", fake_client.factory)
    monkeypatch.setattr(rotate_module, "run_runtime_smoke", fake_smoke)

    rotate_module.main(
        [
            "--base-url",
            "http://admin.test",
            "--admin-token",
            "bootstrap-token",
            "--state",
            str(state_path),
            "--catalog",
            str(catalog_path),
            "--out-state",
            str(out_state),
            "--report-dir",
            str(report_dir),
            "--smoke-query",
            "API timeout 500 에러가 납니다",
            "--revoke-old",
        ]
    )

    stdout = capsys.readouterr().out
    assert "irt_new_secret" not in stdout
    assert "irt_old_secret" not in stdout
    assert fake_client.calls == [
        {
            "path": "/admin/v1/api-keys",
            "json": {
                "service_id": "svc-test",
                "environment": "dev",
                "app_id": "dify-platform",
                "allowed_intents": ["it_api_timeout"],
                "allowed_route_keys": ["it.api_timeout.manual_lookup"],
                "expires_in_days": 365,
            },
        },
        {"path": "/admin/v1/api-keys/key_live_old:revoke", "json": None},
    ]
    assert len(smoke_calls) == 1
    assert smoke_calls[0]["expected_decision"] == "confident"
    assert stat.S_IMODE(out_state.stat().st_mode) == 0o600
    rotated_state = json.loads(out_state.read_text(encoding="utf-8"))
    assert rotated_state["key_id"] == "key_live_new"
    assert rotated_state["api_key"] == "irt_new_secret"

    report = json.loads((report_dir / "svc-test-api-key-rotation.json").read_text())
    assert report["old_key_id"] == "key_live_old"
    assert report["new_key_id"] == "key_live_new"
    assert report["new_key_fingerprint"] == "sha256:new:last4"
    assert report["smoke_trace_id"] == "trace-rotation"
    assert report["old_key_revoked"] is True
    serialized_report = json.dumps(report, sort_keys=True)
    assert "irt_new_secret" not in serialized_report
    assert "irt_old_secret" not in serialized_report


def test_rotate_api_key_does_not_revoke_old_key_when_smoke_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    out_state = tmp_path / "pilot.rotated.state.secret.json"
    catalog_path = _write_catalog(tmp_path)
    state_path.write_text(json.dumps(_state()), encoding="utf-8")
    fake_client = _FakeAdminApiClient()

    def fail_smoke(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("expected decision confident, got fallback")

    monkeypatch.setattr(rotate_module, "AdminApiClient", fake_client.factory)
    monkeypatch.setattr(rotate_module, "run_runtime_smoke", fail_smoke)

    with pytest.raises(RuntimeError, match="expected decision confident"):
        rotate_module.rotate_api_key(
            base_url="http://admin.test",
            admin_token="bootstrap-token",
            state_path=state_path,
            catalog_path=catalog_path,
            out_state_path=out_state,
            report_dir=tmp_path / "reports",
            smoke_query="API timeout 500 에러가 납니다",
            revoke_old=True,
        )

    assert fake_client.calls == [
        {
            "path": "/admin/v1/api-keys",
            "json": {
                "service_id": "svc-test",
                "environment": "dev",
                "app_id": "dify-platform",
                "allowed_intents": ["it_api_timeout"],
                "allowed_route_keys": ["it.api_timeout.manual_lookup"],
                "expires_in_days": 365,
            },
        }
    ]
    assert not out_state.exists()


def _write_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "service_id": "svc-test",
                "display_name": "Rotation service",
                "environment": "dev",
                "app_id": "dify-platform",
                "threshold_preset": "balanced",
                "intents": [
                    {
                        "intent_id": "it_api_timeout",
                        "domain": "it",
                        "display_name": "API timeout",
                        "description": "API timeout handling.",
                        "route_key": "it.api_timeout.manual_lookup",
                        "include_keywords": ["api"],
                        "exclude_keywords": [],
                        "positive_examples": ["api timeout"],
                        "negative_examples": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _state() -> dict[str, Any]:
    return {
        "service_id": "svc-test",
        "environment": "dev",
        "app_id": "dify-platform",
        "key_id": "key_live_old",
        "api_key": "irt_old_secret",
        "policy_version": "pol-test",
        "intent_catalog_version": "cat-test",
        "release_version": "rel-test",
    }


class _FakeAdminApiClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def factory(self, **kwargs: Any) -> _FakeAdminApiClient:
        assert kwargs["base_url"] == "http://admin.test"
        assert kwargs["admin_token"] == "bootstrap-token"
        assert kwargs["actor_id"] == "api-key-rotation"
        assert kwargs["actor_roles"] == "system_admin"
        return self

    def __enter__(self) -> _FakeAdminApiClient:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        return None

    def post(self, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append({"path": path, "json": json})
        if path == "/admin/v1/api-keys":
            return {
                "key_id": "key_live_new",
                "api_key": "irt_new_secret",
                "key_fingerprint": "sha256:new:last4",
            }
        if path.endswith(":revoke"):
            return {"key_id": "key_live_old", "status": "revoked"}
        raise AssertionError(f"unexpected post path: {path}")
