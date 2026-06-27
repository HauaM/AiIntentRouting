from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import httpx


def run_runtime_smoke(
    *,
    base_url: str,
    state: dict[str, Any],
    query: str,
    expected_decision: str,
    http_client: Any | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {state['api_key']}",
        "X-Key-Id": state["key_id"],
        "X-App-Id": state["app_id"],
        "X-Service-Id": state["service_id"],
        "X-Request-Id": "dify-smoke-local-001",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "channel": "chat",
        "user_context": {"workflow_run_id": "dify-smoke-local-001"},
    }
    if http_client is not None:
        response = http_client.post("/v1/intent-route", headers=headers, json=payload)
    else:
        response = httpx.post(
            f"{base_url.rstrip('/')}/v1/intent-route",
            headers=headers,
            json=payload,
            timeout=8.0,
        )

    body = cast("dict[str, Any]", response.json())
    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code} {body}")
    if body.get("decision") != expected_decision:
        raise RuntimeError(
            f"expected decision {expected_decision}, got {body.get('decision')}: {body}"
        )
    return body


def main() -> None:
    args = _parse_args()
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    body = run_runtime_smoke(
        base_url=args.base_url,
        state=state,
        query=args.query,
        expected_decision=args.expect_decision,
    )
    print(json.dumps(body, ensure_ascii=False, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Dify runtime smoke request.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--expect-decision", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
