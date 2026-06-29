from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from scripts.run_pilot_readiness import run_pilot_readiness
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script invocation
    from run_pilot_readiness import run_pilot_readiness


def run_pilot_e2e_smoke(
    *,
    base_url: str,
    admin_token: str,
    service_id: str,
    environment: str,
    state_path: Path,
    out_dir: Path,
    csv_tier: str = "standard",
    csv_path: Path | None = None,
    required_preset: str = "balanced",
    http_client: Any | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    readiness_result = run_pilot_readiness(
        base_url=base_url,
        admin_token=admin_token,
        service_id=service_id,
        environment=environment,
        state_path=state_path,
        csv_tier=csv_tier,
        csv_path=csv_path,
        out_dir=out_dir,
        http_client=http_client,
        required_preset=required_preset,
    )
    readiness_payload = readiness_result["payload"]
    quality_gate = readiness_payload.get("quality_gate")
    if not isinstance(quality_gate, Mapping):
        raise RuntimeError("readiness workflow did not return a quality_gate")

    index = {
        "service_id": service_id,
        "environment": environment,
        "readiness_report": {
            "json_path": readiness_result["json_path"],
            "markdown_path": readiness_result["markdown_path"],
        },
        "threshold_report": dict(readiness_payload["threshold_report"]),
        "quality_gate": dict(quality_gate),
    }
    json_path = out_dir / "pilot-e2e-smoke-index.json"
    markdown_path = out_dir / "pilot-e2e-smoke-index.md"
    json_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_index_markdown(index), encoding="utf-8")
    return {
        **index,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")
    result = run_pilot_e2e_smoke(
        base_url=args.base_url,
        admin_token=admin_token,
        service_id=args.service_id,
        environment=args.environment,
        state_path=args.state_path,
        out_dir=args.out_dir,
        csv_tier=args.csv_tier,
        csv_path=args.csv,
        required_preset=args.required_preset,
    )
    print(
        json.dumps(
            {
                "json_path": result["json_path"],
                "markdown_path": result["markdown_path"],
                "quality_gate": result["quality_gate"],
            },
            ensure_ascii=False,
        )
    )
    if result["quality_gate"]["passed"] is False:
        raise SystemExit(1)


def _render_index_markdown(index: Mapping[str, Any]) -> str:
    quality_gate = index["quality_gate"]
    return "\n".join(
        [
            f"# Pilot E2E Smoke Index: {index['service_id']}",
            "",
            f"- Environment: `{index['environment']}`",
            f"- Required preset: `{quality_gate['required_preset']}`",
            f"- Quality gate: `{'PASS' if bool(quality_gate['passed']) else 'FAIL'}`",
            f"- Pass rate: `{_percent(quality_gate['pass_rate'])}`",
            f"- Risk pass rate: `{_percent(quality_gate['risk_pass_rate'])}`",
            "",
            "## Evidence Files",
            "",
            "| report | json | markdown |",
            "| --- | --- | --- |",
            (
                "| readiness | {json_path} | {markdown_path} |".format(
                    **index["readiness_report"]
                )
            ),
            (
                "| threshold comparison | {json_path} | {markdown_path} |".format(
                    **index["threshold_report"]
                )
            ),
            "",
        ]
    )


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pilot end-to-end smoke evidence workflow.")
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
    parser.add_argument(
        "--required-preset",
        choices=("strict", "balanced", "exploratory"),
        default="balanced",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
