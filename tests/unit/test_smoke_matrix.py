from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from intent_routing.ops.smoke_matrix import (
    default_dify_smoke_cases,
    render_dify_smoke_matrix_json,
    render_dify_smoke_matrix_markdown,
)
from scripts import run_dify_smoke_matrix as smoke_matrix_script
from scripts.run_dify_smoke_matrix import run_dify_smoke_matrix


def test_default_dify_smoke_cases_cover_decision_and_error_branches() -> None:
    cases = default_dify_smoke_cases()
    by_name = {case.name: case for case in cases}

    assert set(by_name) == {
        "confident",
        "clarify",
        "fallback",
        "off_topic",
        "risk",
        "wrong_api_key_401",
        "wrong_service_403",
        "invalid_body_422",
    }
    assert by_name["confident"].query == "API timeout 500 에러가 납니다"
    assert by_name["confident"].expected_status == 200
    assert by_name["confident"].expected_decision == "confident"
    assert by_name["confident"].expected_route_key == "it.api_timeout.manual_lookup"
    assert by_name["clarify"].expected_decision == "clarify"
    assert by_name["fallback"].expected_decision == "fallback"
    assert by_name["off_topic"].expected_decision == "off_topic"
    assert by_name["risk"].expected_decision == "risk"
    assert by_name["wrong_api_key_401"].expected_status == 401
    assert by_name["wrong_api_key_401"].expected_error_code == "AUTHENTICATION_FAILED"
    assert by_name["wrong_api_key_401"].mutation == "wrong_api_key"
    assert by_name["wrong_service_403"].expected_status == 403
    assert by_name["wrong_service_403"].expected_error_code == "SERVICE_SCOPE_DENIED"
    assert by_name["wrong_service_403"].mutation == "wrong_service"
    assert by_name["invalid_body_422"].expected_status == 422
    assert by_name["invalid_body_422"].expected_error_code == "INVALID_REQUEST"
    assert by_name["invalid_body_422"].mutation == "invalid_body"


def test_rendered_smoke_matrix_reports_redact_secrets_and_queries() -> None:
    payload = {
        "api_key": "irt_secret_value",
        "headers": {"Authorization": "Bearer irt_secret_value"},
        "results": [
            {
                "case": "confident",
                "query": "API timeout 500 에러가 납니다",
                "expected_status": 200,
                "actual_status": 200,
                "expected_decision": "confident",
                "actual_decision": "confident",
                "passed": True,
                "request": {
                    "headers": {"Authorization": "Bearer irt_secret_value"},
                    "json": {"query": "회의실 예약 변경 방법을 알려주세요"},
                },
            }
        ],
    }

    json_report = render_dify_smoke_matrix_json(payload)
    markdown_report = render_dify_smoke_matrix_markdown(payload)

    assert "# Dify Smoke Matrix" in markdown_report
    assert "confident" in markdown_report
    serialized = json_report + markdown_report
    for forbidden in (
        "api_key",
        "Bearer",
        "irt_secret_value",
        "API timeout 500 에러가 납니다",
        "회의실 예약 변경 방법을 알려주세요",
    ):
        assert forbidden not in serialized

    parsed = json.loads(json_report)
    assert parsed["results"][0]["case"] == "confident"
    assert parsed["results"][0]["passed"] is True


def test_run_dify_smoke_matrix_writes_reports_and_returns_failures(
    tmp_path: Path,
) -> None:
    client = _MatrixHttpClient()

    result = run_dify_smoke_matrix(
        base_url="http://example.test",
        state=_state(),
        out_dir=tmp_path,
        http_client=client,
    )

    assert result["passed"] is False
    assert {item["case"] for item in result["results"]} == {
        case.name for case in default_dify_smoke_cases()
    }
    assert result["results"][0]["passed"] is True
    assert result["results"][-1]["case"] == "invalid_body_422"
    assert result["results"][-1]["passed"] is False

    assert len(client.calls) == len(default_dify_smoke_cases())
    assert client.calls[0]["headers"]["Authorization"] == "Bearer irt_secret_value"
    assert client.calls[5]["headers"]["Authorization"] != "Bearer irt_secret_value"
    assert client.calls[6]["headers"]["X-Service-Id"] != "svc-test"
    assert "query" not in client.calls[7]["json"]

    json_report = (tmp_path / "dify-smoke-matrix.json").read_text(encoding="utf-8")
    markdown_report = (tmp_path / "dify-smoke-matrix.md").read_text(encoding="utf-8")
    assert "dify-smoke-matrix.json" in result["json_path"]
    for forbidden in ("irt_secret_value", "Bearer", '"api_key"', "회의실 예약 변경 방법"):
        assert forbidden not in json_report
        assert forbidden not in markdown_report


