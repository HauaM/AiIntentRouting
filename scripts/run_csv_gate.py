from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from intent_routing.ops.admin_client import AdminApiClient
from intent_routing.ops.reports import PRESET_ORDER, render_threshold_report


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")

    state_path = Path(args.state)
    csv_path = Path(args.csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    service_id = state["service_id"]
    csv_text = csv_path.read_text(encoding="utf-8")

    runs: dict[str, dict[str, Any]] = {}
    with AdminApiClient(
        base_url=args.base_url,
        admin_token=admin_token,
        actor_id="csv-gate",
        actor_roles="system_admin",
    ) as api:
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

    report_json = {
        "service_id": service_id,
        "policy_version": state["policy_version"],
        "intent_catalog_version": state["intent_catalog_version"],
        "runs": runs,
    }
    json_path = out_dir / f"{service_id}-threshold-comparison.json"
    markdown_path = out_dir / f"{service_id}-threshold-comparison.md"
    json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_threshold_report(service_id=service_id, runs=runs),
        encoding="utf-8",
    )

    print(markdown_path)
    for preset in PRESET_ORDER:
        gate_state = "PASS" if runs[preset]["gate_passed"] else "FAIL"
        print(f"{preset}: {gate_state}")


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
