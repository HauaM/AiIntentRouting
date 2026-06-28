from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol

from intent_routing.ops.admin_client import AdminApiClient
from intent_routing.ops.reports import PRESET_ORDER, render_threshold_report


class _AdminApi(Protocol):
    def post(self, path: str, *, json: dict[str, Any] | None = None) -> Any: ...

    def get(self, path: str) -> Any: ...


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")

    result = run_threshold_comparison(
        base_url=args.base_url,
        admin_token=admin_token,
        state_path=Path(args.state),
        csv_path=Path(args.csv),
        out_dir=Path(args.out_dir),
    )

    print(result["markdown_path"])
    runs = result["runs"]
    for preset in PRESET_ORDER:
        gate_state = "PASS" if runs[preset]["gate_passed"] else "FAIL"
        print(f"{preset}: {gate_state}")


def run_threshold_comparison(
    *,
    base_url: str,
    admin_token: str,
    state_path: Path,
    csv_path: Path,
    out_dir: Path,
    http_client: Any | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    service_id = state["service_id"]
    _validate_service_id_for_output(service_id)
    csv_text = csv_path.read_text(encoding="utf-8")

    runs: dict[str, dict[str, Any]] = {}
    results: dict[str, list[dict[str, Any]]] = {}
    api_context: AbstractContextManager[_AdminApi]
    if http_client is None:
        api_context = AdminApiClient(
            base_url=base_url,
            admin_token=admin_token,
            actor_id="csv-gate",
            actor_roles="system_admin",
        )
    else:
        api_context = _TestClientAdminApi(
            http_client=http_client,
            admin_token=admin_token,
            actor_id="csv-gate",
            actor_roles="system_admin",
        )

    with api_context as api:
        for preset in PRESET_ORDER:
            runs[preset] = api.post(
                f"/admin/v1/services/{service_id}/test-runs",
                json={
                    "policy_version": state["policy_version"],
                    "intent_catalog_version": state["intent_catalog_version"],
                    "threshold_preset": preset,
                    "source_filename": csv_path.name,
                    "csv_text": csv_text,
                },
            )
            test_run_id = runs[preset]["test_run_id"]
            results[preset] = api.get(
                f"/admin/v1/services/{service_id}/test-runs/{test_run_id}/results"
            )

    report_json = {
        "service_id": service_id,
        "policy_version": state["policy_version"],
        "intent_catalog_version": state["intent_catalog_version"],
        "runs": runs,
        "results": results,
    }
    json_path = out_dir / f"{service_id}-threshold-comparison.json"
    markdown_path = out_dir / f"{service_id}-threshold-comparison.md"
    json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_threshold_report(
            service_id=service_id,
            runs=runs,
            results_by_preset=results,
        ),
        encoding="utf-8",
    )
    return {
        "service_id": service_id,
        "policy_version": state["policy_version"],
        "intent_catalog_version": state["intent_catalog_version"],
        "runs": runs,
        "results": results,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


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

    def post(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        response = self._http_client.post(path, headers=self._headers, json=json)
        if response.status_code >= 400:
            raise RuntimeError(f"{response.status_code} {response.json()}")
        return response.json()

    def get(self, path: str) -> Any:
        response = self._http_client.get(path, headers=self._headers)
        if response.status_code >= 400:
            raise RuntimeError(f"{response.status_code} {response.json()}")
        return response.json()


def _validate_service_id_for_output(service_id: str) -> None:
    if service_id in {"", ".", ".."} or "/" in service_id or "\\" in service_id:
        raise ValueError(
            "service_id must be a direct filename-safe identifier without path separators"
        )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CSV gate comparisons across presets.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-token")
    parser.add_argument("--state", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