def test_request_failure_writes_redacted_failure_row_and_continues(
    tmp_path: Path,
) -> None:
    client = _OneFailureHttpClient()

    result = run_dify_smoke_matrix(
        base_url="http://example.test",
        state=_state(),
        out_dir=tmp_path,
        http_client=client,
    )

    assert result["passed"] is False
    assert len(result["results"]) == len(default_dify_smoke_cases())
    failed = result["results"][0]
    assert failed["case"] == "confident"
    assert failed["passed"] is False
    assert failed["actual_status"] is None
    assert failed["error_type"] == "ConnectError"
    assert "REDACTED" in failed["error_message"]
    assert client.calls[-1]["case"] == "invalid_body_422"

    json_report = (tmp_path / "dify-smoke-matrix.json").read_text(encoding="utf-8")
    markdown_report = (tmp_path / "dify-smoke-matrix.md").read_text(encoding="utf-8")
    serialized = json_report + markdown_report
    assert "ConnectError" in json_report
    assert "ConnectError" in markdown_report
    assert "dify-smoke-matrix-confidence" not in serialized
    for forbidden in (
        "irt_secret_value",
        "Bearer",
        "API timeout 500 에러가 납니다",
    ):
        assert forbidden not in serialized


def test_main_exits_nonzero_after_writing_redacted_request_failure_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "pilot.state.secret.json"
    state_path.write_text(json.dumps(_state()), encoding="utf-8")
    out_dir = tmp_path / "evidence"

    def raise_connect_error(_url: str, **_kwargs: Any) -> httpx.Response:
        request = httpx.Request("POST", "http://example.test/v1/intent-route")
        raise httpx.ConnectError(
            "Bearer irt_secret_value refused for API timeout 500 에러가 납니다",
            request=request,
        )

    monkeypatch.setattr("scripts.run_dify_smoke_matrix.httpx.post", raise_connect_error)

    with pytest.raises(SystemExit) as exc_info:
        smoke_matrix_script.main(
            [
                "--base-url",
                "http://example.test",
                "--state",
                str(state_path),
                "--out-dir",
                str(out_dir),
            ]
        )

    assert exc_info.value.code == 1
    assert (out_dir / "dify-smoke-matrix.json").exists()
    assert (out_dir / "dify-smoke-matrix.md").exists()
    captured = capsys.readouterr()
    terminal_output = captured.out + captured.err
    assert "dify-smoke-matrix.json" in terminal_output
    for forbidden in (
        "irt_secret_value",
        "Bearer",
        "API timeout 500 에러가 납니다",
        ".secret.json",
    ):
        assert forbidden not in terminal_output


class _MatrixHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        path: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        self.calls.append({"path": path, "headers": headers, "json": json})
        case_index = len(self.calls) - 1
        case = default_dify_smoke_cases()[case_index]
        if case.name == "wrong_api_key_401":
            return httpx.Response(
                401,
                json={"status": "error", "error": {"code": "AUTHENTICATION_FAILED"}},
            )
        if case.name == "wrong_service_403":
            return httpx.Response(
                403,
                json={"status": "error", "error": {"code": "SERVICE_SCOPE_DENIED"}},
            )
        if case.name == "invalid_body_422":
            return httpx.Response(
                422,
                json={"status": "error", "error": {"code": "SOME_OTHER_CODE"}},
            )
        return httpx.Response(
            200,
            json={
                "decision": case.expected_decision,
                "route_key": case.expected_route_key,
                "trace_id": f"trace-{case.name}",
            },
        )


class _OneFailureHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        path: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        case_index = len(self.calls)
        case = default_dify_smoke_cases()[case_index]
        self.calls.append(
            {"case": case.name, "path": path, "headers": headers, "json": json}
        )
        if case_index == 0:
            request = httpx.Request("POST", "http://example.test/v1/intent-route")
            raise httpx.ConnectError(
                "Bearer irt_secret_value refused for API timeout 500 에러가 납니다",
                request=request,
            )
        if case.name == "wrong_api_key_401":
            return httpx.Response(
                401,
                json={"status": "error", "error": {"code": "AUTHENTICATION_FAILED"}},
            )
        if case.name == "wrong_service_403":
            return httpx.Response(
                403,
                json={"status": "error", "error": {"code": "SERVICE_SCOPE_DENIED"}},
            )
        if case.name == "invalid_body_422":
            return httpx.Response(
                422,
                json={"status": "error", "error": {"code": "INVALID_REQUEST"}},
            )
        return httpx.Response(
            200,
            json={
                "decision": case.expected_decision,
                "route_key": case.expected_route_key,
                "trace_id": f"trace-{case.name}",
            },
        )


def _state() -> dict[str, str]:
    return {
        "api_key": "irt_secret_value",
        "key_id": "key_live_test",
        "app_id": "dify-platform",
        "service_id": "svc-test",
    }
