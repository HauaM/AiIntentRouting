from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from intent_routing.ops.csv_baseline import (  # noqa: E402
    compare_baseline,
    freeze_baseline,
    render_baseline_comparison_json,
    render_baseline_comparison_markdown,
)


def freeze_csv_baseline(
    *,
    threshold_report_path: Path,
    csv_path: Path,
    preset: str,
    baseline_id: str,
    out_path: Path,
) -> dict[str, Any]:
    threshold_report = _read_json(threshold_report_path)
    baseline = freeze_baseline(threshold_report, csv_path, preset)
    baseline["baseline_id"] = baseline_id
    baseline["policy"]["baseline_id"] = baseline_id
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"json_path": str(out_path), "baseline": baseline}


def compare_csv_baseline(
    *,
    threshold_report_path: Path,
    baseline_path: Path,
    out_dir: Path,
    exit_on_failure: bool = True,
) -> dict[str, Any]:
    threshold_report = _read_json(threshold_report_path)
    baseline = _read_json(baseline_path)
    comparison = compare_baseline(threshold_report, baseline)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "csv-baseline-comparison.json"
    markdown_path = out_dir / "csv-baseline-comparison.md"
    json_path.write_text(render_baseline_comparison_json(comparison), encoding="utf-8")
    markdown_path.write_text(
        render_baseline_comparison_markdown(comparison),
        encoding="utf-8",
    )
    result = {
        "passed": comparison.passed,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "block_reasons": comparison.block_reasons,
    }
    if not comparison.passed and exit_on_failure:
        raise SystemExit(1)
    return result


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.command == "freeze":
        result = freeze_csv_baseline(
            threshold_report_path=args.threshold_report,
            csv_path=args.csv,
            preset=args.preset,
            baseline_id=args.baseline_id,
            out_path=args.out,
        )
        print(result["json_path"])
        return
    result = compare_csv_baseline(
        threshold_report_path=args.threshold_report,
        baseline_path=args.baseline,
        out_dir=args.out_dir,
    )
    print(result["json_path"])


def _read_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return parsed


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze or compare a CSV baseline.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    freeze = subcommands.add_parser("freeze")
    freeze.add_argument("--threshold-report", type=Path, required=True)
    freeze.add_argument("--csv", type=Path, required=True)
    freeze.add_argument("--preset", required=True)
    freeze.add_argument("--baseline-id", required=True)
    freeze.add_argument("--out", type=Path, required=True)

    compare = subcommands.add_parser("compare")
    compare.add_argument("--threshold-report", type=Path, required=True)
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
