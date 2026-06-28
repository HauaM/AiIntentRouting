from __future__ import annotations

import argparse
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, cast

import httpx


def run_runtime_smoke(
    *,
    base_url: str,
    state: dict[str, Any],
    query: str,
    expected_decision: str,
    expected_route_key: str | None = None,
    request_id: str = "dify-smoke-local-001",
    timeout_seconds: float = 8.0,
    output_path: Path | None = None,
    http_client: Any | None = None,
) -> dict[str, Any]:
    request_url = f"{base_url.rstrip('/')}/v1/intent-route"
    headers = {
        "Authorization": f"Bearer {state['api_key']}",
        "X-Key-Id": state["key_id"],
        "X-App-Id": state["app_id"],
        "X-Service-Id": state["service_id"],
        "X-Request-Id": request_id,
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "channel": "chat",
        "user_context": {"workflow_run_id": request_id},
    }
    if http_client is not None:
        response = http_client.post("/v1/intent-route", headers=headers, json=payload)
    else:
        try:
            response = httpx.post(
                request_url,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"request failed for {request_url}: {exc}"
            ) from exc

    body = _response_body(response)
    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code} {body}")
    if body.get("decision") != expected_decision:
        raise RuntimeError(
            f"expected decision {expected_decision}, got {body.get('decision')}: {body}"
        )
    if expected_route_key is not None and body.get("route_key") != expected_route_key:
        raise RuntimeError(
            f"expected route_key {expected_route_key}, got {body.get('route_key')}: {body}"
        )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(body, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return body


def _response_body(response: httpx.Response) -> dict[str, Any]:
    try:
        return cast("dict[str, Any]", response.json())
    except JSONDecodeError:
        return {"body": _trim_text(response.text)}


def _trim_text(value: str, *, limit: int = 200) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def main() -> None:
    args = _parse_args()
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    body = run_runtime_smoke(
        base_url=args.base_url,
        state=state,
        query=args.query,
        expected_decision=args.expect_decision,
        expected_route_key=args.expect_route_key,
        request_id=args.request_id,
        timeout_seconds=args.timeout_seconds,
        output_path=args.output,
    )
    print(json.dumps(body, ensure_ascii=False, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Dify runtime smoke request.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--expect-decision", required=True)
    parser.add_argument("--expect-route-key")
    parser.add_argument("--request-id", default="dify-smoke-local-001")
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    main()
