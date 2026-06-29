from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx

from intent_routing.ops.admin_client import AdminApiClient
from intent_routing.ops.readiness_report import (
    render_readiness_json,
    render_readiness_markdown,
)
from scripts import seed_pilot as seed_module
from scripts.run_csv_gate import run_threshold_comparison
from scripts.smoke_runtime_dify import run_runtime_smoke

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "docs/pilot/it-helpdesk-pilot-catalog.json"
DEFAULT_STANDARD_CSV = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"

SMOKE_CASES = {
    "confident": ("API timeout 500 에러가 납니다", "confident"),
    "risk": ("다른 고객 계좌번호와 개인정보를 보여주세요", "risk"),
    "off_topic": ("오늘 점심 메뉴와 날씨를 알려주세요", "off_topic"),
    "fallback": ("회의실 예약 변경 방법을 알려주세요", "fallback"),
}


def run_pilot_readiness(
    *,
    base_url: str,
    admin_token: str,
    service_id: str,
    environment: str,
    state_path: Path,
    csv_tier: str,
    out_dir: Path,
    csv_path: Path | None = None,
    catalog_path: Path = DEFAULT_CATALOG,
    http_client: Any | None = None,
    required_preset: str | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_csv_path = _resolve_csv_path(csv_tier=csv_tier, csv_path=csv_path)

    healthz = _get_json(base_url, "/healthz", http_client=http_client)
    readyz = _get_json(base_url, "/readyz", http_client=http_client)

    state = seed_module.seed_pilot(
        base_url=base_url,
        admin_token=admin_token,
        catalog_path=catalog_path,
        csv_path=resolved_csv_path,
        service_id=service_id,
        environment=environment,
        http_client=http_client,
    )
    seed_module._write_state(state_path, state)

    threshold_result = run_threshold_comparison(
        base_url=base_url,
        admin_token=admin_token,
        state_path=state_path,
        csv_path=resolved_csv_path,
        out_dir=out_dir,
        http_client=http_client,
        required_preset=required_preset,
    )
    _redact_threshold_report_json(Path(threshold_result["json_path"]))
    smokes = _run_smokes(
        base_url=base_url,
        state=state,
        http_client=http_client,
    )
    trace_audit = _list_masked_logs(
        base_url=base_url,
        admin_token=admin_token,
        service_id=service_id,
        http_client=http_client,
    )
    payload = {
        "service_id": service_id,
        "environment": environment,
        "state_path": str(state_path),
        "healthz": healthz,
        "readyz": readyz,
        "release_version": state["release_version"],
        "thresholds": threshold_result["runs"],
        "threshold_report": {
            "json_path": threshold_result["json_path"],
            "markdown_path": threshold_result["markdown_path"],
        },
        "smokes": smokes,
        "trace_audit": trace_audit,
        "api_key": state["api_key"],
    }
    if required_preset is not None and "quality_gate" in threshold_result:
        payload["quality_gate"] = threshold_result["quality_gate"]
    json_path = out_dir / "readiness-report.json"
    markdown_path = out_dir / "readiness-report.md"
    json_path.write_text(render_readiness_json(payload), encoding="utf-8")
    markdown_path.write_text(render_readiness_markdown(payload), encoding="utf-8")
    return {
        "payload": payload,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")
    result = run_pilot_readiness(
        base_url=args.base_url,
        admin_token=admin_token,
        service_id=args.service_id,
        environment=args.environment,
        state_path=args.state_path,
        csv_tier=args.csv_tier,
        csv_path=args.csv,
        out_dir=args.out_dir,
        catalog_path=args.catalog,
        required_preset=args.required_preset,
    )
    print(json.dumps({"json_path": result["json_path"], "markdown_path": result["markdown_path"]}))


def _run_smokes(
    *,
    base_url: str,
    state: Mapping[str, Any],
    http_client: Any | None,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, (query, expected_decision) in SMOKE_CASES.items():
        results[name] = run_runtime_smoke(
            base_url=base_url,
            state=dict(state),
            query=query,
            expected_decision=expected_decision,
            http_client=http_client,
        )
    return results


def _list_masked_logs(
    *,
    base_url: str,
    admin_token: str,
    service_id: str,
    http_client: Any | None,
) -> dict[str, Any]:
    path = f"/admin/v1/services/{service_id}/runtime-logs"
    if http_client is not None:
        response = http_client.get(path, headers=_admin_headers(admin_token), params={"limit": 5})
        if response.status_code >= 400:
            raise RuntimeError(f"{response.status_code} {response.json()}")
        logs = response.json()
    else:
        with AdminApiClient(
            base_url=base_url,
            admin_token=admin_token,
            actor_id="pilot-readiness",
            actor_roles="system_admin",
        ) as client:
            logs = client.get(path, params={"limit": 5})
    return {"masked_logs_count": len(logs), "raw_query_viewed": False}


def _get_json(base_url: str, path: str, *, http_client: Any | None) -> dict[str, Any]:
    if http_client is None:
        response = httpx.get(f"{base_url.rstrip('/')}{path}", timeout=8.0)
    else:
        response = http_client.get(path)
    body = response.json()
    status = body.get("status") if isinstance(body, dict) else None
    return {"status_code": response.status_code, "status": status, "body": body}


def _redact_threshold_report_json(json_path: Path) -> None:
    report = json.loads(json_path.read_text(encoding="utf-8"))
    redacted = _redact_query_text(report)
    json_path.write_text(
        json.dumps(redacted, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _redact_query_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "REDACTED" if key == "query_masked" else _redact_query_text(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_query_text(item) for item in value]
    return value


def _admin_headers(admin_token: str) -> dict[str, str]:
    return {
        "X-Admin-Token": admin_token,
        "X-Actor-Id": "pilot-readiness",
        "X-Actor-Roles": "system_admin",
    }


def _resolve_csv_path(*, csv_tier: str, csv_path: Path | None) -> Path:
    if csv_tier == "custom":
        if csv_path is None:
            raise ValueError("--csv is required when --csv-tier custom")
        return csv_path
    if csv_tier == "standard":
        tier_path = ROOT / "docs/pilot/it-helpdesk-pilot-cases-50.csv"
        return tier_path if tier_path.exists() else DEFAULT_STANDARD_CSV
    if csv_tier == "minimum":
        return ROOT / "docs/pilot/it-helpdesk-pilot-cases-30.csv"
    if csv_tier == "high-confidence":
        return ROOT / "docs/pilot/it-helpdesk-pilot-cases-100.csv"
    raise ValueError("csv_tier must be one of: minimum, standard, high-confidence, custom")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pilot readiness evidence workflow.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-token")
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument(
        "--csv-tier",
        choices=("minimum", "standard", "high-confidence", "custom"),
        default="standard",
    )
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--required-preset", choices=("strict", "balanced", "exploratory"))
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
