from typing import Any

import httpx
import pytest

from scripts.smoke_runtime_dify import run_runtime_smoke


def test_run_runtime_smoke_posts_expected_headers_and_payload() -> None:
    client = _FakeHttpClient(
        response=httpx.Response(
            200,
            json={
                "decision": "confident",
                "intent_id": "it_api_timeout",
                "route_key": "it.api_timeout.manual_lookup",
            },
        )
    )

    result = run_runtime_smoke(
        base_url="http://example.test",
        state=_state(),
        query="API timeout 500 에러가 납니다",
        expected_decision="confident",
        http_client=client,
    )

    assert result["decision"] == "confident"
    assert client.calls == [
        {
            "path": "/v1/intent-route",
            "headers": {
                "Authorization": "Bearer irt_secret_value",
                "X-Key-Id": "key_live_test",
                "X-App-Id": "dify-platform",
                "X-Service-Id": "svc-test",
                "X-Request-Id": "dify-smoke-local-001",
                "Content-Type": "application/json",
            },
            "json": {
                "query": "API timeout 500 에러가 납니다",
                "channel": "chat",
                "user_context": {"workflow_run_id": "dify-smoke-local-001"},
            },
        }
    ]


def test_run_runtime_smoke_raises_on_decision_mismatch_without_secret() -> None:
    client = _FakeHttpClient(response=httpx.Response(200, json={"decision": "fallback"}))

    with pytest.raises(RuntimeError, match="expected decision confident, got fallback"):
        run_runtime_smoke(
            base_url="http://example.test",
            state=_state(),
            query="API timeout 500 에러가 납니다",
            expected_decision="confident",
            http_client=client,
        )

    message = str(
        pytest.raises(
            RuntimeError,
            run_runtime_smoke,
            base_url="http://example.test",
            state=_state(),
            query="API timeout 500 에러가 납니다",
            expected_decision="confident",
            http_client=client,
        ).value
    )
    assert "irt_secret_value" not in message


def test_run_runtime_smoke_raises_clear_error_for_non_json_failure_response() -> None:
    client = _FakeHttpClient(
        response=httpx.Response(
            500,
            text="<html><body>upstream exploded</body></html>",
        )
    )

    with pytest.raises(RuntimeError) as exc_info:
        run_runtime_smoke(
            base_url="http://example.test",
            state=_state(),
            query="API timeout 500 에러가 납니다",
            expected_decision="confident",
            http_client=client,
        )

    message = str(exc_info.value)
    assert "500" in message
    assert "upstream exploded" in message
    assert "irt_secret_value" not in message


def test_run_runtime_smoke_raises_clear_error_for_json_auth_failure() -> None:
    client = _FakeHttpClient(
        response=httpx.Response(
            401,
            json={
                "status": "error",
                "error": {"code": "AUTHENTICATION_FAILED"},
            },
        )
    )

    with pytest.raises(RuntimeError) as exc_info:
        run_runtime_smoke(
            base_url="http://example.test",
            state=_state(),
            query="API timeout 500 에러가 납니다",
            expected_decision="confident",
            http_client=client,
        )

    message = str(exc_info.value)
    assert "401" in message
    assert "AUTHENTICATION_FAILED" in message
    assert "irt_secret_value" not in message


def test_run_runtime_smoke_wraps_network_errors_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_connect_error(url: str, **_kwargs: Any) -> httpx.Response:
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr("scripts.smoke_runtime_dify.httpx.post", raise_connect_error)

    with pytest.raises(RuntimeError) as exc_info:
        run_runtime_smoke(
            base_url="http://example.test",
            state=_state(),
            query="API timeout 500 에러가 납니다",
            expected_decision="confident",
        )

    message = str(exc_info.value)
    assert "http://example.test/v1/intent-route" in message
    assert "connection refused" in message
    assert "irt_secret_value" not in message


class _FakeHttpClient:
    def __init__(self, *, response: httpx.Response) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        path: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        self.calls.append({"path": path, "headers": headers, "json": json})
        return self._response


def _state() -> dict[str, str]:
    return {
        "api_key": "irt_secret_value",
        "key_id": "key_live_test",
        "app_id": "dify-platform",
        "service_id": "svc-test",
    }
