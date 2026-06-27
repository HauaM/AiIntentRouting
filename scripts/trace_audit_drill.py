from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from intent_routing.ops.admin_client import AdminApiClient


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")

    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    service_id = state["service_id"]

    with AdminApiClient(
        base_url=args.base_url,
        admin_token=admin_token,
        actor_id="pilot-auditor",
        actor_roles="auditor",
        service_scope=service_id,
    ) as client:
        payload = _run_drill(
            client=client,
            service_id=service_id,
            trace_id=args.trace_id,
            view_reason=args.view_reason,
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _run_drill(
    *,
    client: AdminApiClient,
    service_id: str,
    trace_id: str | None,
    view_reason: str | None,
) -> Any:
    if trace_id is None:
        return client.get(
            f"/admin/v1/services/{service_id}/runtime-logs",
            params={"limit": 5},
        )
    if view_reason is None:
        return client.get(f"/admin/v1/services/{service_id}/runtime-logs/{trace_id}")

    response = client.post(
        f"/admin/v1/services/{service_id}/runtime-logs/{trace_id}:decrypt-raw-query",
        json={"view_reason": view_reason},
    )
    return {
        "trace_id": response["trace_id"],
        "service_id": response["service_id"],
        "viewed_by": response["viewed_by"],
        "viewed_at": response["viewed_at"],
        "raw_query_viewed": True,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the intent routing trace and audit drill."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-token", default="local-admin-token")
    parser.add_argument("--state", required=True)
    parser.add_argument("--trace-id")
    parser.add_argument("--view-reason")
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
