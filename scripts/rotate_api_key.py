from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from intent_routing.ops.admin_client import AdminApiClient
from intent_routing.ops.pilot_catalog import load_pilot_catalog
from scripts.smoke_runtime_dify import run_runtime_smoke


class _AdminApi(Protocol):
    def post(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any: ...


def rotate_api_key(
    *,
    base_url: str,
    admin_token: str,
    catalog_path: Path,
    out_state_path: Path,
    report_dir: Path,
    smoke_query: str,
    state_path: Path | None = None,
    state: Mapping[str, Any] | None = None,
    expires_in_days: int = 365,
    revoke_old: bool = False,
    expected_decision: str = "confident",
    allowed_intents: Sequence[str] | None = None,
    allowed_route_keys: Sequence[str] | None = None,
    http_client: Any | None = None,
) -> dict[str, Any]:
    if state is None:
        if state_path is None:
            raise ValueError("state or state_path is required")
        state = json.loads(state_path.read_text(encoding="utf-8"))

    old_state = dict(state)
    catalog = load_pilot_catalog(catalog_path)
    service_id = str(old_state["service_id"])
    new_key_payload = {
        "service_id": service_id,
        "environment": str(old_state["environment"]),
        "app_id": str(old_state["app_id"]),
        "allowed_intents": list(
            allowed_intents or [intent.intent_id for intent in catalog.intents]
        ),
        "allowed_route_keys": list(
            allowed_route_keys or [intent.route_key for intent in catalog.intents]
        ),
        "expires_in_days": expires_in_days,
    }

    api_context: AbstractContextManager[_AdminApi]
    if http_client is None:
        api_context = AdminApiClient(
            base_url=base_url,
            admin_token=admin_token,
            actor_id="api-key-rotation",
            actor_roles="system_admin",
        )
    else:
        api_context = _TestClientAdminApi(
            http_client=http_client,
            admin_token=admin_token,
            actor_id="api-key-rotation",
            actor_roles="system_admin",
        )

    with api_context as api:
        new_key = api.post("/admin/v1/api-keys", json=new_key_payload)
        new_state = old_state | {
            "key_id": new_key["key_id"],
            "api_key": new_key["api_key"],
        }
        smoke = run_runtime_smoke(
            base_url=base_url,
            state=new_state,
            query=smoke_query,
            expected_decision=expected_decision,
            http_client=http_client,
        )
        old_key_revoked = False
        if revoke_old:
            api.post(f"/admin/v1/api-keys/{old_state['key_id']}:revoke")
            old_key_revoked = True

    _write_secret_state(out_state_path, new_state)
    report = _rotation_report(
        old_state=old_state,
        new_key=new_key,
        smoke=smoke,
        old_key_revoked=old_key_revoked,
    )
    report_path = _write_report(report_dir, service_id, report)
    return {
        "state": new_state,
        "report": report,
        "state_path": str(out_state_path),
        "report_path": str(report_path),
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")

    result = rotate_api_key(
        base_url=args.base_url,
        admin_token=admin_token,
        state_path=args.state,
        catalog_path=args.catalog,
        out_state_path=args.out_state,
        report_dir=args.report_dir,
        smoke_query=args.smoke_query,
        revoke_old=args.revoke_old,
        expires_in_days=args.expires_in_days,
        expected_decision=args.expect_decision,
        allowed_intents=args.allowed_intent,
        allowed_route_keys=args.allowed_route_key,
    )
    output = {
        "service_id": result["report"]["service_id"],
        "old_key_id": result["report"]["old_key_id"],
        "new_key_id": result["report"]["new_key_id"],
        "old_key_revoked": result["report"]["old_key_revoked"],
        "state_path": result["state_path"],
        "report_path": result["report_path"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


class _TestClientAdminApi:
    def __init__(
        self,
        *,
        http_client: Any,
        admin_token: str,
        actor_id: str,
        actor_roles: str,
    ) -> None:
        self._http_client = http_client
        self._headers = {
            "X-Admin-Token": admin_token,
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": actor_roles,
        }

    def __enter__(self) -> _TestClientAdminApi:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        return None

    def post(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        response = self._http_client.post(path, headers=self._headers, json=json)
        if response.status_code >= 400:
            raise RuntimeError(_format_response_error(response))
        if not response.content:
            return None
        return response.json()


def _rotation_report(
    *,
    old_state: Mapping[str, Any],
    new_key: Mapping[str, Any],
    smoke: Mapping[str, Any],
    old_key_revoked: bool,
) -> dict[str, Any]:
    return {
        "rotated_at": datetime.now(UTC).isoformat(),
        "service_id": old_state["service_id"],
        "environment": old_state["environment"],
        "app_id": old_state["app_id"],
        "old_key_id": old_state["key_id"],
        "new_key_id": new_key["key_id"],
        "new_key_fingerprint": new_key.get("key_fingerprint"),
        "smoke_trace_id": smoke.get("trace_id"),
        "smoke_decision": smoke.get("decision"),
        "smoke_route_key": smoke.get("route_key"),
        "old_key_revoked": old_key_revoked,
    }


def _write_secret_state(path: Path, state: Mapping[str, Any]) -> None:
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        temp_path = Path(temp_name)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    path.chmod(0o600)


def _write_report(report_dir: Path, service_id: str, report: Mapping[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{service_id}-api-key-rotation.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rotate a pilot runtime API key.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-token")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--out-state", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--smoke-query", required=True)
    parser.add_argument("--expect-decision", default="confident")
    parser.add_argument("--expires-in-days", type=int, default=365)
    parser.add_argument("--allowed-intent", action="append")
    parser.add_argument("--allowed-route-key", action="append")
    parser.add_argument("--revoke-old", action="store_true")
    return parser.parse_args(argv)


def _format_response_error(response: Any) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"{response.status_code} HTTP_ERROR {response.text}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return (
            f"{response.status_code} "
            f"{error.get('code', 'UNKNOWN_ERROR')} "
            f"{error.get('message', '')}"
        ).strip()
    return f"{response.status_code} HTTP_ERROR {body}"


if __name__ == "__main__":
    main()
