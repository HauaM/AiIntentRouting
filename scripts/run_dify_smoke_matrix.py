from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from json import JSONDecodeError
from pathlib import Path
from typing import Any, cast

import httpx

from intent_routing.ops.smoke_matrix import (
    DifySmokeCase,
    default_dify_smoke_cases,
    render_dify_smoke_matrix_json,
    render_dify_smoke_matrix_markdown,
)


def run_dify_smoke_matrix(
    *,
    base_url: str,
    state: Mapping[str, Any],
    out_dir: Path,
    timeout_seconds: float = 8.0,
    http_client: Any | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [
        _run_case(
            case=case,
            base_url=base_url,
            state=state,
            timeout_seconds=timeout_seconds,
            http_client=http_client,
        )
        for case in default_dify_smoke_cases()
    ]
    payload: dict[str, Any] = {
        "base_url": base_url,
        "passed": all(bool(result["passed"]) for result in results),
        "results": results,
    }
    json_path = out_dir / "dify-smoke-matrix.json"
    markdown_path = out_dir / "dify-smoke-matrix.md"
    json_path.write_text(render_dify_smoke_matrix_json(payload), encoding="utf-8")
    markdown_path.write_text(render_dify_smoke_matrix_markdown(payload), encoding="utf-8")
    return {
        **payload,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    state = json.loads(args.state.read_text(encoding="utf-8"))
    result = run_dify_smoke_matrix(
        base_url=args.base_url,
        state=state,
        out_dir=args.out_dir,
        timeout_seconds=args.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "json_path": result["json_path"],
                "markdown_path": result["markdown_path"],
                "passed": result["passed"],
            },
            ensure_ascii=False,
        )
    )
    if result["passed"] is False:
        raise SystemExit(1)


def _run_case(
    *,
    case: DifySmokeCase,
    base_url: str,
    state: Mapping[str, Any],
    timeout_seconds: float,
    http_client: Any | None,
) -> dict[str, Any]:
    request_id = f"dify-smoke-matrix-{case.name}"
    headers = _headers_for_case(case=case, state=state, request_id=request_id)
    body = _body_for_case(case=case, request_id=request_id)
    response = _post(
        base_url=base_url,
        headers=headers,
        body=body,
        timeout_seconds=timeout_seconds,
        http_client=http_client,
        state=state,
    )
    response_body = _response_body(response)
    actual_decision = response_body.get("decision")
    actual_error_code = _error_code(response_body)
    actual_route_key = response_body.get("route_key")
    passed = (
        response.status_code == case.expected_status
        and actual_decision == case.expected_decision
        and actual_error_code == case.expected_error_code
        and (
            case.expected_route_key is None
            or actual_route_key == case.expected_route_key
        )
    )
    return {
        "case": case.name,
        "mutation": case.mutation,
        "expected_status": case.expected_status,
        "actual_status": response.status_code,
        "expected_decision": case.expected_decision,
        "actual_decision": actual_decision,
        "expected_error_code": case.expected_error_code,
        "actual_error_code": actual_error_code,
        "expected_route_key": case.expected_route_key,
        "actual_route_key": actual_route_key,
        "trace_id": response_body.get("trace_id"),
        "request_id": response_body.get("request_id", request_id),
        "release_version": response_body.get("release_version"),
        "passed": passed,
    }


def _headers_for_case(
    *,
    case: DifySmokeCase,
    state: Mapping[str, Any],
    request_id: str,
) -> dict[str, str]:
    api_key = str(state["api_key"])
    service_id = str(state["service_id"])
    if case.mutation == "wrong_api_key":
        api_key = f"{api_key}-wrong"
    if case.mutation == "wrong_service":
        service_id = f"{service_id}-wrong"
    return {
        "Authorization": f"Bearer {api_key}",
        "X-Key-Id": str(state["key_id"]),
        "X-App-Id": str(state["app_id"]),
        "X-Service-Id": service_id,
        "X-Request-Id": request_id,
        "Content-Type": "application/json",
    }


def _body_for_case(*, case: DifySmokeCase, request_id: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "channel": "chat",
        "user_context": {"workflow_run_id": request_id},
    }
    if case.mutation != "invalid_body":
        body["query"] = case.query
    return body


def _post(
    *,
    base_url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_seconds: float,
    http_client: Any | None,
    state: Mapping[str, Any],
) -> httpx.Response:
    try:
        if http_client is not None:
            return cast(
                "httpx.Response",
                http_client.post("/v1/intent-route", headers=headers, json=body),
            )
        return httpx.post(
            f"{base_url.rstrip('/')}/v1/intent-route",
            headers=headers,
            json=body,
            timeout=timeout_seconds,
        )
    except httpx.RequestError as exc:
        message = _redact_error_text(str(exc), state=state)
        raise RuntimeError(f"request failed: {message}") from exc


def _response_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except JSONDecodeError:
        return {"body": _trim_text(response.text)}
    if isinstance(body, dict):
        return cast("dict[str, Any]", body)
    return {"body": body}


def _error_code(body: Mapping[str, Any]) -> str | None:
    error = body.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        return str(code) if code is not None else None
    code = body.get("error_code")
    return str(code) if code is not None else None


def _redact_error_text(value: str, *, state: Mapping[str, Any]) -> str:
    redacted = value.replace("Bearer", "REDACTED")
    api_key = state.get("api_key")
    if isinstance(api_key, str) and api_key:
        redacted = redacted.replace(api_key, "REDACTED")
    return redacted


def _trim_text(value: str, *, limit: int = 200) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Dify branch smoke matrix.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
